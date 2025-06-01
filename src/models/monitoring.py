from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict

Base = declarative_base()

class MonitoredContent(Base):
    """Database model for monitored social media content"""
    __tablename__ = "monitored_content"
    
    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)  # twitter, facebook, etc
    content_id = Column(String(100), nullable=False)  # platform-specific ID
    content_text = Column(Text, nullable=True)
    content_url = Column(String(500), nullable=True)
    author_username = Column(String(100), nullable=True)
    
    # Detection Results
    is_synthetic = Column(Boolean, nullable=True)
    confidence_score = Column(Float, nullable=True)
    detection_method = Column(String(100), nullable=True)
    
    # Monitoring Info
    keyword_matched = Column(String(200), nullable=True)
    company_target = Column(String(100), nullable=True)  # Vodafone, BMW, etc
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    detected_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

class MonitoringKeyword(Base):
    """Keywords to monitor for each company"""
    __tablename__ = "monitoring_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(100), nullable=False)
    keyword = Column(String(200), nullable=False)
    language = Column(String(10), default="de")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Pydantic Models for API
class ContentDetectionResponse(BaseModel):
    content_id: str
    platform: str
    is_synthetic: bool
    confidence: float
    detection_method: str
    details: Dict
    timestamp: str

class MonitoringStats(BaseModel):
    total_monitored: int
    synthetic_detected: int
    companies_protected: int
    last_detection: Optional[str]