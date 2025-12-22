# TruthShield Meme Generator - Quick Start Guide

## 🚀 Getting Started

This guide will walk you through implementing the TruthShield Meme Generator from scratch.

---

## 1. Prerequisites

### Install Dependencies

```bash
# Add to pyproject.toml
poetry add Pillow

# Or via pip
pip install Pillow
```

### Download Required Assets

**Fonts:**
```bash
# Create fonts directory
mkdir -p assets/fonts

# Download Impact font (free from Google Fonts)
# Option 1: Manual download from https://fonts.google.com/specimen/Impact
# Option 2: Use system font if available
cp /usr/share/fonts/truetype/msttcorefonts/impact.ttf assets/fonts/
```

**Meme Templates:**
```bash
# Create templates directory
mkdir -p assets/templates

# You'll need to acquire meme template images
# Recommended sources:
# - imgflip.com (download blank templates)
# - Make your own using design tools
# - Use public domain images
```

---

## 2. Project Structure Setup

```bash
# Create meme generator module
mkdir -p src/ml/meme

# Create storage for generated memes
mkdir -p demo_data/memes

# Create assets directories
mkdir -p assets/templates
mkdir -p assets/fonts
```

**Directory Tree:**
```
truthshield-api/
├── src/
│   └── ml/
│       └── meme/
│           ├── __init__.py
│           ├── concept_generator.py    # LLM concept creation
│           ├── template_selector.py    # Template logic
│           └── image_renderer.py       # PNG rendering
├── assets/
│   ├── templates/                      # Base meme images
│   │   ├── drake.png
│   │   ├── panik_kalm.png
│   │   └── ...
│   ├── fonts/                          # Typography
│   │   ├── impact.ttf
│   │   └── arial.ttf
│   └── watermark.png                   # TruthShield logo
└── demo_data/
    └── memes/                          # Generated output
        └── {uuid}.png
```

---

## 3. Implementation Steps

### Step 1: Create Data Models

**File:** `src/ml/meme/__init__.py`

```python
"""
TruthShield Meme Generator
Inoculation memes for cognitive security.
"""
from pydantic import BaseModel
from typing import Optional, Dict
from src.ml.learning.bandit import ToneVariant

class MemeSpec(BaseModel):
    """Meme specification from LLM."""
    visual_template: str        # Template name (e.g., "drake")
    top_text: str               # Hook text
    bottom_text: str            # Payload text
    footer: str                 # Source citation
    tone: ToneVariant           # EMPATHIC, WITTY, FACTUAL, FIRM
    aspect_ratio: str = "1:1"   # Image dimensions

class TemplateMetadata(BaseModel):
    """Template rendering metadata."""
    file_path: str
    top_text_region: Dict[str, int]     # {x, y, w, h}
    bottom_text_region: Dict[str, int]  # {x, y, w, h}
    footer_region: Dict[str, int]       # {x, y, w, h}
    watermark_position: str             # "bottom_right" | "diagonal"
    aspect_ratio: str

__all__ = ["MemeSpec", "TemplateMetadata"]
```

---

### Step 2: Implement Template Selector

**File:** `src/ml/meme/template_selector.py`

