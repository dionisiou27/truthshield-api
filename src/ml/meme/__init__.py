"""
TruthShield Meme Generator
==========================

Inoculation memes for cognitive security.

Converts disinformation narratives + fact-checks into viral, shareable memes.

Components:
-----------
- MemeConceptGenerator: LLM-driven concept creation
- TemplateSelector: Meme template selection logic
- ImageRenderer: Programmatic PNG rendering with Pillow

Usage:
------
    from src.ml.meme import generate_meme

    meme_bytes = await generate_meme(
        narrative="Die EU plant, Fleisch zu verbieten!",
        fact_basis="Kein EU-Verbot. Nur Subventions-Anpassung.",
        sources=["EU Kommission", "DW Faktencheck"]
    )

Architecture:
-------------
    Claim → LLM Concept → Template → Render → PNG
       ↓         ↓          ↓         ↓        ↓
   ClaimRouter  GPT-4   TEMPLATES  Pillow  Storage

Safety:
-------
- No ad hominem attacks (LLM filtered)
- Source citations required (programmatically rendered)
- Tone adaptation (ML-driven via bandit)
- Human review for CRITICAL risk claims
"""

from pydantic import BaseModel
from typing import Dict
from src.ml.learning.bandit import ToneVariant


class MemeSpec(BaseModel):
    """
    Meme specification from LLM.

    Defines the visual template and text content for meme rendering.
    """
    visual_template: str        # Template name (e.g., "drake", "panik_kalm")
    top_text: str               # Hook text (emotional/narrative reference)
    bottom_text: str            # Payload text (hard fact, max 10-12 words)
    footer: str                 # Source citation (e.g., "Quellen: EZB | Reuters")
    tone: ToneVariant           # EMPATHIC, WITTY, FIRM, SPICY
    aspect_ratio: str = "1:1"   # Image dimensions ("1:1" or "9:16")


class TemplateMetadata(BaseModel):
    """
    Template rendering metadata.

    Defines regions for text placement and rendering parameters.
    """
    file_path: str                          # Path to template image
    top_text_region: Dict[str, int]         # {x, y, w, h} for top text
    bottom_text_region: Dict[str, int]      # {x, y, w, h} for bottom text
    footer_region: Dict[str, int]           # {x, y, w, h} for footer
    watermark_position: str                 # "bottom_right" | "diagonal"
    aspect_ratio: str                       # "1:1" | "4:3" | "9:16"


__all__ = [
    "MemeSpec",
    "TemplateMetadata",
]

# Future exports (to be implemented):
# - MemeConceptGenerator
# - TemplateSelector
# - ImageRenderer
# - generate_meme (convenience function)
