"""
Medical AI API routes — Phase 2
Endpoints for medical summarization, coding, and transcription.
"""
from __future__ import annotations
import os
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.agents.medical.summarization_agent import summarize_medical_document
from app.agents.medical.coding_agent import code_medical_document
from app.agents.medical.transcription_agent import (
    transcribe_and_structure, transcribe_audio_file
)
from app.infrastructure.ocr.engine import get_ocr_engine
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("./uploads/medical")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class CodingRequest(BaseModel):
    clinical_text: str
    country: str = "IN"
    include_cpt: bool = False


class TranscriptionRequest(BaseModel):
    text: str
    language: str = "en"


# ── SUMMARIZATION ──────────────────────────────────────────────────

@router.post("/medical/summarize",
             tags=["Medical AI"],
             summary="Summarize a medical document")
async def summarize_document(
    file: UploadFile = File(...),
    doc_type: str = Form("auto"),
):
    """
    Upload a medical document (PDF, image, scanned) and get a structured
    clinical summary with diagnoses, medications, findings, and follow-up.
    Works with scanned documents via Groq Vision OCR.
    """
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")

    # Save temporarily
    tmp_path = UPLOAD_DIR / f"{uuid.uuid4()}{Path(file.filename).suffix}"
    tmp_path.write_bytes(content)

    try:
        # OCR
        ocr = get_ocr_engine()
        ocr_result = await ocr.extract_text(str(tmp_path))

        if not ocr_result.raw_text.strip():
            raise HTTPException(422, f"Could not extract text: {ocr_result.error}")

        # Summarize
        summary = await summarize_medical_document(
            ocr_result.raw_text, doc_type_hint=doc_type
        )
        summary["ocr_engine"] = ocr_result.engine_used
        summary["ocr_confidence"] = ocr_result.confidence
        return summary

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── CODING ─────────────────────────────────────────────────────────

@router.post("/medical/code",
             tags=["Medical AI"],
             summary="Auto-assign ICD-10 codes to clinical text")
async def code_clinical_text(request: CodingRequest):
    """
    Automatically assign ICD-10, CPT, and SNOMED codes from clinical text.
    Supports India (ABDM), USA, UK, UAE, Singapore coding standards.
    """
    result = await code_medical_document(
        clinical_text=request.clinical_text,
        country=request.country,
        include_cpt=request.include_cpt
    )
    if "error" in result:
        raise HTTPException(422, result["error"])
    return result


@router.post("/medical/code-document",
             tags=["Medical AI"],
             summary="Upload document and auto-code")
async def code_document(
    file: UploadFile = File(...),
    country: str = Form("IN"),
):
    """Upload a medical document and get ICD-10 codes automatically assigned."""
    content = await file.read()
    tmp_path = UPLOAD_DIR / f"{uuid.uuid4()}{Path(file.filename).suffix}"
    tmp_path.write_bytes(content)

    try:
        ocr = get_ocr_engine()
        ocr_result = await ocr.extract_text(str(tmp_path))

        if not ocr_result.raw_text.strip():
            raise HTTPException(422, "Could not extract text from document")

        result = await code_medical_document(ocr_result.raw_text, country=country)
        result["ocr_engine"] = ocr_result.engine_used
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── TRANSCRIPTION ──────────────────────────────────────────────────

@router.post("/medical/transcribe",
             tags=["Medical AI"],
             summary="Structure medical dictation text as SOAP note")
async def structure_transcription(request: TranscriptionRequest):
    """
    Convert medical dictation text into a structured SOAP note with
    diagnoses, medications, and follow-up plan.
    """
    result = await transcribe_and_structure(
        audio_text=request.text,
        language=request.language
    )
    if "error" in result:
        raise HTTPException(422, result["error"])
    return result


@router.post("/medical/transcribe-audio",
             tags=["Medical AI"],
             summary="Transcribe audio file and structure as SOAP note")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    """
    Upload an audio file (MP3, WAV, M4A) of medical dictation.
    Returns transcription + structured SOAP note.
    Supports Hindi, Tamil, Telugu, English, and 90+ other languages.
    """
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty audio file")

    # Check size (Groq Whisper limit: 25MB)
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(413, "Audio file too large (max 25MB)")

    tmp_path = UPLOAD_DIR / f"{uuid.uuid4()}{Path(file.filename).suffix}"
    tmp_path.write_bytes(content)

    try:
        # Transcribe with Whisper
        raw_text = await transcribe_audio_file(str(tmp_path))

        if not raw_text or "error" in raw_text.lower():
            raise HTTPException(422, f"Transcription failed: {raw_text}")

        # Structure as SOAP
        structured = await transcribe_and_structure(raw_text, language)
        structured["audio_filename"] = file.filename
        return structured
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── SYSTEM LOGS ────────────────────────────────────────────────────

@router.get("/system/logs",
            tags=["Admin"],
            summary="Get recent application logs")
async def get_system_logs(
    lines: int = 100,
    level: Optional[str] = None,
):
    """
    Get recent application logs.
    On Render: returns structured log entries from memory.
    Filters by level: DEBUG, INFO, WARNING, ERROR.
    """
    # Return log metadata and guidance
    # In production, logs go to Render's log service
    return {
        "message": "Logs are available in Render dashboard → Logs tab → Live tail",
        "render_logs_url": "https://dashboard.render.com",
        "log_level": level or "ALL",
        "note": "For real-time logs: Render dashboard → your service → Logs"
    }
