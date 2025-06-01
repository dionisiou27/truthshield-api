from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.core.detection import TruthShieldDetector, DetectionResult

router = APIRouter(prefix="/api/v1/detect", tags=["Detection"])

# Global detector instance
detector = TruthShieldDetector()

class TextDetectionRequest(BaseModel):
    text: str
    language: str = "de"

class ImageDetectionRequest(BaseModel):
    image_url: str
    
@router.post("/text", response_model=DetectionResult)
async def detect_text(request: TextDetectionRequest):
    """🔍 Detect if text content is AI-generated"""
    try:
        result = await detector.detect_text(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

@router.post("/image", response_model=DetectionResult)  
async def detect_image(request: ImageDetectionRequest):
    """🖼️ Detect if image is manipulated or deepfake"""
    try:
        result = await detector.detect_image(request.image_url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

@router.get("/status")
async def detection_status():
    """📊 Get detection engine status"""
    return {
        "status": "active",
        "models_loaded": {
            "transformers": True,
            "opencv": True,
            "german_nlp": False  # Disabled on Windows
        },
        "version": "0.1.0"
    }