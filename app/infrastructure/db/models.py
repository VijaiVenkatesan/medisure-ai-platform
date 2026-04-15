"""
Database infrastructure - async SQLAlchemy with SQLite (dev) / PostgreSQL (prod).
Handles all persistence including claims, documents, decisions, audit logs, HITL reviews.
"""
from __future__ import annotations
import json
from datetime import datetime
from typing import AsyncGenerator, Optional
from sqlalchemy import (
    Column, String, Float, Boolean, Integer, Text, DateTime,
    ForeignKey, Index, event, JSON
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─────────────────────────────────────────────
# BASE + ENGINE SETUP
# ─────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


def create_engine():
    db_url = settings.DATABASE_URL
    if "sqlite" in db_url:
        engine = create_async_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.DB_ECHO,
        )
    else:
        engine = create_async_engine(
            db_url,
            pool_size=settings.DB_POOL_SIZE,
            echo=settings.DB_ECHO,
        )
    return engine


engine = create_engine()
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Called at application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully")


# ─────────────────────────────────────────────
# ORM MODELS
# ─────────────────────────────────────────────

class ClaimDB(Base):
    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, index=True)
    correlation_id = Column(String(36), unique=True, index=True)
    status = Column(String(50), nullable=False, default="RECEIVED", index=True)
    country = Column(String(10), default="IN")
    currency = Column(String(10), default="INR")

    # Extracted data (stored as JSON)
    extracted_data = Column(JSON, nullable=True)
    ocr_raw_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, nullable=True)

    # Claimant info (denormalized for fast queries)
    claimant_name = Column(String(255), nullable=True, index=True)
    policy_number = Column(String(100), nullable=True, index=True)
    insurance_type = Column(String(50), nullable=True)
    claimed_amount = Column(Float, nullable=True)

    # Fraud
    fraud_score = Column(Float, nullable=True)
    fraud_level = Column(String(20), nullable=True)
    fraud_indicators = Column(JSON, nullable=True)

    # Decision
    decision = Column(String(30), nullable=True)
    decision_confidence = Column(Float, nullable=True)
    approved_amount = Column(Float, nullable=True)
    decision_explanation = Column(Text, nullable=True)

    # Workflow control
    retry_count = Column(Integer, default=0)
    error_log = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    documents = relationship("ClaimDocumentDB", back_populates="claim", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogDB", back_populates="claim", cascade="all, delete-orphan")
    hitl_reviews = relationship("HITLReviewDB", back_populates="claim", cascade="all, delete-orphan")
    decisions_history = relationship("DecisionDB", back_populates="claim", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_claims_status_created", "status", "created_at"),
        Index("ix_claims_fraud_score", "fraud_score"),
    )


class ClaimDocumentDB(Base):
    __tablename__ = "claim_documents"

    id = Column(String(36), primary_key=True, index=True)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    content_type = Column(String(100))
    size_bytes = Column(Integer)
    ocr_status = Column(String(30), default="PENDING")
    ocr_confidence = Column(Float, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("ClaimDB", back_populates="documents")


class DecisionDB(Base):
    __tablename__ = "decisions"

    id = Column(String(36), primary_key=True, index=True)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    decision = Column(String(30), nullable=False)
    confidence = Column(Float)
    explanation = Column(Text)
    approved_amount = Column(Float, nullable=True)
    rejection_reasons = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)
    decision_factors = Column(JSON, nullable=True)
    is_final = Column(Boolean, default=False)
    made_by = Column(String(100), default="SYSTEM")  # SYSTEM | reviewer_id
    made_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("ClaimDB", back_populates="decisions_history")


class AuditLogDB(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, index=True)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    actor = Column(String(100), nullable=False)  # SYSTEM | agent_name | user_id
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    claim = relationship("ClaimDB", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_claim_event", "claim_id", "event_type"),
    )


class HITLReviewDB(Base):
    __tablename__ = "hitl_reviews"

    id = Column(String(36), primary_key=True, index=True)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)
    approved_amount = Column(Float, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("ClaimDB", back_populates="hitl_reviews")


class PolicyDocumentDB(Base):
    __tablename__ = "policy_documents"

    id = Column(String(36), primary_key=True, index=True)
    policy_name = Column(String(255), nullable=False)
    insurance_type = Column(String(50))
    country = Column(String(10), default="IN")
    company = Column(String(255), nullable=True)
    content_hash = Column(String(64), unique=True)  # SHA-256 for dedup
    chunk_count = Column(Integer, default=0)
    indexed_at = Column(DateTime, default=datetime.utcnow)
    effective_date = Column(String(20), nullable=True)
