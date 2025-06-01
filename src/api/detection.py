from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, validator
from typing import Dict, List, Optional
import logging
from datetime import datetime

from src.core.detection import TruthShieldDetector, DetectionResult, CompanyFactCheckRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/detect", tags=["Detection"])

# Global detector instance
detector = TruthShieldDetector()

# Legacy request models (backward compatibility)
class TextDetectionRequest(BaseModel):
    text: str
    language: str = "de"

class ImageDetectionRequest(BaseModel):
    image_url: str

# Enhanced request models
class FactCheckRequest(BaseModel):
    """Enhanced fact-checking request"""
    text: str
    company: str = "BMW"
    language: str = "de"
    generate_ai_response: bool = True
    
    @validator('company')
    def validate_company(cls, v):
        supported = ["BMW", "Vodafone", "Bayer", "Siemens", "Mercedes", "SAP"]
        if v not in supported:
            raise ValueError(f'Company must be one of: {supported}')
        return v
    
    @validator('text')
    def validate_text(cls, v):
        if len(v.strip()) < 10:
            raise ValueError('Text must be at least 10 characters')
        if len(v) > 1000:
            raise ValueError('Text must be less than 1000 characters')
        return v.strip()

class QuickFactCheckRequest(BaseModel):
    """Quick fact-check without AI response"""
    text: str
    company: str = "BMW"

# === LEGACY ENDPOINTS (backward compatibility) ===

@router.post("/text", response_model=DetectionResult)
async def detect_text(request: TextDetectionRequest):
    """🔍 Basic text detection (legacy)"""
    try:
        result = await detector.detect_text(request.text)
        return result
    except Exception as e:
        logger.error(f"Text detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

@router.post("/image", response_model=DetectionResult)  
async def detect_image(request: ImageDetectionRequest):
    """🖼️ Basic image detection (legacy)"""
    try:
        result = await detector.detect_image(request.image_url)
        return result
    except Exception as e:
        logger.error(f"Image detection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")

# === NEW AI-POWERED ENDPOINTS ===

@router.post("/fact-check", response_model=DetectionResult)
async def fact_check_claim(request: FactCheckRequest):
    """🧠 AI-powered fact-checking with brand response"""
    try:
        logger.info(f"🎯 Fact-checking claim for {request.company}")
        
        company_request = CompanyFactCheckRequest(
            text=request.text,
            company=request.company,
            language=request.language,
            generate_ai_response=request.generate_ai_response
        )
        
        result = await detector.fact_check_company_claim(company_request)
        
        logger.info(f"✅ Fact-check completed: {result.request_id}")
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Fact-checking failed: {e}")
        raise HTTPException(status_code=500, detail=f"Fact-checking failed: {str(e)}")

@router.post("/quick-check", response_model=DetectionResult)
async def quick_fact_check(request: QuickFactCheckRequest):
    """⚡ Quick fact-check without AI response generation"""
    try:
        company_request = CompanyFactCheckRequest(
            text=request.text,
            company=request.company,
            language="de",
            generate_ai_response=False
        )
        
        result = await detector.fact_check_company_claim(company_request)
        return result
        
    except Exception as e:
        logger.error(f"Quick fact-check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quick check failed: {str(e)}")

@router.get("/status")
async def detection_status():
    """📊 Get enhanced detection engine status"""
    try:
        stats = await detector.get_detection_stats()
        return {
            **stats,
            "endpoints": {
                "legacy": ["/text", "/image"],
                "ai_powered": ["/fact-check", "/quick-check"],
                "monitoring": ["/status", "/health"]
            },
            "example_requests": {
                "fact_check": {
                    "text": "BMW Elektroautos explodieren bei Minusgraden",
                    "company": "BMW",
                    "language": "de",
                    "generate_ai_response": True
                },
                "quick_check": {
                    "text": "Vodafone 5G causes cancer",
                    "company": "Vodafone"
                }
            }
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.get("/health")
async def health_check():
    """🏥 Health check endpoint"""
    try:
        stats = await detector.get_detection_stats()
        
        # Determine overall health
        ai_available = stats["capabilities"]["ai_fact_checking"]
        health_status = "healthy" if ai_available else "degraded"
        
        return {
            "status": health_status,
            "ai_available": ai_available,
            "timestamp": datetime.now().isoformat(),
            "message": "TruthShield Detection API operational" if ai_available 
                      else "TruthShield running in limited mode (no OpenAI)",
            "capabilities": stats["capabilities"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# === COMPANY-SPECIFIC ENDPOINTS ===

@router.get("/companies")
async def get_supported_companies():
    """🏢 Get list of supported companies"""
    try:
        stats = await detector.get_detection_stats()
        return {
            "supported_companies": stats["supported_companies"],
            "total_count": len(stats["supported_companies"]),
            "default": "BMW"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/demo")
async def demo_endpoint(background_tasks: BackgroundTasks):
    """🎪 Demo endpoint with sample data"""
    demo_requests = [
        {
            "text": "BMW Elektroautos explodieren bei Minusgraden",
            "company": "BMW",
            "expected": "This should be flagged as misinformation"
        },
        {
            "text": "Vodafone 5G network expansion continues in Germany",
            "company": "Vodafone", 
            "expected": "This should be marked as likely true"
        }
    ]
    
    return {
        "demo_mode": True,
        "available_demos": demo_requests,
        "usage": "POST to /fact-check with any of the demo texts",
        "note": "Demo responses may take 10-30 seconds due to AI processing"
    }