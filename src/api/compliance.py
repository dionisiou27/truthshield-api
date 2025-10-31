from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict

from src.core.config import settings


router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance & Ethics"])


class TransparencyConfig(BaseModel):
    transparency_required: bool
    transparency_label_en: str = Field(min_length=3)
    transparency_label_de: str = Field(min_length=3)


@router.get("/transparency", response_model=TransparencyConfig)
async def get_transparency():
    return TransparencyConfig(
        transparency_required=settings.transparency_required,
        transparency_label_en=settings.transparency_label_en,
        transparency_label_de=settings.transparency_label_de,
    )


@router.post("/transparency", response_model=TransparencyConfig)
async def set_transparency(cfg: TransparencyConfig):
    # Update runtime settings (process-level; persist externally if needed)
    settings.transparency_required = cfg.transparency_required
    settings.transparency_label_en = cfg.transparency_label_en
    settings.transparency_label_de = cfg.transparency_label_de
    return cfg


@router.get("/dpa/clauses")
async def dpa_clauses():
    return {
        "contact": settings.dpa_contact_email,
        "ownership_models": [
            {"key": "client", "desc": "Client owns content; TruthShield license to operate."},
            {"key": "truthshield", "desc": "TruthShield owns avatar IP; client usage rights granted."},
            {"key": "cobrand", "desc": "Co-branded ownership; shared rights as specified."},
        ],
        "example_clauses": [
            "Data Processing Addendum (DPA) including purpose limitation and retention.",
            "Content ownership and licensing per selected ownership model.",
            "Transparency and disclosure obligations for automated content.",
            "Audit and evidence preservation: hashed archives and export on request.",
        ],
    }


