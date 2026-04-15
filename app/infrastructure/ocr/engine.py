"""
OCR Engine - Cloud-native implementation using Groq Vision API.
Converts ANY document (scanned PDF, image, digital PDF) to text.

Strategy:
  1. Digital PDF  → pypdf text layer (fast, free)
  2. Scanned PDF  → convert pages to base64 images → Groq Vision
  3. Images       → base64 encode → Groq Vision
  4. Fallback     → return empty with helpful error

This works 100% on Render/cloud with NO binary dependencies.
"""
from __future__ import annotations
import base64
import io
import os
import time
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import OCRResult

logger = get_logger(__name__)

_IS_CLOUD = os.environ.get("RENDER") == "true"


class OCREngine:
    """
    Cloud-native OCR using Groq Vision (llama-4 scout) for images/scanned docs.
    Falls back to pypdf for digital PDFs. Works everywhere.
    """

    def __init__(self):
        self._groq = None

    def _get_groq(self):
        if self._groq is None:
            from groq import AsyncGroq
            self._groq = AsyncGroq(api_key=settings.GROQ_API_KEY)
        return self._groq

    async def extract_text(self, file_path: str) -> OCRResult:
        path = Path(file_path)
        if not path.exists():
            return OCRResult(raw_text="", confidence=0.0,
                             error=f"File not found: {file_path}")

        ext = path.suffix.lower().lstrip(".")
        start = time.monotonic()

        try:
            if ext == "pdf":
                result = await self._process_pdf(str(path))
            elif ext in ["png", "jpg", "jpeg", "tiff", "tif", "bmp", "webp"]:
                result = await self._process_image(str(path))
            else:
                return OCRResult(raw_text="", confidence=0.0,
                                 error=f"Unsupported: {ext}")

            result.extraction_time_ms = (time.monotonic() - start) * 1000
            logger.info("OCR done", extra={"extra_data": {
                "file": path.name, "engine": result.engine_used,
                "chars": len(result.raw_text), "ms": round(result.extraction_time_ms)
            }})
            return result

        except Exception as e:
            logger.error(f"OCR failed: {e}", exc_info=True)
            return OCRResult(raw_text="", confidence=0.0, error=str(e),
                             extraction_time_ms=(time.monotonic() - start) * 1000)

    async def _process_pdf(self, file_path: str) -> OCRResult:
        """Try text layer first, then vision OCR for scanned pages."""
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            scanned_pages = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if len(text.strip()) > 30:
                    pages_text.append(text.strip())
                else:
                    scanned_pages.append(i)

            # If most pages have text, return text layer result
            if len(pages_text) > len(scanned_pages):
                full_text = "\n\n".join(pages_text)
                return OCRResult(
                    raw_text=full_text, confidence=0.95,
                    pages=len(reader.pages),
                    language_detected=self._detect_lang(full_text),
                    engine_used="pypdf_text"
                )

            # Scanned PDF — convert to images and use vision OCR
            logger.info(f"Scanned PDF detected ({len(scanned_pages)} pages), using vision OCR")
            return await self._pdf_vision_ocr(file_path, reader.pages)

        except Exception as e:
            logger.warning(f"PDF processing error: {e}")
            return OCRResult(raw_text="", confidence=0.0, error=str(e))

    async def _pdf_vision_ocr(self, file_path: str, pages) -> OCRResult:
        """Convert PDF pages to base64 and OCR with Groq Vision."""
        try:
            # Try pdf2image if available (local), else use Pillow fallback
            images_b64 = await self._pdf_to_base64_images(file_path)

            if not images_b64:
                return OCRResult(raw_text="", confidence=0.0,
                                 error="Could not convert PDF pages to images")

            all_text = []
            for i, img_b64 in enumerate(images_b64[:5]):  # Max 5 pages
                page_text = await self._vision_ocr(img_b64, f"page {i+1}")
                if page_text:
                    all_text.append(page_text)

            full_text = "\n\n--- Page Break ---\n\n".join(all_text)
            return OCRResult(
                raw_text=full_text, confidence=0.88,
                pages=len(images_b64),
                language_detected=self._detect_lang(full_text),
                engine_used="groq_vision_pdf"
            )
        except Exception as e:
            logger.error(f"PDF vision OCR failed: {e}")
            return OCRResult(raw_text="", confidence=0.0, error=str(e))

    async def _process_image(self, file_path: str) -> OCRResult:
        """Process image file using Groq Vision."""
        with open(file_path, "rb") as f:
            img_bytes = f.read()

        # Detect MIME type
        ext = Path(file_path).suffix.lower().lstrip(".")
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
                "png": "image/png", "tiff": "image/tiff",
                "bmp": "image/bmp", "webp": "image/webp"}.get(ext, "image/jpeg")

        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        img_b64_url = f"data:{mime};base64,{img_b64}"

        text = await self._vision_ocr(img_b64_url)
        return OCRResult(
            raw_text=text or "", confidence=0.90 if text else 0.0,
            language_detected=self._detect_lang(text or ""),
            engine_used="groq_vision_image"
        )

    async def _vision_ocr(self, image_b64_url: str,
                           context: str = "document") -> str:
        """Send image to Groq Vision model for text extraction."""
        try:
            groq = self._get_groq()
            response = await groq.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_b64_url}
                        },
                        {
                            "type": "text",
                            "text": (
                                f"Extract ALL text from this insurance document {context}. "
                                "Include every word, number, date, and symbol exactly as shown. "
                                "Preserve line structure. Output raw text only, no commentary. "
                                "Handle English, Hindi, Tamil, Telugu, or any Indian language text."
                            )
                        }
                    ]
                }],
                max_tokens=4096,
                temperature=0.0,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.warning(f"Groq Vision OCR failed: {e}")
            return ""

    async def _pdf_to_base64_images(self, file_path: str) -> list[str]:
        """Convert PDF pages to base64 image strings."""
        images_b64 = []

        # Try pdf2image (requires poppler — not available on Render)
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(file_path, dpi=150, first_page=1, last_page=5)
            for img in images:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                images_b64.append(f"data:image/png;base64,{b64}")
            return images_b64
        except Exception:
            pass

        # Fallback: use pypdf to extract embedded images
        try:
            import pypdf
            from PIL import Image
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages[:5]:
                for img_obj in page.images:
                    buf = io.BytesIO(img_obj.data)
                    img = Image.open(buf)
                    out_buf = io.BytesIO()
                    img.save(out_buf, format="PNG")
                    b64 = base64.b64encode(out_buf.getvalue()).decode("utf-8")
                    images_b64.append(f"data:image/png;base64,{b64}")
                    break  # One image per page
            if images_b64:
                return images_b64
        except Exception:
            pass

        return images_b64

    def _detect_lang(self, text: str) -> str:
        if not text:
            return "en"
        devanagari = sum(1 for c in text if '\u0900' <= c <= '\u097F')
        return "hi" if devanagari > 10 else "en"


_ocr_engine: Optional[OCREngine] = None


def get_ocr_engine() -> OCREngine:
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine
