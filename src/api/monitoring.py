from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, validator
from typing import List, Optional, Dict
from datetime import datetime
import logging

from src.services.social_monitor import SocialMediaMonitor
from src.core.config import settings
from src.core.prioritization import PrioritizedItem
from src.core.coordinated_behavior import CoordinatedBehaviorDetector, AstroScoreResult
from src.core.evidence import EvidenceArchiver
from src.core.playbooks import get_playbooks, get_playbook
from src.core.threat_scoring import ThreatScoringEnsemble
from src.core.watchlist import WatchlistStore
from src.core.kpi import KPIDecider
from src.core.qa import QASampler
from src.core.coordinated_behavior import CoordinatedBehaviorDetector
from src.core.publish import PublishQueue
from src.core.config import settings
from src.core.audit import AuditLog
from random import random

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitor", tags=["Social Media Monitoring"])

# Global instances
social_monitor = SocialMediaMonitor()
astro_detector = CoordinatedBehaviorDetector()
evidence_archiver = EvidenceArchiver()
threat_ensemble = ThreatScoringEnsemble()
watchlists = WatchlistStore()
kpi_decider = KPIDecider()
qa_sampler = QASampler(kpi_decider)
publisher = PublishQueue()
auditor = AuditLog()

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

class PrioritizationItem(BaseModel):
    """Minimal schema for prioritization input (platform-agnostic)."""
    platform: Optional[str] = None
    content_id: Optional[str] = None
    content_text: Optional[str] = None
    content_url: Optional[str] = None
    author_username: Optional[str] = None
    # Metrics
    views: Optional[int] = 0
    growth_rate_24h: Optional[float] = 0.0
    author_followers: Optional[int] = 0
    follower_spike_24h: Optional[float] = 0.0
    coordination_score: Optional[float] = 0.0

class PrioritizationResponse(BaseModel):
    priority: str
    watchlist: bool
    pools: Dict[str, bool]
    score_components: Dict[str, float]
    thresholds: Dict[str, float]

class AstroSignals(BaseModel):
    # All signals optional; 0 default
    follower_spike_24h: Optional[float] = 0.0
    new_accounts_ratio: Optional[float] = 0.0
    synchronized_posting_ratio: Optional[float] = 0.0
    text_reuse_ratio: Optional[float] = 0.0
    shared_fingerprint_ratio: Optional[float] = 0.0
    account_age_days: Optional[float] = 365.0
    identical_media_ratio: Optional[float] = 0.0
    repeated_phrases_ratio: Optional[float] = 0.0
    reply_stacking_ratio: Optional[float] = 0.0
    comment_like_to_view_ratio: Optional[float] = 0.0
    author_network_density: Optional[float] = 0.0
    burst_posts_in_window: Optional[float] = 0.0
    posting_window_minutes: Optional[float] = 10.0
    stylometry_similarity: Optional[float] = 0.0
    recurring_token_signature: Optional[float] = 0.0
    unnatural_punctuation_ratio: Optional[float] = 0.0

class AstroScoreResponse(BaseModel):
    score_0_10: float
    category_scores: Dict[str, float]
    notes: List[str]

class PipelineItem(BaseModel):
    platform: Optional[str] = None
    content_id: Optional[str] = None
    content_text: Optional[str] = None
    content_url: Optional[str] = None
    author_username: Optional[str] = None
    views: Optional[int] = 0
    growth_rate_24h: Optional[float] = 0.0
    author_followers: Optional[int] = 0
    follower_spike_24h: Optional[float] = 0.0
    coordination_score: Optional[float] = 0.0
    # Optional astro signals
    astro_signals: Optional[AstroSignals] = None
    # KPI inputs
    harm_topic: Optional[str] = None
    harm_weight_override: Optional[float] = None
    avg_analyst_seconds: Optional[float] = None
    salary_rate_per_hour: Optional[float] = None
    client_max_cpr: Optional[float] = None
    # Auto-post integration
    verified: Optional[bool] = None

class RouteDecision(BaseModel):
    action: str  # ALERT_HITL | SEMI_HITL | ARCHIVE
    watchlist: bool
    astro_score: float
    virality_score: float
    reasons: List[str]
    evidence: Optional[Dict] = None
    qa_selected: Optional[bool] = None

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

@router.get("/prioritization/config")
async def get_prioritization_config():
    """Get current reach/risk/coordination thresholds."""
    return {
        "track_pool_min_views": settings.track_pool_min_views,
        "track_pool_min_growth_rate_24h": settings.track_pool_min_growth_rate_24h,
        "account_pool_min_followers": settings.account_pool_min_followers,
        "account_pool_min_follower_spike_24h": settings.account_pool_min_follower_spike_24h,
        "coordination_min_score": settings.coordination_min_score,
    }

@router.post("/prioritization/prioritize", response_model=List[PrioritizationResponse])
async def prioritize_items(items: List[PrioritizationItem]):
    """Prioritize content by Reach × Risk × Coordination and flag Watchlist candidates.

    - Track-Pool: views >= 5,000 OR growth_rate_24h >= 0.30
    - Account-Pool: author_followers >= 10,000 OR follower_spike_24h >= 2.0
    - coordination_min_score gates High priority
    """
    try:
        prioritized = social_monitor.prioritize_batch([i.model_dump() for i in items])
        responses: List[PrioritizationResponse] = []
        for p in prioritized:
            responses.append(PrioritizationResponse(
                priority=p.priority,
                watchlist=p.watchlist,
                pools=p.pools,
                score_components=p.score_components,
                thresholds=p.thresholds,
            ))
        return responses
    except Exception as e:
        logger.error(f"Prioritization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/astro/score", response_model=List[AstroScoreResponse])