```python
"""
Meme Template Selector
Maps template names to image assets and metadata.
"""
from typing import Dict, Optional
import os
from .models import TemplateMetadata

# Template Registry
MEME_TEMPLATES: Dict[str, Dict] = {
    "drake": {
        "file": "assets/templates/drake.png",
        "top_text_region": {"x": 350, "y": 80, "w": 300, "h": 150},
        "bottom_text_region": {"x": 350, "y": 280, "w": 300, "h": 150},
        "footer_region": {"x": 0, "y": 450, "w": 650, "h": 50},
        "watermark_position": "bottom_right",
        "aspect_ratio": "1:1"
    },
    "panik_kalm": {
        "file": "assets/templates/panik_kalm.png",
        "top_text_region": {"x": 50, "y": 50, "w": 400, "h": 150},
        "bottom_text_region": {"x": 50, "y": 350, "w": 400, "h": 150},
        "footer_region": {"x": 0, "y": 550, "w": 500, "h": 50},
        "watermark_position": "bottom_right",
        "aspect_ratio": "1:1"
    },
    "distracted_boyfriend": {
        "file": "assets/templates/distracted_boyfriend.png",
        "top_text_region": {"x": 50, "y": 20, "w": 250, "h": 100},
        "bottom_text_region": {"x": 350, "y": 20, "w": 250, "h": 100},
        "footer_region": {"x": 0, "y": 550, "w": 650, "h": 50},
        "watermark_position": "bottom_right",
        "aspect_ratio": "4:3"
    },
    # Add more templates as needed
}

class TemplateSelector:
    """Selects and validates meme templates."""

    def __init__(self, template_dir: str = "assets/templates"):
        self.template_dir = template_dir

    def get_template(self, template_name: str) -> TemplateMetadata:
        """
        Retrieve template metadata.

        Args:
            template_name: Name of the meme template (e.g., "drake")

        Returns:
            TemplateMetadata with file path and rendering regions

        Raises:
            ValueError: If template not found
        """
        template_name = template_name.lower().replace(" ", "_")

        if template_name not in MEME_TEMPLATES:
            raise ValueError(
                f"Template '{template_name}' not found. "
                f"Available: {list(MEME_TEMPLATES.keys())}"
            )

        config = MEME_TEMPLATES[template_name]

        # Validate file exists
        if not os.path.exists(config["file"]):
            raise FileNotFoundError(
                f"Template image not found: {config['file']}"
            )

        return TemplateMetadata(
            file_path=config["file"],
            top_text_region=config["top_text_region"],
            bottom_text_region=config["bottom_text_region"],
            footer_region=config["footer_region"],
            watermark_position=config["watermark_position"],
            aspect_ratio=config["aspect_ratio"]
        )

    def list_templates(self) -> list[str]:
        """List all available template names."""
        return list(MEME_TEMPLATES.keys())
```

---

### Step 3: Implement Image Renderer

**File:** `src/ml/meme/image_renderer.py`

