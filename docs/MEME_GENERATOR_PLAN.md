# TruthShield Meme Generator - Implementation Plan

## Executive Summary

Integration of an "Inoculation Meme" (Impf-Meme) Generator in TruthShield API to transform factual debunking information into viral, shareable memes that build digital resilience through humor and facts.

**Status:** PLANNING PHASE
**Target:** Production-ready API endpoint + CLI tooling
**Architecture:** LLM-driven concept generation + Programmatic image rendering

---

## 1. SYSTEM OVERVIEW

### 1.1 Core Concept: "Cognitive Security Architect"

The Meme Generator role:
- **Input:** Narrative (false claim), Fact basis (correction), Source (institution)
- **Output:** Meme specification in TruthShield format
- **Objective:** Expose disinformation/logic errors WITHOUT ad hominem attacks
- **Method:** Use known meme templates + witty/empathic/factual tone

### 1.2 Output Format ("TruthShield-Format")

```python
MemeSpec:
  - visual_template: str        # e.g., "Drake", "Distracted Boyfriend", "Panik/Kalm"
  - top_text: str               # Hook (emotional/narrative reference)
  - bottom_text: str            # Payload (hard fact, max 10-12 words)
  - footer: str                 # Source citation (e.g., "Quelle: Destatis | Reuters")
  - tone: ToneVariant           # WITTY, EMPATHIC, FACTUAL
  - aspect_ratio: str           # "1:1" or "9:16"
```

### 1.3 Quality Safeguards

✅ **Allowed:**
- Attack METHODS (cherrypicking, whataboutism)
- Attack DATA inconsistencies
- Use humor to expose logical fallacies

❌ **Forbidden:**
- Ad hominem attacks on individuals or parties
- Cynicism toward victims
- Tone-deaf humor on sensitive topics (hate speech, violence)

---

## 2. ARCHITECTURE DESIGN

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MEME GENERATOR PIPELINE                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   STEP 1:    │───▶│   STEP 2:    │───▶│   STEP 3:    │  │
│  │ Meme Concept │    │   Template   │    │    Image     │  │
│  │  Generator   │    │   Selector   │    │   Renderer   │  │
│  │   (LLM)      │    │   (Logic)    │    │  (Pillow)    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         ▲                                           │
         │                                           ▼
┌────────────────────┐                    ┌───────────────────┐
│  Guardian Pipeline │                    │  Static Asset DB  │
│  (Claim Analysis)  │                    │  (Meme Templates) │
└────────────────────┘                    └───────────────────┘
```

### 2.2 Integration with Existing TruthShield Components

**Leverage Existing:**
1. **ClaimRouter** (`src/ml/guardian/claim_router.py`)
   - Already classifies claim types, risk levels, narratives
   - Use `ClaimAnalysis` to inform meme tone selection

2. **SourceRanker** (`src/ml/guardian/source_ranker.py`)
   - Already retrieves and ranks authoritative sources
   - Use top sources for footer citations

3. **GuardianBandit** (`src/ml/learning/bandit.py`)
   - Already manages tone variants (EMPATHIC, WITTY, FIRM, SPICY)
   - Reuse tone selection logic for meme tone

4. **AI Engine** (`src/core/ai_engine.py`)
   - Already has OpenAI integration
   - Extend with Meme Concept Generator prompt

**New Components:**
1. **MemeConceptGenerator** - LLM-driven concept creation
2. **TemplateSelector** - Logic for meme format selection
3. **ImageRenderer** - Programmatic PNG generation
4. **MemeTemplateDB** - Asset storage for base images

---

## 3. DETAILED COMPONENT SPECIFICATIONS

### 3.1 MemeConceptGenerator (LLM)

**File:** `src/ml/meme/concept_generator.py`

**Responsibilities:**
- Receive claim analysis + fact basis + sources
- Generate creative meme concept via GPT-4
- Output structured `MemeSpec` object

**Prompt Template:**
```python
SYSTEM_PROMPT = """
Du bist der "Cognitive Security Architect" für TruthShield.
Deine Aufgabe: Erstelle ein Meme-Konzept, das eine Desinformations-Narrative
entlarvt, OHNE Personen anzugreifen.

INPUT: Narrativ, Fakten, Quelle
OUTPUT: JSON mit folgenden Feldern:
- visual_template: [Meme-Format Name]
- top_text: [Hook, max 40 Zeichen]
- bottom_text: [Payload, max 60 Zeichen]
- footer: [Quelle, formatiert]
- tone: [WITTY|EMPATHIC|FACTUAL]

REGELN:
- Keine Angriffe auf Parteien/Personen
- Fokus auf METHODEN (Cherrypicking, Whataboutism)
- Tone EMPATHIC für Health/Science, WITTY für Conspiracy
- Footer IMMER mit echten Quellen

BEISPIEL:
Input: "Narrativ: Wirtschaft kollabiert. Fakt: Inflation sinkt, DAX Rekord. Quelle: EZB"
Output:
{
  "visual_template": "panik_kalm",
  "top_text": "Telegram: 'Das Ende ist nah!'",
  "bottom_text": "Realität: Inflation 2%, Börse feiert",
  "footer": "Quelle: EZB Monatsbericht 11/2024",
  "tone": "WITTY"
}
"""
```

**API:**
```python
class MemeSpec(BaseModel):
    visual_template: str
    top_text: str
    bottom_text: str
    footer: str
    tone: ToneVariant
    aspect_ratio: str = "1:1"