async def astro_score_batch(items: List[AstroSignals]):
    """Score coordinated behavior (Astro-Score 0–10) for a batch of items."""
    try:
        results: List[AstroScoreResponse] = []
        for i in items:
            res = astro_detector.score(i.model_dump())
            results.append(AstroScoreResponse(
                score_0_10=res.score_0_10,
                category_scores=res.category_scores,
                notes=res.notes,
            ))
        return results
    except Exception as e:
        logger.error(f"Astro scoring error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class RedTeamScenario(BaseModel):
    name: str
    description: str
    tactics: List[str]

@router.get("/qa/redteam/scenarios", response_model=List[RedTeamScenario])
async def redteam_scenarios():
    return [
        RedTeamScenario(
            name="Synchronized Text Reuse",
            description="Multiple new accounts reuse identical captions within 10 minutes",
            tactics=["text_reuse", "temporal_burst", "new_accounts"]
        ),
        RedTeamScenario(
            name="Media Hash Replay",
            description="Identical video frame hashes posted by a cluster",
            tactics=["identical_media", "cluster_posting"]
        ),
        RedTeamScenario(
            name="Reply Stacking",
            description="Same set of accounts stacking comments to boost ranking",
            tactics=["reply_stacking", "comment_brigading"]
        ),
    ]


@router.get("/pipeline/config")
async def pipeline_config():
    return {
        "astro_alert_threshold": settings.astro_alert_threshold,
        "astro_semi_threshold": settings.astro_semi_threshold,
        "virality_threshold": settings.virality_threshold,
    }

@router.post("/pipeline/route", response_model=List[RouteDecision])
async def pipeline_route(items: List[PipelineItem]):
    """Route items through pre-filter → astro score → action decision."""
    decisions: List[RouteDecision] = []
    for item in items:
        base = item.model_dump()
        virality = social_monitor.virality_score(base)
        # Pre-filter: watchlist or virality ≥ threshold (client ROI can adjust)
        watchlist = False
        pools = social_monitor.prioritize_batch([base])[0].pools
        if pools.get("track_pool") or pools.get("account_pool"):
            watchlist = True
        # ROI scaling: if author/topic in client watchlist, scale threshold down
        roi_scale = 1.0
        wl = None
        if item.author_username:
            wl = watchlists.get(item.author_username)
        if not wl and base.get("content_text"):
            wl = watchlists.get(base.get("content_text", "")[:32])  # naive topic key
        vt = settings.virality_threshold * (wl.get("roi_threshold", 1.0) if wl else 1.0)
        passes_prefilter = watchlist or virality >= vt

        astro_score = 0.0
        reasons: List[str] = []
        if passes_prefilter:
            signals = item.astro_signals.model_dump() if item.astro_signals else {}
            astro = astro_detector.score(signals)
            astro_score = astro.score_0_10
            reasons.extend(astro.notes)

        # KPI decision
        kpi = kpi_decider.decide(
            views=float(base.get("views") or 0.0),
            growth_rate_24h=float(base.get("growth_rate_24h") or 0.0),
            harm_topic=item.harm_topic,
            harm_weight_override=item.harm_weight_override,
            astro_score=astro_score,
            avg_analyst_seconds=item.avg_analyst_seconds,
            salary_rate_per_hour=item.salary_rate_per_hour,
            client_max_cpr=item.client_max_cpr,
        )

        # Map KPI actions to routing actions
        if not passes_prefilter:
            action = "ARCHIVE"
        elif kpi.action == "HITL":
            action = "ALERT_HITL"
        elif kpi.action == "SEMI_HITL":
            action = "SEMI_HITL"
        else:
            action = "ARCHIVE"

        evidence = None
        if action != "ARCHIVE":
            provenance = {
                "platform": base.get("platform"),
                "content_id": base.get("content_id"),
                "content_url": base.get("content_url"),
                "author_username": base.get("author_username"),
            }
            evidence = evidence_archiver.archive(base, action, provenance=provenance)

        # QA sampling for low-score but high-spread (even if ARCHIVE)
        qa = qa_sampler.evaluate(base, astro_score)
        qa_selected = False
        if action == "ARCHIVE" and qa.selected:
            qa_selected = True
            evidence = evidence_archiver.archive(base, "QA_SAMPLE", provenance={
                "platform": base.get("platform"),
                "content_id": base.get("content_id"),
                "content_url": base.get("content_url"),
                "author_username": base.get("author_username"),
            })

        # Edge automation: enqueue verified items if enabled and action is HITL/SEMI
        if settings.auto_post_enabled and base.get("verified") and action in ("ALERT_HITL", "SEMI_HITL"):
            publisher.enqueue({
                "action": action,
                "content": base,
            })

        decisions.append(RouteDecision(
            action=action,
            watchlist=watchlist,
            astro_score=astro_score,
            virality_score=virality,
            reasons=reasons + [f"kpi:{kpi.reasons}", f"qa:{qa.reason}:{qa.projected_reach_48h}"],
            evidence=evidence,
            qa_selected=qa_selected,
        ))
    return decisions

@router.get("/playbooks")
async def list_playbooks():
    """Return all staff playbooks (L1–L3)."""
    return get_playbooks()

@router.get("/playbooks/{level}")
async def get_playbook_by_level(level: int):
    """Return a specific staff playbook level (1, 2, or 3)."""
    if level not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="level must be 1, 2, or 3")
    return get_playbook(level)

# KPI configuration endpoints
class HarmWeightUpsert(BaseModel):
    weight: float

@router.post("/kpi/harm/{topic}")
async def kpi_set_harm_weight(topic: str, body: HarmWeightUpsert):
    kpi_decider.set_harm_weight(topic, body.weight)
    return {"topic": topic, "weight": body.weight}

@router.get("/kpi/harm")
async def kpi_get_harm_weights():
    return {"harm_weights": kpi_decider.harm_weights}

# QA endpoints
@router.get("/qa/config")
async def qa_config():
    return {
        "qa_sample_rate": settings.qa_sample_rate,
        "qa_low_score_threshold": settings.qa_low_score_threshold,
        "qa_high_spread_projected_reach": settings.qa_high_spread_projected_reach,
    }

@router.get("/watchlists")
async def list_watchlists():
    return watchlists.list()

class WatchlistUpsert(BaseModel):
    topics: Optional[List[str]] = None
    accounts: Optional[List[str]] = None
    roi_threshold: Optional[float] = None

@router.post("/watchlists/{client}")
async def upsert_watchlist(client: str, body: WatchlistUpsert):
    wl = watchlists.upsert(client, {k: v for k, v in body.model_dump().items() if v is not None})
    return wl

class ThreatScoreRequest(BaseModel):
    virality_score: float
    harm_potential: float
    astro_score: float