```python
"""
Meme Image Renderer
Programmatic PNG generation with Pillow.
"""
import os
from io import BytesIO
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import logging

from .models import MemeSpec, TemplateMetadata

logger = logging.getLogger(__name__)

class ImageRenderer:
    """Renders meme images with text overlays."""

    def __init__(
        self,
        font_dir: str = "assets/fonts",
        watermark_path: str = "assets/watermark.png"
    ):
        self.font_dir = font_dir
        self.watermark_path = watermark_path

        # Load fonts
        try:
            self.impact_font = ImageFont.truetype(
                os.path.join(font_dir, "impact.ttf"), 48
            )
            self.impact_font_small = ImageFont.truetype(
                os.path.join(font_dir, "impact.ttf"), 36
            )
            self.footer_font = ImageFont.truetype(
                os.path.join(font_dir, "arial.ttf"), 18
            )
        except Exception as e:
            logger.warning(f"Font loading failed: {e}. Using default font.")
            self.impact_font = ImageFont.load_default()
            self.impact_font_small = ImageFont.load_default()
            self.footer_font = ImageFont.load_default()

        # Load watermark
        if os.path.exists(watermark_path):
            self.watermark = Image.open(watermark_path).convert("RGBA")
        else:
            logger.warning(f"Watermark not found: {watermark_path}")
            self.watermark = None

    async def render_meme(
        self,
        template_meta: TemplateMetadata,
        meme_spec: MemeSpec
    ) -> bytes:
        """
        Render final meme image as PNG bytes.

        Args:
            template_meta: Template metadata with regions
            meme_spec: Meme specification with text

        Returns:
            PNG image as bytes
        """
        # Load base template
        base_image = Image.open(template_meta.file_path).convert("RGBA")
        draw = ImageDraw.Draw(base_image)

        # Draw top text
        self._draw_meme_text(
            draw,
            meme_spec.top_text,
            template_meta.top_text_region,
            self.impact_font
        )

        # Draw bottom text
        self._draw_meme_text(
            draw,
            meme_spec.bottom_text,
            template_meta.bottom_text_region,
            self.impact_font
        )

        # Draw footer
        self._draw_footer(
            draw,
            meme_spec.footer,
            template_meta.footer_region,
            base_image.width
        )

        # Add watermark
        if self.watermark:
            self._add_watermark(
                base_image,
                template_meta.watermark_position
            )

        # Convert to RGB and save as PNG
        output_image = base_image.convert("RGB")
        buffer = BytesIO()
        output_image.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)

        return buffer.getvalue()

    def _draw_meme_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        region: dict,
        font: ImageFont.FreeTypeFont
    ):
        """
        Draw meme text with white fill and black stroke.

        Classic Impact font style with outline.
        """
        x, y = region["x"], region["y"]
        w, h = region["w"], region["h"]

        # Center text in region
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate centered position
        text_x = x + (w - text_width) // 2
        text_y = y + (h - text_height) // 2

        # Draw black stroke (outline)
        stroke_width = 2
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                draw.text(
                    (text_x + offset_x, text_y + offset_y),
                    text,
                    font=font,
                    fill="black"
                )

        # Draw white text on top
        draw.text((text_x, text_y), text, font=font, fill="white")

    def _draw_footer(
        self,
        draw: ImageDraw.ImageDraw,
        footer_text: str,
        region: dict,
        image_width: int
    ):
        """
        Draw footer with source citation.

        Uses smaller sans-serif font on dark background.
        """
        x, y = region["x"], region["y"]
        h = region["h"]

        # Draw dark background bar
        draw.rectangle(
            [(0, y), (image_width, y + h)],
            fill=(0, 0, 0, 180)  # Semi-transparent black
        )

        # Draw footer text
        bbox = draw.textbbox((0, 0), footer_text, font=self.footer_font)
        text_width = bbox[2] - bbox[0]
        text_x = (image_width - text_width) // 2
        text_y = y + (h - (bbox[3] - bbox[1])) // 2

        draw.text(
            (text_x, text_y),
            footer_text,
            font=self.footer_font,
            fill="white"
        )

    def _add_watermark(
        self,
        base_image: Image.Image,
        position: str
    ):
        """
        Add semi-transparent watermark.

        Positions: "bottom_right" or "diagonal"
        """
        if not self.watermark:
            return

        # Resize watermark to fit
        watermark = self.watermark.copy()
        watermark.thumbnail((200, 50))

        # Set transparency
        watermark.putalpha(int(255 * 0.4))  # 40% opacity

        if position == "bottom_right":
            # Bottom right corner
            pos = (
                base_image.width - watermark.width - 10,
                base_image.height - watermark.height - 10
            )
        else:
            # Diagonal (center-bottom-right)
            pos = (
                base_image.width - watermark.width - 50,
                base_image.height - watermark.height - 50
            )

        base_image.paste(watermark, pos, watermark)
```

---

### Step 4: Implement Concept Generator

**File:** `src/ml/meme/concept_generator.py`

