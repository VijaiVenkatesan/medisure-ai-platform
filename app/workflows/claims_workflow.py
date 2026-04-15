"""
LangGraph workflow: Stateful insurance claim processing pipeline.
Defines the directed graph with conditional branching and retry logic.

Flow:
OCR → Extract → Validate → PolicyCheck → FraudAnalysis → Decision → [HITL/Done]

Branches:
- Validation fail (critical) → skip to Decision with auto-reject
- Fraud HIGH → route to INVESTIGATE
- Low risk + small amount → auto-approve
"""
from __future__ import annotations
import asyncio
from typing import Literal
from langgraph.graph import StateGraph, END

from app.models.schemas import WorkflowState, ClaimStatus
from app.agents.extraction_agent import extraction_agent
from app.agents.validation_agent import validation_agent
from app.agents.policy_agent import policy_agent
from app.agents.fraud_agent import fraud_agent
from app.agents.decision_agent import decision_agent
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# OCR NODE
# ─────────────────────────────────────────────

async def ocr_node(state: WorkflowState) -> WorkflowState:
    """Run OCR on the uploaded document."""
    from app.infrastructure.ocr.engine import get_ocr_engine
    from app.core.logging import log_agent_start, log_agent_complete, log_agent_error

    log_agent_start(logger, "OCRNode", state.claim_id)
    state.status = ClaimStatus.OCR_PROCESSING

    if not state.document_path:
        state.errors.append("No document path provided")
        state.status = ClaimStatus.ERROR
        return state

    try:
        ocr_engine = get_ocr_engine()
        result = await ocr_engine.extract_text(state.document_path)
        state.ocr_result = result

        if result.error:
            state.errors.append(f"OCR error: {result.error}")
            logger.warning(f"OCR returned error for claim {state.claim_id}: {result.error}")
        else:
            log_agent_complete(logger, "OCRNode", state.claim_id, {
                "confidence": result.confidence,
                "text_length": len(result.raw_text),
                "language": result.language_detected,
            })

    except Exception as e:
        from app.core.logging import log_agent_error
        log_agent_error(logger, "OCRNode", state.claim_id, e)
        state.errors.append(f"OCR failed: {str(e)}")
        state.status = ClaimStatus.ERROR

    return state


# ─────────────────────────────────────────────
# RETRY WRAPPER
# ─────────────────────────────────────────────

def _with_retry(agent_fn, max_retries: int = 2):
    """Wrap an agent function with retry logic."""
    async def wrapper(state: WorkflowState) -> WorkflowState:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                return await agent_fn(state)
            except Exception as e:
                last_error = e
                state.retry_count += 1
                if attempt < max_retries:
                    wait = 1.5 ** attempt
                    logger.warning(
                        f"Agent {agent_fn.__name__} failed (attempt {attempt+1}), retrying in {wait:.1f}s: {e}"
                    )
                    await asyncio.sleep(wait)

        logger.error(f"Agent {agent_fn.__name__} exhausted retries: {last_error}")
        state.errors.append(f"{agent_fn.__name__} failed after {max_retries} retries: {str(last_error)}")
        return state

    wrapper.__name__ = agent_fn.__name__
    return wrapper


# ─────────────────────────────────────────────
# CONDITIONAL EDGES
# ─────────────────────────────────────────────

def route_after_ocr(state: WorkflowState) -> Literal["extract", "end"]:
    """Route after OCR: proceed if we have text, else end."""
    if state.status == ClaimStatus.ERROR:
        return "end"
    if state.ocr_result and state.ocr_result.raw_text.strip():
        return "extract"
    # OCR failed but no hard error - try extraction with empty text (will produce minimal data)
    return "extract"


def route_after_validation(state: WorkflowState) -> Literal["policy_check", "decision"]:
    """Route after validation: skip downstream if too many critical errors."""
    if state.should_skip_downstream:
        logger.info(f"Claim {state.claim_id}: skipping downstream agents due to validation failure")
        return "decision"
    return "policy_check"


def route_after_fraud(state: WorkflowState) -> Literal["decision", "end"]:
    """Route after fraud: always proceed to decision."""
    return "decision"


