from typing import Dict, List, Optional, Union
from pydantic import BaseModel
import logging
from datetime import datetime
import uuid

from .ai_engine import ai_engine, FactCheckResult as AIFactCheckResult, AIInfluencerResponse

logger = logging.getLogger(__name__)

class DetectionResult(BaseModel):
    """Enhanced detection result with fact-checking"""
    # Original fields
    content_type: str
    is_synthetic: bool
    confidence: float
    detection_method: str
    details: Dict
    timestamp: str
    
    # NEW: Fact-checking fields
    request_id: str
    fact_check: Optional[AIFactCheckResult] = None
    ai_response: Optional[Union[AIInfluencerResponse, Dict[str, AIInfluencerResponse]]] = None
    processing_time_ms: int

class CompanyFactCheckRequest(BaseModel):
    """Enhanced request model for company fact-checking"""
    text: str
    company: str = "BMW"
    language: str = "de"
    generate_ai_response: bool = True

class TruthShieldDetector:
    """Enhanced detector with real AI fact-checking"""
    
    def __init__(self):
        self.ai_engine = ai_engine
        logger.info("🛡️ TruthShield Detector initialized with AI engine")
    
    async def detect_text(self, text: str) -> DetectionResult:
        """Basic text detection (legacy endpoint)"""
        start_time = datetime.now()
        
        try:
            # Basic analysis
            word_count = len(text.split())
            char_count = len(text)
            confidence = min(0.8, max(0.2, word_count / 100))
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return DetectionResult(
                content_type="text",
                is_synthetic=confidence > 0.6,
                confidence=confidence,
                detection_method="basic_analysis",
                details={
                    "word_count": word_count,
                    "char_count": char_count,
                    "language": "auto-detected"
                },
                timestamp=datetime.now().isoformat(),
                request_id=str(uuid.uuid4()),
                processing_time_ms=int(processing_time)
            )
            
        except Exception as e:
            logger.error(f"Text detection error: {e}")
            raise
    
    async def detect_image(self, image_path: str) -> DetectionResult:
        """Basic image detection (legacy endpoint)"""
        start_time = datetime.now()
        
        try:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return DetectionResult(
                content_type="image",
                is_synthetic=False,
                confidence=0.5,
                detection_method="opencv_basic",
                details={
                    "file_path": image_path,
                    "analysis": "basic_opencv"
                },
                timestamp=datetime.now().isoformat(),
                request_id=str(uuid.uuid4()),
                processing_time_ms=int(processing_time)
            )
            
        except Exception as e:
            logger.error(f"Image detection error: {e}")
            raise
    
    async def fact_check_company_claim(self, request: CompanyFactCheckRequest) -> DetectionResult:
        """NEW: Complete fact-checking with AI response generation"""
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        logger.info(f"🔍 Starting fact-check for {request.company}: {request.text[:50]}...")
        
        try:
            # Step 1: AI Fact-checking
            fact_check_result = await self.ai_engine.fact_check_claim(
                text=request.text,
                company=request.company
            )
            
            # Step 2: Generate AI brand response (if requested)
            ai_response = None
            ai_responses = None
            if request.generate_ai_response:
                ai_responses = await self.ai_engine.generate_brand_response(
                    claim=request.text,
                    fact_check=fact_check_result,
                    company=request.company,
                    language=request.language
                )
                # Get the response for the requested language
                ai_response = ai_responses.get(request.language, ai_responses.get('en'))
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Build verified sources: pick up to 3 from distinct trusted domains
            def _domain(url: str) -> str:
                try:
                    return url.split('//', 1)[-1].split('/', 1)[0].lower()
                except Exception:
                    return ""

            reputable_domains = {
                "reuters.com", "apnews.com", "associatedpress.com", "bbc.com", "bbc.co.uk",
                "nytimes.com", "washingtonpost.com", "wsj.com", "bloomberg.com", "theguardian.com",
                "factcheck.org", "snopes.com", "politifact.com", "fullfact.org", "correctiv.org",
                "mimikama.org", "wikipedia.org", "wikidata.org", "npr.org", "theguardian.com",
                "afp.com", "apfactcheck.com", "afpfactcheck.com"
            }

            sorted_sources = sorted((fact_check_result.sources or []), key=lambda s: s.credibility_score, reverse=True)
            picked = []
            seen = set()
            # First pass: reputable domains only
            for s in sorted_sources:
                dom = _domain(s.url)
                if dom in reputable_domains and dom not in seen:
                    picked.append(s)
                    seen.add(dom)
                if len(picked) >= 3:
                    break
            # Fallback pass: any remaining distinct domains
            if len(picked) < 3:
                for s in sorted_sources:
                    dom = _domain(s.url)
                    if dom not in seen and dom:
                        picked.append(s)
                        seen.add(dom)
                    if len(picked) >= 3:
                        break

            # Final fill: if still fewer than 3 but sources exist, allow duplicates of existing domains
            if len(picked) < 3:
                for s in sorted_sources:
                    if s not in picked:
                        picked.append(s)
                    if len(picked) >= 3:
                        break

            # Create enhanced detection result
            result = DetectionResult(
                content_type="text",
                is_synthetic=fact_check_result.is_fake,
                confidence=fact_check_result.confidence,
                detection_method="ai_fact_checking",
                details={
                    "company": request.company,
                    "language": request.language,
                    "category": fact_check_result.category,
                    "sources_found": len(fact_check_result.sources),
                    "verified_sources": [s.model_dump() for s in picked],
                    "ai_response_generated": ai_response is not None,
                    "ai_responses": ai_responses if ai_responses else None  # Include both language responses
                },
                timestamp=datetime.now().isoformat(),
                request_id=request_id,
                fact_check=fact_check_result,
                ai_response=ai_response,  # Single response for requested language
                processing_time_ms=int(processing_time)
            )
            
            logger.info(f"✅ Fact-check complete [{request_id}]: "
                       f"Fake={fact_check_result.is_fake} "
                       f"Confidence={fact_check_result.confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Fact-checking failed [{request_id}]: {e}")
            
            # Return safe fallback
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return DetectionResult(
                content_type="text",
                is_synthetic=False,
                confidence=0.3,
                detection_method="ai_fact_checking_error",
                details={
                    "error": str(e),
                    "company": request.company,
                    "fallback_mode": True
                },
                timestamp=datetime.now().isoformat(),
                request_id=request_id,
                processing_time_ms=int(processing_time)
            )
    
    async def universal_fact_check(self, request: CompanyFactCheckRequest) -> DetectionResult:
        """Universal Guardian Bot - fact-checks any misinformation"""
        start_time = datetime.now()
        request_id = str(uuid.uuid4())
        
        # Override company for universal bot
        original_company = request.company
        request.company = "Guardian"  # This will use Guardian persona
        
        logger.info(f"🛡️ Universal Guardian Bot fact-check: {request.text[:50]}...")
        
        try:
            # Use the existing fact-checking logic
            result = await self.fact_check_company_claim(request)
            
            # Customize the response for Guardian Bot
            if result.ai_response:
                result.ai_response.bot_name = "Guardian Bot 🛡️"
                result.ai_response.bot_type = "universal"
                
            # Update details to show it's from Guardian Bot
            result.details.update({
                "bot_type": "universal",
                "original_company": original_company,
                "guardian_mode": True
            })
            
            logger.info(f"✅ Guardian Bot check complete [{request_id}]")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Guardian Bot failed [{request_id}]: {e}")
            
            # Fallback response
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return DetectionResult(
                content_type="text",
                is_synthetic=False,
                confidence=0.3,
                detection_method="guardian_bot_error",
                details={
                    "error": str(e),
                    "bot_type": "universal",
                    "fallback_mode": True
                },
                timestamp=datetime.now().isoformat(),
                request_id=request_id,
                processing_time_ms=int(processing_time)
            )
    
    async def get_detection_stats(self) -> Dict:
        """Get detector statistics"""
        return {
            "status": "active",
            "capabilities": {
                "basic_text_detection": True,
                "basic_image_detection": True,
                "ai_fact_checking": self.ai_engine.openai_client is not None,
                "company_responses": True,
                "source_verification": True,
                "universal_guardian_bot": True  # NEW
            },
            "supported_companies": list(self.ai_engine.company_personas.keys()),
            "supported_languages": ["de", "en"],
            "version": "1.1.0-guardian",
            "uptime": "active"
        }