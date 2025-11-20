from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from src.core.content_templates import claim_vs_proof_script, investigative_thread
from src.core.publish import PublishQueue
from src.core.config import settings


router = APIRouter(prefix="/api/v1/content", tags=["Content Amplification"])
publish_queue = PublishQueue()


class Proof(BaseModel):
    title: str
    url: str


class ClaimVsProofRequest(BaseModel):
    claim: str
    proofs: List[Proof]
    persona: str = "GuardianAvatar"
    language: str = Field(default="en", pattern="^(en|de)$")
    brand_name: Optional[str] = None
    co_brand: bool = False


@router.post("/amplify/claim-vs-proof")
async def amplify_claim_vs_proof(body: ClaimVsProofRequest):
    try:
        out = claim_vs_proof_script(
            claim=body.claim,
            proofs=[p.model_dump() for p in body.proofs],
            persona=body.persona,
            language=body.language,
            brand_name=body.brand_name,
            co_brand=body.co_brand,
        )
        if settings.transparency_required:
            out["transparency_notice"] = (
                settings.transparency_label_de if body.language == "de" else settings.transparency_label_en
            )
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class Source(BaseModel):
    title: str
    url: str


class InvestigativeThreadRequest(BaseModel):
    topic: str
    key_findings: List[str]
    sources: List[Source]
    astro_score: Optional[float] = None
    persona: str = "GuardianAvatar"
    language: str = Field(default="en", pattern="^(en|de)$")
    brand_name: Optional[str] = None
    co_brand: bool = False


@router.post("/amplify/investigative-thread")
async def amplify_investigative_thread(body: InvestigativeThreadRequest):
    try:
        out = investigative_thread(
            topic=body.topic,
            key_findings=body.key_findings,
            sources=[s.model_dump() for s in body.sources],
            astro_score=body.astro_score,
            persona=body.persona,
            language=body.language,
            brand_name=body.brand_name,
            co_brand=body.co_brand,
        )
        if settings.transparency_required:
            out["transparency_notice"] = (
                settings.transparency_label_de if body.language == "de" else settings.transparency_label_en
            )
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/amplify/formats")
async def list_formats():
    return {
        "formats": [
            "claim_vs_proof",
            "investigative_thread",
        ],
        "personas": [
            "GuardianAvatar",
            "PolicyAvatar",
            "MemeAvatar",
            "EuroShieldAvatar",
            "ScienceAvatar",
        ],
        "languages": ["en", "de"],
    }


class PublishEnqueueRequest(BaseModel):
    content: Dict
    verified: bool = False


@router.post("/publish/enqueue")
async def publish_enqueue(body: PublishEnqueueRequest):
    if not settings.auto_post_enabled:
        return {"auto_post_enabled": False, "queued": False}
    if not body.verified:
        return {"auto_post_enabled": True, "queued": False, "reason": "not_verified"}
    entry = publish_queue.enqueue({"content": body.content, "verified": True})
    return {"queued": True, "entry": entry}

@router.get("/publish/queue")
async def publish_list():
    return {"items": publish_queue.list()}