def route_after_decision(state: WorkflowState) -> Literal["end"]:
    """Final routing - always end (HITL status is set in state)."""
    return "end"


# ─────────────────────────────────────────────
# GRAPH CONSTRUCTION
# ─────────────────────────────────────────────

def build_workflow() -> StateGraph:
    """Build and compile the LangGraph workflow."""

    # Use dict-based state for LangGraph compatibility
    from langgraph.graph import StateGraph as SG

    # We pass WorkflowState as a dict to LangGraph and convert back
    workflow = SG(dict)

    # Add nodes with retry wrappers
    workflow.add_node("ocr", _dict_wrapped(ocr_node))
    workflow.add_node("extract", _dict_wrapped(_with_retry(extraction_agent)))
    workflow.add_node("validate", _dict_wrapped(_with_retry(validation_agent)))
    workflow.add_node("policy_check", _dict_wrapped(_with_retry(policy_agent)))
    workflow.add_node("fraud_analysis", _dict_wrapped(_with_retry(fraud_agent)))
    workflow.add_node("decision", _dict_wrapped(_with_retry(decision_agent)))

    # Set entry point
    workflow.set_entry_point("ocr")

    # Add edges
    workflow.add_conditional_edges(
        "ocr",
        lambda s: route_after_ocr(_dict_to_state(s)),
        {"extract": "extract", "end": END},
    )
    workflow.add_edge("extract", "validate")
    workflow.add_conditional_edges(
        "validate",
        lambda s: route_after_validation(_dict_to_state(s)),
        {"policy_check": "policy_check", "decision": "decision"},
    )
    workflow.add_edge("policy_check", "fraud_analysis")
    workflow.add_conditional_edges(
        "fraud_analysis",
        lambda s: route_after_fraud(_dict_to_state(s)),
        {"decision": "decision", "end": END},
    )
    workflow.add_conditional_edges(
        "decision",
        lambda s: route_after_decision(_dict_to_state(s)),
        {"end": END},
    )

    return workflow.compile()


def _dict_to_state(d: dict) -> WorkflowState:
    """Convert dict back to WorkflowState for routing functions."""
    try:
        return WorkflowState(**d)
    except Exception:
        return WorkflowState(claim_id=d.get("claim_id", "unknown"))


def _dict_wrapped(agent_fn):
    """Wrap an agent that accepts WorkflowState to work with dict-based LangGraph."""
    async def wrapper(state_dict: dict) -> dict:
        state = _dict_to_state(state_dict)
        result_state = await agent_fn(state)
        return result_state.model_dump()

    wrapper.__name__ = agent_fn.__name__
    return wrapper


# Compile once at module level
_compiled_workflow = None


def get_workflow():
    """Get the compiled workflow (singleton)."""
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = build_workflow()
        logger.info("LangGraph workflow compiled and ready")
    return _compiled_workflow


async def run_workflow(initial_state: WorkflowState) -> WorkflowState:
    """
    Execute the full claims processing workflow.
    Returns the final WorkflowState after all agents have run.
    """
    workflow = get_workflow()

    logger.info(
        f"Starting workflow for claim {initial_state.claim_id}",
        extra={"extra_data": {"claim_id": initial_state.claim_id, "correlation_id": initial_state.correlation_id}},
    )

    try:
        state_dict = initial_state.model_dump()
        final_dict = await workflow.ainvoke(state_dict)
        final_state = _dict_to_state(final_dict)

        logger.info(
            f"Workflow completed for claim {initial_state.claim_id}",
            extra={
                "extra_data": {
                    "claim_id": initial_state.claim_id,
                    "final_status": final_state.status.value if final_state.status else "UNKNOWN",
                    "decision": final_state.decision_result.decision.value if final_state.decision_result else "NONE",
                    "errors": len(final_state.errors),
                }
            },
        )

        return final_state

    except Exception as e:
        logger.error(f"Workflow failed for claim {initial_state.claim_id}: {e}", exc_info=True)
        initial_state.status = ClaimStatus.ERROR
        initial_state.errors.append(f"Workflow execution failed: {str(e)}")
        return initial_state