class MemeConceptGenerator:
    async def generate_concept(
        self,
        claim_analysis: ClaimAnalysis,
        fact_basis: str,
        sources: List[Source]
    ) -> MemeSpec:
        """Generate meme concept via LLM."""
```

---

### 3.2 TemplateSelector (Logic)

**File:** `src/ml/meme/template_selector.py`

**Responsibilities:**
- Map `visual_template` name to actual base image
- Validate template exists in asset DB
- Return template metadata (text positions, font sizes)

**Template Registry:**
```python
MEME_TEMPLATES = {
    "drake": {
        "file": "assets/templates/drake.png",
        "top_text_region": {"x": 350, "y": 50, "w": 300, "h": 150},
        "bottom_text_region": {"x": 350, "y": 250, "w": 300, "h": 150},
        "aspect_ratio": "1:1"
    },
    "distracted_boyfriend": {
        "file": "assets/templates/distracted_boyfriend.png",
        # ... similar metadata
    },
    "panik_kalm": {
        "file": "assets/templates/panik_kalm.png",
        # ...
    },
    # Add 10-15 popular meme formats
}
```

**API:**
```python
class TemplateMetadata(BaseModel):
    file_path: str
    top_text_region: Dict[str, int]
    bottom_text_region: Dict[str, int]
    footer_region: Dict[str, int]
    watermark_position: str  # "bottom_right" | "diagonal"

class TemplateSelector:
    def get_template(self, template_name: str) -> TemplateMetadata:
        """Retrieve template metadata."""
```

---

### 3.3 ImageRenderer (Pillow/OpenCV)

**File:** `src/ml/meme/image_renderer.py`

**Responsibilities:**
- Load base template image
- Render text (top/bottom/footer) with Impact font
- Add TruthShield.eu watermark
- Export high-quality PNG

**Text Rendering Specs:**
- **Top/Bottom Text:** Impact font, white fill, black stroke (2px)
- **Footer:** Sans-serif font (Arial/Helvetica), smaller size, white on dark bar
- **Watermark:** Semi-transparent PNG overlay, "TruthShield.eu"

**API:**
```python
class ImageRenderer:
    def __init__(self, font_dir: str = "assets/fonts"):
        self.impact_font = ImageFont.truetype(f"{font_dir}/impact.ttf", 48)
        self.footer_font = ImageFont.truetype(f"{font_dir}/arial.ttf", 18)
        self.watermark = Image.open("assets/watermark.png")

    async def render_meme(
        self,
        template_meta: TemplateMetadata,
        meme_spec: MemeSpec
    ) -> bytes:
        """
        Render final meme image as PNG bytes.

        Steps:
        1. Load base template
        2. Draw top_text with Impact font
        3. Draw bottom_text with Impact font
        4. Draw footer with sans-serif font
        5. Overlay watermark
        6. Return PNG bytes
        """
        # Implementation with Pillow
