import io
import logging
import asyncio
from functools import lru_cache
from typing import List

import easyocr
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ocr_reader(languages: tuple = ("en", "de")) -> easyocr.Reader:
    """
    Returns a singleton EasyOCR reader instance.
    Using lru_cache avoids expensive re-initialization for every request.
    """
    logger.info(f"Initializing EasyOCR reader for languages: {languages}")
    return easyocr.Reader(list(languages), gpu=False)


async def extract_text_from_image(file_bytes: bytes, languages: List[str] = None) -> str:
    """
    Extract text from an image using EasyOCR.
    Executed in a background thread to avoid blocking the event loop.
    """
    if not file_bytes:
        return ""

    def _run_ocr() -> str:
        try:
            image = Image.open(io.BytesIO(file_bytes))
            image = image.convert("RGB")
            image_np = np.array(image)

            reader = get_ocr_reader(tuple(languages or ["en", "de"]))
            results = reader.readtext(image_np, detail=0, paragraph=True)

            if not results:
                return ""

            cleaned = [segment.strip() for segment in results if segment.strip()]
            return "\n".join(cleaned).strip()

        except Exception as exc:
            logger.error(f"OCR extraction failed: {exc}")
            return ""

    return await asyncio.to_thread(_run_ocr)

