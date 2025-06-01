from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v1/monitor", tags=["Social Media Monitoring"])

class MonitoringRequest(BaseModel):
    company_name: str
    keywords: Optional[List[str]] = None
    limit: int = 10

@router.get("/status")
async def monitoring_status():
    """📊 Get monitoring system status"""
    return {
        "status": "active",
        "twitter_api": False,
        "supported_companies": 6,
        "version": "0.1.0"
    }

@router.get("/companies") 
async def get_supported_companies():
    """🏢 Get list of companies we can monitor"""
    companies = {
        "vodafone": ["Vodafone", "Vodafone Deutschland", "@VodafoneDE"],
        "bmw": ["BMW", "BMW Deutschland", "@BMW"],
        "bayer": ["Bayer", "Bayer AG", "@Bayer"],
        "deutsche_telekom": ["Deutsche Telekom", "Telekom", "@deutschetelekom"],
        "sap": ["SAP", "SAP Deutschland", "@SAP"],
        "siemens": ["Siemens", "Siemens AG", "@Siemens"]
    }
    return {
        "supported_companies": list(companies.keys()),
        "details": companies
    }

@router.post("/start")
async def start_monitoring(request: MonitoringRequest):
    """🔍 Start monitoring social media for a company"""
    return {
        "status": "monitoring_started",
        "company": request.company_name,
        "limit": request.limit,
        "message": "Mock monitoring active - real X/Twitter API integration coming next!"
    }