```python
"""
Meme Concept Generator
LLM-driven meme concept creation.
"""
import json
import logging
from typing import List
import openai

from src.ml.guardian.claim_router import ClaimAnalysis, RiskLevel, ClaimType
from src.ml.learning.bandit import ToneVariant
from src.core.ai_engine import Source
from .models import MemeSpec

logger = logging.getLogger(__name__)

COGNITIVE_SECURITY_PROMPT = """Du bist der "Cognitive Security Architect" für TruthShield.

AUFGABE:
Erstelle ein Meme-Konzept, das eine Desinformations-Narrative entlarvt, OHNE Personen anzugreifen.

INPUT:
- Narrativ: {narrative}
- Fakten: {fact_basis}
- Quellen: {sources}
- Tone: {tone}

OUTPUT FORMAT (JSON):
{{
  "visual_template": "[Meme-Format Name aus: drake, panik_kalm, distracted_boyfriend]",
  "top_text": "[Hook, max 40 Zeichen]",
  "bottom_text": "[Payload, max 60 Zeichen]",
  "footer": "[Quelle, formatiert]",
  "tone": "{tone}"
}}

REGELN:
1. Keine Angriffe auf Parteien/Personen
2. Fokus auf METHODEN (Cherrypicking, Whataboutism, Panikmache)
3. Tone EMPATHIC für Health/Science, WITTY für Conspiracy
4. Footer IMMER mit echten Quellen (max 3, getrennt mit |)
5. Text muss kurz, viral, und TikTok-geeignet sein

BEISPIEL:
Input:
  Narrativ: "Die Wirtschaft kollabiert total!"
  Fakten: "Inflation sinkt, DAX auf Rekord"
  Quellen: ["EZB", "Destatis"]
  Tone: "WITTY"

Output:
{{
  "visual_template": "panik_kalm",
  "top_text": "Telegram: 'Das Ende ist nah!'",
  "bottom_text": "Realität: Inflation 2%, Börse feiert",
  "footer": "Quellen: EZB | Destatis",
  "tone": "WITTY"
}}

WICHTIG: Antworte NUR mit JSON, kein zusätzlicher Text!
"""

class MemeConceptGenerator:
    """Generates meme concepts via LLM."""

    def __init__(self, openai_api_key: str = None):
        if openai_api_key:
            openai.api_key = openai_api_key

    async def generate_concept(
        self,
        claim_analysis: ClaimAnalysis,
        fact_basis: str,
        sources: List[Source],
        tone_override: ToneVariant = None
    ) -> MemeSpec:
        """
        Generate meme concept via GPT-4.

        Args:
            claim_analysis: Analyzed claim from ClaimRouter
            fact_basis: The factual correction
            sources: Authoritative sources for citation
            tone_override: Optional manual tone selection

        Returns:
            MemeSpec with template and text
        """
        # Determine tone
        tone = tone_override or self._select_tone(claim_analysis)

        # Format sources for prompt
        source_names = [
            s.title.split(" - ")[0][:30] for s in sources[:3]
        ]

        # Build prompt
        prompt = COGNITIVE_SECURITY_PROMPT.format(
            narrative=claim_analysis.normalized_claim,
            fact_basis=fact_basis,
            sources=", ".join(source_names),
            tone=tone.value
        )

        try:
            # Call OpenAI with JSON mode
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "You are a meme concept generator."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=300
            )

            # Parse JSON response
            content = response.choices[0].message.content
            meme_data = json.loads(content)

            # Validate and create MemeSpec
            return MemeSpec(
                visual_template=meme_data["visual_template"],
                top_text=meme_data["top_text"],
                bottom_text=meme_data["bottom_text"],
                footer=meme_data["footer"],
                tone=ToneVariant(meme_data["tone"])
            )

        except Exception as e:
            logger.error(f"Meme concept generation failed: {e}")
            # Fallback to template-based generation
            return self._fallback_concept(claim_analysis, fact_basis, sources, tone)

    def _select_tone(self, claim_analysis: ClaimAnalysis) -> ToneVariant:
        """
        Select appropriate tone based on claim analysis.

        Logic:
        - CRITICAL/HIGH risk → FIRM (no humor)
        - Health/Science → EMPATHIC
        - Conspiracy → WITTY
        - Default → FACTUAL
        """
        if claim_analysis.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return ToneVariant.FIRM

        claim_types = claim_analysis.claim_types
        if ClaimType.HEALTH_MISINFORMATION in claim_types:
            return ToneVariant.EMPATHIC
        if ClaimType.CONSPIRACY_THEORY in claim_types:
            return ToneVariant.WITTY

        return ToneVariant.FIRM  # Default to factual

    def _fallback_concept(
        self,
        claim_analysis: ClaimAnalysis,
        fact_basis: str,
        sources: List[Source],
        tone: ToneVariant
    ) -> MemeSpec:
        """
        Fallback template-based meme when LLM fails.
        """
        logger.warning("Using fallback meme concept")

        # Simple template
        source_line = " | ".join([
            s.title.split(" - ")[0][:20] for s in sources[:3]
        ])

        return MemeSpec(
            visual_template="drake",
            top_text="Desinformation",
            bottom_text="Fakten prüfen!",
            footer=f"Quellen: {source_line}",
            tone=tone
        )
```

---

## 4. Testing Your Implementation

### Quick Test Script

**File:** `tests/ml/meme/test_meme_generator.py`