```

**Dependencies:**
```bash
pip install Pillow
```

---

### 3.4 MemeTemplateDB (Asset Storage)

**Directory Structure:**
```
assets/
├── templates/
│   ├── drake.png
│   ├── distracted_boyfriend.png
│   ├── panik_kalm.png
│   ├── spongebob_mocking.png
│   ├── lisa_simpson_presentation.png
│   ├── expanding_brain.png
│   ├── two_buttons.png
│   ├── change_my_mind.png
│   ├── is_this.png
│   ├── galaxy_brain.png
│   └── ...
├── fonts/
│   ├── impact.ttf
│   ├── arial.ttf
│   └── helvetica.ttf
└── watermark.png
```

**Template Acquisition Strategy:**
1. **Public Domain Memes:** Use CC0/public domain images
2. **Fair Use:** Meme templates typically fall under transformative fair use
3. **Fallback:** Create custom TruthShield-branded templates

---

## 4. API ENDPOINT DESIGN

### 4.1 New Endpoint: `/api/v1/meme/generate`

**File:** `src/api/meme.py`

**Request Schema:**
```python
class MemeGenerateRequest(BaseModel):
    narrative: str          # The false claim/disinformation
    fact_basis: str         # The correction/debunk
    sources: List[str]      # URLs of authoritative sources
    language: str = "de"    # Language for text
    tone_override: Optional[ToneVariant] = None  # Optional manual tone
```

**Response Schema:**
```python
class MemeGenerateResponse(BaseModel):
    meme_id: str                    # UUID for tracking
    meme_spec: MemeSpec             # The concept metadata
    image_url: str                  # CDN URL to rendered PNG
    image_base64: Optional[str]     # Inline base64 (optional)
    claim_analysis: Dict            # From ClaimRouter
    generation_time_ms: int
```

**Implementation:**
```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

router = APIRouter(prefix="/api/v1/meme", tags=["Meme Generator"])

@router.post("/generate")
async def generate_meme(request: MemeGenerateRequest):
    """
    Generate an inoculation meme from claim + facts + sources.

    Pipeline:
    1. Analyze claim (ClaimRouter)
    2. Rank sources (SourceRanker)
    3. Generate concept (MemeConceptGenerator)
    4. Select template (TemplateSelector)
    5. Render image (ImageRenderer)
    6. Save + return
    """
    try:
        start_time = time.time()

        # Step 1: Analyze claim
        claim_router = ClaimRouter()
        claim_analysis = claim_router.analyze_claim(request.narrative)

        # Step 2: Rank sources (use existing SourceRanker)
        # ... source ranking logic

        # Step 3: Generate concept
        concept_gen = MemeConceptGenerator()
        meme_spec = await concept_gen.generate_concept(
            claim_analysis=claim_analysis,
            fact_basis=request.fact_basis,
            sources=ranked_sources
        )

        # Step 4: Select template
        template_sel = TemplateSelector()
        template_meta = template_sel.get_template(meme_spec.visual_template)

        # Step 5: Render image
        renderer = ImageRenderer()
        image_bytes = await renderer.render_meme(template_meta, meme_spec)

        # Step 6: Save to disk/CDN
        meme_id = str(uuid.uuid4())
        image_path = f"demo_data/memes/{meme_id}.png"
        with open(image_path, "wb") as f:
            f.write(image_bytes)

        generation_time_ms = int((time.time() - start_time) * 1000)

        return {
            "meme_id": meme_id,
            "meme_spec": meme_spec.dict(),
            "image_url": f"/api/v1/meme/image/{meme_id}",
            "claim_analysis": claim_analysis.dict(),
            "generation_time_ms": generation_time_ms
        }

    except Exception as e:
        logger.error(f"Meme generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/{meme_id}")
