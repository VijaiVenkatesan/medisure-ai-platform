"""
Medical Transcription Agent — Phase 2
Converts audio transcription text or dictation into structured SOAP notes.
Uses Groq Whisper for audio, then LLM for SOAP structuring.
"""
from __future__ import annotations
import base64
from app.infrastructure.llm.groq_client import get_groq_client
from app.core.logging import get_logger

logger = get_logger(__name__)

TRANSCRIPTION_SYSTEM = """You are a medical transcriptionist and clinical documentation specialist.
Convert medical dictation into properly formatted clinical notes.
Preserve all clinical details. Correct obvious transcription errors using medical context.
Structure output as SOAP (Subjective, Objective, Assessment, Plan) format.
Return valid JSON only."""

SOAP_SCHEMA = """{
  "raw_transcription": "verbatim transcription text",
  "soap_note": {
    "subjective": {
      "chief_complaint": "primary complaint",
      "history_of_present_illness": "HPI narrative",
      "past_medical_history": ["list"],
      "medications": ["list"],
      "allergies": ["list"],
      "social_history": "relevant social factors",
      "family_history": "relevant family history",
      "review_of_systems": ["positive findings"]
    },
    "objective": {
      "vitals": {"bp": null, "pulse": null, "temp": null, "weight": null, "spo2": null},
      "physical_examination": "examination findings",
      "lab_results": [],
      "imaging": []
    },
    "assessment": {
      "diagnoses": [{"description": "text", "icd10_code": "code"}],
      "clinical_impression": "clinical assessment narrative"
    },
    "plan": {
      "medications": [{"drug": "name", "dose": "dose", "frequency": "freq", "duration": "dur"}],
      "procedures": [],
      "referrals": [],
      "investigations_ordered": [],
      "patient_education": "",
      "follow_up": "",
      "return_precautions": []
    }
  },
  "confidence": 0.0,
  "language_detected": "en",
  "corrections_made": ["list of transcription corrections"]
}"""


async def transcribe_and_structure(
    audio_text: str,
    language: str = "en"
) -> dict:
    """
    Structure pre-transcribed text (or raw dictation) as SOAP note.
    
    For audio files, first transcribe with Groq Whisper, then call this.
    """
    if not audio_text or len(audio_text.strip()) < 10:
        return {"error": "Insufficient text to transcribe"}

    llm = get_groq_client()

    language_guidance = {
        "en": "English medical dictation",
        "hi": "Hindi medical dictation — handle Hindi medical terms",
        "ta": "Tamil medical dictation",
        "te": "Telugu medical dictation",
    }.get(language, "multilingual medical dictation")

    prompt = f"""Structure this medical {language_guidance} into a complete SOAP note.

DICTATION TEXT:
{audio_text[:4000]}

Instructions:
1. Identify and correct obvious speech-to-text errors using medical context
2. Expand medical abbreviations (BP=Blood Pressure, SOB=Shortness of Breath, etc.)
3. Assign ICD-10 codes where diagnoses are clearly stated
4. Structure medications with complete dosage information
5. Flag any unclear or ambiguous sections

Return complete JSON matching:
{SOAP_SCHEMA}"""

    try:
        result = await llm.extract_json(
            prompt=prompt,
            system_prompt=TRANSCRIPTION_SYSTEM,
            model="llama-3.3-70b-versatile"
        )
        logger.info("Medical transcription structured")
        return result
    except Exception as e:
        logger.error(f"Transcription structuring failed: {e}")
        return {"error": str(e)}


async def transcribe_audio_file(audio_file_path: str) -> str:
    """
    Transcribe audio file using Groq Whisper.
    Returns raw transcription text.
    """
    try:
        from groq import AsyncGroq
        from app.core.config import settings
        import aiofiles

        client = AsyncGroq(api_key=settings.GROQ_API_KEY)

        async with aiofiles.open(audio_file_path, "rb") as f:
            audio_bytes = await f.read()

        # Groq Whisper transcription
        transcription = await client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=("audio.mp3", audio_bytes),
            response_format="text",
            language=None,  # Auto-detect language
        )
        return transcription
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        return f"Transcription error: {str(e)}"