class ThreatScoreResponse(BaseModel):
    score_0_10: float
    components: Dict[str, float]
    weights: Dict[str, float]

@router.post("/threat/score", response_model=ThreatScoreResponse)
async def threat_score(body: ThreatScoreRequest):
    s = threat_ensemble.score(body.virality_score, body.harm_potential, body.astro_score)
    return ThreatScoreResponse(score_0_10=s.score_0_10, components=s.components, weights=s.weights)

# Capacity estimation
class CapacityEstimateRequest(BaseModel):
    items_per_day: int
    pct_alert: float = 0.1
    pct_semi: float = 0.2
    avg_seconds_l1: int = 60
    avg_seconds_l2: int = 300
    avg_seconds_l3: int = 900
    analyst_hours_per_day: float = 6.5

class CapacityEstimateResponse(BaseModel):
    total_seconds: int
    analysts_needed: float
    breakdown: Dict[str, int]

@router.post("/capacity/estimate", response_model=CapacityEstimateResponse)
async def capacity_estimate(body: CapacityEstimateRequest):
    alerts = int(body.items_per_day * body.pct_alert)
    semis = int(body.items_per_day * body.pct_semi)
    l1 = body.items_per_day  # triage pass for all
    total_seconds = l1 * body.avg_seconds_l1 + semis * body.avg_seconds_l2 + alerts * body.avg_seconds_l3
    analysts_needed = round(total_seconds / (body.analyst_hours_per_day * 3600.0), 2)
    return CapacityEstimateResponse(
        total_seconds=total_seconds,
        analysts_needed=analysts_needed,
        breakdown={
            "l1_seconds": l1 * body.avg_seconds_l1,
            "l2_seconds": semis * body.avg_seconds_l2,
            "l3_seconds": alerts * body.avg_seconds_l3,
        },
    )

# Staff model suggestion
@router.get("/staff/model")
async def staff_model():
    return {
        "suggested_ratios": {
            "senior_analysts": 1,
            "investigators_on_call": 1,
            "junior_triage": 4
        },
        "notes": "Small senior core, larger junior pool, on-call investigators."
    }

# Quick-triage UI endpoints
class TriageItemRequest(BaseModel):
    content_id: str
    content_text: str
    content_url: Optional[str] = None
    platform: Optional[str] = None
    author_username: Optional[str] = None
    views: Optional[int] = 0
    growth_rate_24h: Optional[float] = 0.0
    author_followers: Optional[int] = 0
    follower_spike_24h: Optional[float] = 0.0
    astro_signals: Optional[AstroSignals] = None

class TriageItemResponse(BaseModel):
    content_id: str
    verdict: str  # "true" | "misleading" | "unsupported" | "manipulated"
    priority: str  # "high" | "medium" | "low"
    watchlist: bool
    astro_score: float
    virality_score: float
    projected_reach_48h: float
    top_sources: List[Dict]  # top 5 sources (would come from fact-check)
    network_cluster: Optional[Dict] = None  # compact graph view
    suggested_templates: List[str]  # 1-click reply templates
    escalate_flag: bool = False

class TriageActionRequest(BaseModel):
    content_id: str
    action: str  # approve | edit | escalate | archive
    analyst: str
    time_spent_seconds: int
    template_text: Optional[str] = None
    sources: Optional[List[Dict]] = None
    enqueue_avatar: Optional[bool] = True
    verified: Optional[bool] = True

class TriageActionResponse(BaseModel):
    ok: bool
    queued: bool
    clipboard_text: Optional[str] = None
    audit_id: Optional[str] = None

