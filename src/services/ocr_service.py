import io
import logging
import asyncio
from functools import lru_cache
from typing import List

# Optional import - OCR is not critical for fact-checking
try:
    import easyocr
    from PIL import Image
    import numpy as np
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ocr_reader(languages: tuple = ("en", "de")):
    """
    Returns a singleton EasyOCR reader instance.
    Using lru_cache avoids expensive re-initialization for every request.
    """
    if not EASYOCR_AVAILABLE:
        logger.warning("EasyOCR not installed - OCR features disabled")
        return None
    logger.info(f"Initializing EasyOCR reader for languages: {languages}")
    return easyocr.Reader(list(languages), gpu=False)


async def extract_text_from_image(file_bytes: bytes, languages: List[str] = None) -> str:
    """
    Extract text from an image using EasyOCR.
    Executed in a background thread to avoid blocking the event loop.
    """
    if not file_bytes:
        return ""

    if not EASYOCR_AVAILABLE:
        logger.warning("OCR requested but EasyOCR not installed")
        return ""

    def _run_ocr() -> str:
        try:
            image = Image.open(io.BytesIO(file_bytes))
            image = image.convert("RGB")
            image_np = np.array(image)

            reader = get_ocr_reader(tuple(languages or ["en", "de"]))
            if reader is None:
                return ""
            results = reader.readtext(image_np, detail=0, paragraph=True)

            if not results:
                return ""

            cleaned = [segment.strip() for segment in results if segment.strip()]
            return "\n".join(cleaned).strip()

        except Exception as exc:
            logger.error(f"OCR extraction failed: {exc}")
            return ""

    return await asyncio.to_thread(_run_ocr)


class OCRService:
    """OCR Service wrapper class"""

    def __init__(self, languages: List[str] = None):
        self.languages = languages or ["en", "de"]
        self.available = EASYOCR_AVAILABLE

    async def extract_text(self, file_bytes: bytes) -> str:
        """Extract text from image bytes"""
        return await extract_text_from_image(file_bytes, self.languages)

    def is_available(self) -> bool:
        """Check if OCR is available"""
        return self.available
