from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, validator
from typing import List, Optional, Dict
from datetime import datetime
import logging

from src.services.social_monitor import SocialMediaMonitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitor", tags=["Social Media Monitoring"])

# Global instances
social_monitor = SocialMediaMonitor()

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

class CampaignMonitoringRequest(BaseModel):
    """Request for campaign monitoring"""
    client_name: str
    platforms: List[str] = ["twitter", "tiktok", "facebook"]
    monitoring_duration_hours: int = 24
    
    @validator('client_name')
    def validate_client_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Client name must be at least 2 characters')
        return v.strip().lower()

@router.post("/start")
async def start_monitoring(request: MonitoringRequest):
    """🔍 Start monitoring social media for a company"""
    return {
        "status": "monitoring_started",
        "company": request.company_name,
        "limit": request.limit,
        "message": "Mock monitoring active - real X/Twitter API integration coming next!"
    }

@router.post("/campaigns/start")
async def start_campaign_monitoring(request: CampaignMonitoringRequest, background_tasks: BackgroundTasks):
    """🚨 Start monitoring for coordinated campaigns against client"""
    try:
        logger.info(f"🔍 Starting campaign monitoring for {request.client_name}")
        
        # Start background monitoring
        background_tasks.add_task(
            monitor_client_campaigns,
            request.client_name,
            request.platforms,
            request.monitoring_duration_hours
        )
        
        return {
            "success": True,
            "client_name": request.client_name,
            "platforms": request.platforms,
            "monitoring_duration_hours": request.monitoring_duration_hours,
            "message": f"Campaign monitoring started for {request.client_name}",
            "started_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting campaign monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaigns/{client_name}")
async def get_client_campaigns(client_name: str, days: int = 7):
    """📊 Get detected campaigns for a client (Mock Implementation)"""
    try:
        # Mock response for now
        return {
            "client_name": client_name,
            "campaigns": [],
            "summary": {
                "active_campaigns": 0,
                "total_campaigns": 0,
                "severity_breakdown": {},
                "platform_breakdown": {}
            },
            "total_found": 0,
            "message": "Campaign detection integration in progress"
        }
        
    except Exception as e:
        logger.error(f"Error getting campaigns for {client_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/campaigns/{client_name}/summary")
async def get_campaign_summary(client_name: str):
    """📈 Get campaign summary for client dashboard (Mock Implementation)"""
    try:
        # Mock summary for now
        summary = {
            "active_campaigns": 0,
            "total_campaigns": 0,
            "severity_breakdown": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "platform_breakdown": {"twitter": 0, "tiktok": 0, "facebook": 0},
            "threat_level": "low",
            "client_name": client_name,
            "last_updated": datetime.now().isoformat(),
            "message": "Campaign detection integration in progress"
        }
        
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/campaigns/analyze")
async def analyze_content_batch(client_name: str, content_batch: List[Dict]):
    """🔍 Analyze batch of content for campaign detection (Mock Implementation)"""
    try:
        logger.info(f"🔍 Analyzing {len(content_batch)} items for {client_name}")
        
        # Mock analysis for now
        return {
            "success": True,
            "client_name": client_name,
            "content_analyzed": len(content_batch),
            "campaigns_detected": 0,
            "campaigns": [],
            "analyzed_at": datetime.now().isoformat(),
            "message": "Campaign detection integration in progress"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing content batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === HELPER FUNCTIONS ===

async def monitor_client_campaigns(client_name: str, platforms: List[str], duration_hours: int):
    """Background task to monitor client for campaigns"""
    try:
        logger.info(f"🔍 Background monitoring started for {client_name}")
        
        # Get social media content for client
        content_batch = []
        
        # Monitor Twitter/X
        if "twitter" in platforms:
            keywords = social_monitor.get_company_keywords(client_name)
            if keywords:
                twitter_content = await social_monitor.scan_for_threats(client_name, limit=50)
                content_batch.extend(twitter_content)
        
        # Monitor TikTok (would integrate with TikTok scraper)
        if "tiktok" in platforms:
            # Placeholder for TikTok monitoring
            logger.info(f"TikTok monitoring for {client_name} - integration pending")
        
        # Analyze content for campaigns (Mock for now)
        if content_batch:
            logger.info(f"📊 Mock analysis: {len(content_batch)} items for {client_name}")
            # Mock: No campaigns detected for now
            campaigns = []
        
        logger.info(f"✅ Background monitoring completed for {client_name}")
        
    except Exception as e:
        logger.error(f"Background monitoring error for {client_name}: {e}")