@router.post("/triage/item", response_model=TriageItemResponse)
async def triage_item(body: TriageItemRequest):
    """Quick-triage screen: side-by-side view with sources, network miniature, templates."""
    base = body.model_dump()
    virality = social_monitor.virality_score(base)
    prioritized = social_monitor.prioritize_batch([base])[0]
    
    # Compute astro score
    astro_score = 0.0
    if body.astro_signals:
        astro_result = astro_detector.score(body.astro_signals.model_dump())
        astro_score = astro_result.score_0_10
    
    # Projected reach
    projected = kpi_decider.estimate_projected_reach_48h(base.get("views") or 0.0, base.get("growth_rate_24h") or 0.0)
    
    # Network cluster (compact view - would fetch related items in real implementation)
    network_cluster = None
    if base.get("author_username"):
        network_cluster = {
            "nodes": 1,
            "edges": 0,
            "cluster_id": "single",
            "note": "Full graph analysis requires batch of related items"
        }
    
    # Suggested templates (from L1 playbook)
    templates = []
    playbook = get_playbook(1)
    if "templates" in playbook:
        templates = list(playbook["templates"].values())[:3]
    
    # Verdict suggestion (based on scores)
    verdict = "unsupported"
    if astro_score >= 8.0:
        verdict = "manipulated"
    elif astro_score >= 5.0:
        verdict = "misleading"
    elif virality > 7.0:
        verdict = "misleading"
    
    return TriageItemResponse(
        content_id=body.content_id,
        verdict=verdict,
        priority=prioritized.priority,
        watchlist=prioritized.watchlist,
        astro_score=astro_score,
        virality_score=virality,
        projected_reach_48h=projected,
        top_sources=[],  # Would come from fact-check API call in real implementation
        network_cluster=network_cluster,
        suggested_templates=templates,
        escalate_flag=prioritized.priority == "high",
    )

@router.post("/triage/batch", response_model=List[TriageItemResponse])
async def triage_batch(items: List[TriageItemRequest]):
    """Batch triage for multiple items."""
    return [await triage_item(item) for item in items]

@router.post("/triage/action", response_model=TriageActionResponse)
async def triage_action(body: TriageActionRequest):
    # Build clipboard-ready text if approving or editing
    queued = False
    clipboard = None
    if body.action in ("approve", "edit") and body.template_text:
        srcs = body.sources or []
        links = "\n".join([f"- {s.get('title','Source')}: {s.get('url','')}" for s in srcs[:5]])
        clipboard = f"{body.template_text}\n\nSources:\n{links}" if links else body.template_text

    # Optionally enqueue for avatar publish on approve
    if settings.auto_post_enabled and body.action == "approve" and body.enqueue_avatar and body.verified:
        publisher.enqueue({
            "content_id": body.content_id,
            "template_text": body.template_text,
            "sources": body.sources or [],
            "verified": True,
        })
        queued = True

    # Audit record
    auditor.write({
        "type": "triage_action",
        "content_id": body.content_id,
        "action": body.action,
        "analyst": body.analyst,
        "time_spent_seconds": body.time_spent_seconds,
        "queued": queued,
    })

    return TriageActionResponse(ok=True, queued=queued, clipboard_text=clipboard)

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
        
        # Analyze + prioritize for watchlist + route decisions
        if content_batch:
            prioritized = social_monitor.prioritize_batch(content_batch)
            watchlist_items = [p for p in prioritized if p.watchlist]

            # Build pipeline items with minimal features; astro signals left empty for now
            pipeline_items = []
            for raw in content_batch:
                pipeline_items.append(PipelineItem(
                    platform=raw.get("platform"),
                    content_id=raw.get("content_id"),
                    content_text=raw.get("content_text"),
                    content_url=raw.get("content_url"),
                    author_username=raw.get("author_username"),
                    views=raw.get("views") or 0,
                    growth_rate_24h=raw.get("growth_rate_24h") or 0.0,
                    author_followers=(raw.get("engagement") or {}).get("author_followers", 0),
                    follower_spike_24h=raw.get("follower_spike_24h") or 0.0,
                ))

            decisions = await pipeline_route(pipeline_items)  # reuse logic
            counts = {"ALERT_HITL": 0, "SEMI_HITL": 0, "ARCHIVE": 0}
            for d in decisions:
                counts[d.action] += 1

            logger.info(
                f"📊 Routed {len(content_batch)} items for {client_name}: "
                f"alerts={counts['ALERT_HITL']}, semi={counts['SEMI_HITL']}, archive={counts['ARCHIVE']}"
            )
        
        logger.info(f"✅ Background monitoring completed for {client_name}")
        
    except Exception as e:
        logger.error(f"Background monitoring error for {client_name}: {e}")