async def get_meme_image(meme_id: str):
    """Serve rendered meme image."""
    image_path = f"demo_data/memes/{meme_id}.png"

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Meme not found")

    return FileResponse(image_path, media_type="image/png")


@router.get("/templates")
async def list_templates():
    """List all available meme templates."""
    from src.ml.meme.template_selector import MEME_TEMPLATES

    return {
        "templates": [
            {
                "name": name,
                "aspect_ratio": meta["aspect_ratio"],
                "preview_url": f"/api/v1/meme/template-preview/{name}"
            }
            for name, meta in MEME_TEMPLATES.items()
        ],
        "total": len(MEME_TEMPLATES)
    }
```

---

## 5. IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Week 1)
- [ ] Create `src/ml/meme/` directory structure
- [ ] Implement `MemeSpec` and `TemplateMetadata` models
- [ ] Set up `assets/` directory with initial 5 templates
- [ ] Implement `TemplateSelector` with hardcoded registry
- [ ] Add Impact font to `assets/fonts/`

### Phase 2: Text Rendering (Week 1-2)
- [ ] Implement `ImageRenderer` core functionality
- [ ] Test text rendering with Impact font + stroke
- [ ] Implement footer rendering with source citation
- [ ] Create TruthShield watermark PNG
- [ ] Test watermark overlay (transparency + positioning)

### Phase 3: LLM Concept Generation (Week 2)
- [ ] Design "Cognitive Security Architect" prompt
- [ ] Implement `MemeConceptGenerator` with OpenAI
- [ ] Add JSON validation for LLM output
- [ ] Test with 10 sample claims (hate speech, health misinfo, etc.)
- [ ] Tune prompt for tone appropriateness

### Phase 4: API Integration (Week 2-3)
- [ ] Create `src/api/meme.py` with `/generate` endpoint
- [ ] Integrate with ClaimRouter for claim analysis
- [ ] Integrate with SourceRanker for source citations
- [ ] Add meme storage in `demo_data/memes/`
- [ ] Implement `/image/{meme_id}` serving endpoint

### Phase 5: Template Expansion (Week 3)
- [ ] Acquire 15 popular meme templates (Drake, Distracted BF, etc.)
- [ ] Create metadata for each template (text regions)
- [ ] Test rendering on all templates
- [ ] Add `/templates` endpoint for discovery

### Phase 6: Quality Safeguards (Week 3-4)
- [ ] Implement ad hominem detection filter
- [ ] Add sensitive topic detector (RiskLevel integration)
- [ ] Test with edge cases (political figures, violence)
- [ ] Add human review flag for CRITICAL risk claims

### Phase 7: Learning Integration (Week 4)
- [ ] Add meme engagement tracking (shares, likes)
- [ ] Log meme generation to `demo_data/ml/meme_logs.jsonl`
- [ ] Integrate with GuardianBandit for tone optimization
- [ ] Create scoreboard for meme quality metrics

### Phase 8: Production Hardening (Week 4-5)
- [ ] Add rate limiting for `/generate` endpoint
- [ ] Implement CDN upload for images (optional)
- [ ] Add error handling for missing templates
- [ ] Create batch meme generation CLI tool
- [ ] Write integration tests

---

## 6. TECHNICAL REQUIREMENTS

### 6.1 Dependencies

**New:**
```toml
[tool.poetry.dependencies]
Pillow = "^10.0.0"          # Image manipulation
```

**Existing (Reuse):**
- OpenAI client (already in `ai_engine.py`)
- FastAPI (already in `api/`)
- Pydantic (already used)

### 6.2 Asset Requirements

**Fonts:**
- `impact.ttf` - Classic meme font (free download)
- `arial.ttf` - Footer font (system font)

**Meme Templates (Recommended):**
1. Drake Hotline Bling
2. Distracted Boyfriend
3. Panik / Kalm
4. SpongeBob Mocking
5. Lisa Simpson Presentation
6. Expanding Brain
7. Two Buttons
8. Change My Mind
9. Is This a Pigeon?
10. Galaxy Brain
11. Woman Yelling at Cat
12. Bernie Sanders Mittens
13. They're the Same Picture
14. Vince McMahon Reaction
15. Trade Offer

**Watermark:**
- Transparent PNG with "TruthShield.eu" text
- Dimensions: 200x50px
- Opacity: 30-40%

### 6.3 Storage

**Directory Structure:**
```
demo_data/
├── memes/                    # Rendered memes
│   ├── {uuid}.png
│   └── ...
└── ml/
    └── meme_logs.jsonl       # Generation logs