```python
"""
Quick test for meme generator.
"""
import asyncio
from src.ml.meme.concept_generator import MemeConceptGenerator
from src.ml.meme.template_selector import TemplateSelector
from src.ml.meme.image_renderer import ImageRenderer
from src.ml.guardian.claim_router import ClaimRouter
from src.core.ai_engine import Source

async def test_meme_generation():
    """Test full meme generation pipeline."""

    # Sample claim
    claim_text = "Die EU plant, Fleisch zu verbieten!"

    # Analyze claim
    router = ClaimRouter()
    claim_analysis = router.analyze_claim(claim_text)

    # Mock sources
    sources = [
        Source(
            url="https://ec.europa.eu/food/farm-fork-strategy_en",
            title="EU Farm-to-Fork Strategy",
            snippet="Sustainable food system",
            credibility_score=1.0
        ),
        Source(
            url="https://www.dw.com/de/faktencheck-eu-fleischverbot/a-123",
            title="DW Faktencheck: EU Fleischverbot",
            snippet="Kein Verbot geplant",
            credibility_score=0.9
        )
    ]

    # Generate concept
    concept_gen = MemeConceptGenerator()
    meme_spec = await concept_gen.generate_concept(
        claim_analysis=claim_analysis,
        fact_basis="Kein EU-Verbot. Nur Subventions-Anpassung.",
        sources=sources
    )

    print(f"Generated Meme Spec:")
    print(f"  Template: {meme_spec.visual_template}")
    print(f"  Top: {meme_spec.top_text}")
    print(f"  Bottom: {meme_spec.bottom_text}")
    print(f"  Footer: {meme_spec.footer}")
    print(f"  Tone: {meme_spec.tone}")

    # Select template
    template_sel = TemplateSelector()
    template_meta = template_sel.get_template(meme_spec.visual_template)

    # Render image
    renderer = ImageRenderer()
    image_bytes = await renderer.render_meme(template_meta, meme_spec)

    # Save output
    output_path = "demo_data/memes/test_meme.png"
    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"✅ Meme saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_meme_generation())
```

**Run:**
```bash
python tests/ml/meme/test_meme_generator.py
```

---

## 5. Next Steps

### Immediate Actions

1. **Acquire Assets:**
   - Download 5 meme template images
   - Download Impact font
   - Create TruthShield watermark PNG

2. **Test Rendering:**
   - Run test script above
   - Verify text is readable
   - Check watermark visibility

3. **Tune LLM Prompt:**
   - Test with 10 different claims
   - Adjust prompt for tone appropriateness
   - Add edge case handling

### Production Readiness

4. **Add API Endpoint:**
   - See `docs/MEME_GENERATOR_PLAN.md` Section 4
   - Implement `/api/v1/meme/generate`
   - Add rate limiting

5. **Quality Assurance:**
   - Manual review queue for CRITICAL risk
   - Ad hominem detection filter
   - Source accuracy validation

6. **Scaling:**
   - CDN integration for image serving
   - Batch generation CLI tool
   - Performance optimization

---

## 6. Troubleshooting

### Font Not Found

**Error:** `OSError: cannot open resource`

**Solution:**
```bash
# Check font path
ls assets/fonts/impact.ttf

# If missing, download from:
# https://fonts.google.com/specimen/Impact

# Or use fallback
# Edit image_renderer.py to use default font
```

### Template Not Found

**Error:** `FileNotFoundError: Template image not found`

**Solution:**
```bash
# Check template exists
ls assets/templates/drake.png

# Add placeholder templates
# Use solid color images for testing
```

### LLM Timeout

**Error:** `openai.error.Timeout`

**Solution:**
```python
# Add retry logic in concept_generator.py
# Or use fallback template
```

---

## 7. Resources

### Meme Template Sources
- **Imgflip:** https://imgflip.com/memetemplates
- **Know Your Meme:** https://knowyourmeme.com/
- **Meme Generator:** https://memegenerator.net/

### Fonts
- **Impact Font:** https://fonts.google.com/specimen/Impact
- **Anton (Impact Alternative):** https://fonts.google.com/specimen/Anton

### Design Tools
- **Create Watermark:** https://www.canva.com/
- **Image Editing:** GIMP, Photoshop

---

**Ready to implement? Start with Phase 1 in the main plan!**

**Questions? Check `docs/MEME_GENERATOR_PLAN.md` for full architecture.**