```

**Estimated Storage:**
- Each meme: ~200-500 KB
- 1000 memes: ~500 MB
- Consider CDN for production

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests

**Test Cases:**
```python
# tests/ml/meme/test_concept_generator.py
async def test_generate_concept_health_claim():
    """Test EMPATHIC tone for health misinformation."""

async def test_generate_concept_conspiracy():
    """Test WITTY tone for conspiracy theories."""

async def test_no_ad_hominem():
    """Ensure no personal attacks in output."""
```

```python
# tests/ml/meme/test_image_renderer.py
def test_render_impact_text():
    """Test Impact font rendering with stroke."""

def test_watermark_overlay():
    """Test watermark transparency and positioning."""

def test_aspect_ratio_1x1():
    """Test square output for Instagram."""
```

### 7.2 Integration Tests

```python
# tests/integration/test_meme_api.py
async def test_full_meme_generation():
    """Test complete pipeline from claim to PNG."""

async def test_template_not_found():
    """Test error handling for invalid template."""
```

### 7.3 Quality Tests (Manual)

**Checklist:**
- [ ] Text is 100% readable (no LLM typos)
- [ ] Sources are accurate and formatted
- [ ] Watermark is visible but not intrusive
- [ ] No ad hominem content
- [ ] Tone matches claim severity

---

## 8. EXAMPLE WORKFLOW

### 8.1 Input
```json
{
  "narrative": "Die EU plant, Fleisch zu verbieten!",
  "fact_basis": "Kein EU-Verbot. Farm-to-Fork Strategie empfiehlt reduzierte Subventionen für Fleisch, aber kein Verbot für Verbraucher.",
  "sources": [
    "https://ec.europa.eu/food/horizontal-topics/farm-fork-strategy_en",
    "https://www.dw.com/de/faktencheck-eu-fleischverbot/a-57892341"
  ],
  "language": "de"
}
```

### 8.2 Processing

**Claim Analysis (ClaimRouter):**
```python
ClaimAnalysis(
    claim_types=[ClaimType.POLICY_MOBILIZATION],
    risk_level=RiskLevel.MEDIUM,
    keywords=["EU", "Fleisch", "Verbot"]
)
```

**Bandit Decision:**
```python
ToneVariant.WITTY  # Conspiracy-adjacent → WITTY tone
```

**LLM Output (MemeSpec):**
```json
{
  "visual_template": "panik_kalm",
  "top_text": "Telegram: 'EU verbietet Fleisch!'",
  "bottom_text": "Realität: Nur Subventions-Anpassung",
  "footer": "Quellen: EU Kommission | DW Faktencheck",
  "tone": "WITTY"
}
```

### 8.3 Output

**Image:** `demo_data/memes/{uuid}.png`

**Visual Layout:**
```
┌────────────────────────────────────┐
│                                    │
│  😱 [Panik Character]              │
│  "Telegram: 'EU verbietet Fleisch!'│
│                                    │
├────────────────────────────────────┤
│                                    │
│  😌 [Kalm Character]               │
│  "Realität: Nur Subventions-       │
│   Anpassung"                       │
│                                    │
├────────────────────────────────────┤
│ Quellen: EU Kommission | DW        │
│                         TruthShield│
└────────────────────────────────────┘
```

---

## 9. RISK ANALYSIS & MITIGATIONS

### 9.1 Risk: Ad Hominem Violations

**Mitigation:**
- LLM system prompt explicitly forbids personal attacks
- Post-generation filter checks for politician/party names
- Human review flag for CRITICAL risk claims

### 9.2 Risk: Tone-Deaf Humor

**Mitigation:**
- RiskLevel integration: HIGH/CRITICAL → FACTUAL tone only
- ClaimType filters: HATE_DEHUMANIZATION → no humor
- Manual review queue for edge cases

### 9.3 Risk: Source Misrepresentation

**Mitigation:**
- SourceRanker provides pre-validated sources
- Footer programmatically rendered (no LLM hallucination)
- Watermark ensures attribution to TruthShield

### 9.4 Risk: Copyright Infringement (Meme Templates)

**Mitigation:**
- Use public domain/CC0 templates where possible
- Rely on transformative fair use doctrine (memes typically protected)
- Create custom TruthShield-branded templates as fallback

### 9.5 Risk: LLM Hallucination in Facts

**Mitigation:**
- `fact_basis` is human-provided, not LLM-generated
- Sources are pre-ranked by SourceRanker
- Bottom text limited to 10-12 words (less room for hallucination)

---

## 10. SUCCESS METRICS

### 10.1 Technical Metrics
- **Generation Time:** < 3 seconds per meme
- **Image Quality:** 1080x1080px, < 500 KB
- **Text Readability:** 100% accuracy (no LLM typos)
- **Template Coverage:** 15+ meme formats

### 10.2 Quality Metrics
- **Ad Hominem Rate:** 0%
- **Source Accuracy:** 100%
- **Tone Appropriateness:** > 90% (via manual review)

### 10.3 Engagement Metrics (Future)
- **Share Rate:** > 5% of viewers
- **Positive Sentiment:** > 70% in replies
- **Fact Retention:** Measure via follow-up surveys

---

## 11. FUTURE ENHANCEMENTS

### 11.1 Video Memes
- Extend to short video formats (MP4)
- Add text overlays to viral video templates
- Integrate with TikTok/Instagram Reels specs

### 11.2 Multilingual Support
- Support EN, FR, ES, PL, UA meme generation
- Language-specific meme template preferences

### 11.3 Custom Branding
- Allow partner organizations to use their watermark
- White-label meme generation for NGOs

### 11.4 AI-Driven Template Selection
- Train ML model to match claim → optimal template
- A/B test templates for engagement

### 11.5 Real-Time Monitoring Integration
- Auto-generate memes for trending disinformation
- RSS feed monitoring → meme pipeline

---

## 12. CONCLUSION

The TruthShield Meme Generator represents a **strategic innovation** in cognitive security:

1. **Viral Counter-Narratives:** Memes are the native language of social media
2. **Factual Accuracy:** Programmatic rendering eliminates LLM typos
3. **Ethical Compliance:** No ad hominem, source citations required
4. **Scalable Production:** LLM + automation enables rapid response
5. **ML-Driven Optimization:** Bandit learning ensures tone adaptation

**Recommendation:** Proceed with **Phase 1-3 implementation** (4 weeks) to build MVP with 5 templates and basic API endpoint. Validate with batch testing before production rollout.

---

**Document Version:** 1.0
**Last Updated:** 2025-12-22
**Author:** Claude Code
**Status:** READY FOR REVIEW
