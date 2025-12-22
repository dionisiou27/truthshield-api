# TruthShield Meme Generator

**Inoculation memes for cognitive security.**

Transform disinformation narratives into viral, fact-based memes that build digital resilience.

---

## Overview

The Meme Generator is a **cognitive security tool** that:

1. ✅ **Analyzes** false claims with ClaimRouter
2. ✅ **Generates** creative meme concepts via GPT-4
3. ✅ **Renders** high-quality PNG images with Pillow
4. ✅ **Cites** authoritative sources programmatically
5. ✅ **Adapts** tone based on claim risk level

**Key Principle:** Attack the METHOD (e.g., cherrypicking, whataboutism), NOT the person.

---

## Quick Start

### 1. Install Dependencies

```bash
poetry add Pillow
```

### 2. Set Up Assets

```bash
# Create directories
mkdir -p assets/templates assets/fonts

# Add meme templates (PNG files)
# Download from imgflip.com or create custom

# Add fonts
# Download Impact font to assets/fonts/impact.ttf
```

### 3. Generate Your First Meme

```python
from src.ml.meme.concept_generator import MemeConceptGenerator
from src.ml.meme.template_selector import TemplateSelector
from src.ml.meme.image_renderer import ImageRenderer
from src.ml.guardian.claim_router import ClaimRouter
from src.core.ai_engine import Source

# Analyze claim
router = ClaimRouter()
analysis = router.analyze_claim("Die EU verbietet Fleisch!")

# Generate concept
concept_gen = MemeConceptGenerator()
meme_spec = await concept_gen.generate_concept(
    claim_analysis=analysis,
    fact_basis="Kein Verbot. Nur Subventions-Anpassung.",
    sources=[
        Source(url="...", title="EU Kommission", snippet="...", credibility_score=1.0),
        Source(url="...", title="DW Faktencheck", snippet="...", credibility_score=0.9)
    ]
)

# Render image
template_sel = TemplateSelector()
template_meta = template_sel.get_template(meme_spec.visual_template)

renderer = ImageRenderer()
image_bytes = await renderer.render_meme(template_meta, meme_spec)

# Save
with open("demo_data/memes/my_meme.png", "wb") as f:
    f.write(image_bytes)
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│           MEME GENERATOR PIPELINE                │
├─────────────────────────────────────────────────┤
│                                                  │
│  Claim → Concept → Template → Render → PNG      │
│    ↓        ↓         ↓         ↓        ↓      │
│  ClaimR   GPT-4   Selector   Pillow   Storage   │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Components

1. **MemeConceptGenerator** (`concept_generator.py`)
   - LLM-driven concept creation
   - Selects template, tone, text
   - Ensures no ad hominem attacks

2. **TemplateSelector** (`template_selector.py`)
   - Maps template names to image files
   - Provides rendering metadata (text regions)
   - Validates template availability

3. **ImageRenderer** (`image_renderer.py`)
   - Loads base template image
   - Renders text with Impact font
   - Adds watermark and footer
   - Exports optimized PNG

---

## Meme Format (TruthShield Standard)

### Anatomy of a TruthShield Meme

```
┌────────────────────────────────┐
│  TOP TEXT (Hook)               │  ← Emotional/narrative reference
│  [Meme Template Image]         │
├────────────────────────────────┤
│  BOTTOM TEXT (Payload)         │  ← Hard fact (max 60 chars)
├────────────────────────────────┤
│  Quellen: A | B | C            │  ← Source citations
│                   TruthShield  │  ← Watermark
└────────────────────────────────┘
```

### Design Rules

- **Top Text:** Max 40 characters, Impact font, white + black stroke
- **Bottom Text:** Max 60 characters, Impact font, factual punch
- **Footer:** Sans-serif, dark background, 3 sources required
- **Watermark:** "TruthShield.eu", 40% opacity, bottom-right

---

## Tone Adaptation

### Tone Selection Logic

| Claim Type | Risk Level | Tone | Example |
|------------|-----------|------|---------|
| Health Misinfo | MEDIUM | EMPATHIC | "I get why this sounds scary, but..." |
| Conspiracy | LOW | WITTY | "Nope. Here's what actually happened." |
| Hate Speech | CRITICAL | **FIRM ONLY** | "Stop. That's false." |
| Science Denial | MEDIUM | EMPATHIC | "The data shows..." |

**Safety Rule:** CRITICAL/HIGH risk → **FIRM tone only** (no humor).

---

## Available Templates

### MVP Templates (Initial 5)

1. **drake** - Drake approval/disapproval
2. **panik_kalm** - Panik/Kalm character
3. **distracted_boyfriend** - Guy looking at other girl
4. **lisa_simpson_presentation** - Lisa showing chart
5. **two_buttons** - Sweating guy choosing button

**Location:** `assets/templates/{name}.png`

**Adding Templates:**
Edit `template_selector.py` → `MEME_TEMPLATES` registry.

---

## API Integration

### Endpoint: `/api/v1/meme/generate`

**Request:**
```json
{
  "narrative": "Die EU verbietet Fleisch!",
  "fact_basis": "Kein Verbot. Nur Subventions-Anpassung.",
  "sources": ["https://ec.europa.eu/...", "https://dw.com/..."],
  "language": "de"
}
```

**Response:**
```json
{
  "meme_id": "uuid-here",
  "meme_spec": {
    "visual_template": "panik_kalm",
    "top_text": "Telegram: 'EU verbietet Fleisch!'",
    "bottom_text": "Realität: Nur Subventions-Anpassung",
    "footer": "Quellen: EU Kommission | DW",
    "tone": "WITTY"
  },
  "image_url": "/api/v1/meme/image/uuid-here",
  "generation_time_ms": 1234
}
```

**See:** `src/api/meme.py` (to be implemented)

---

## Quality Safeguards

### Prohibited Content

❌ **Ad Hominem:** No attacks on individuals or parties
❌ **Cynicism:** No mockery of victims
❌ **Tone-Deaf Humor:** No jokes on sensitive topics (violence, trauma)

### Enforcement

1. **LLM System Prompt:** Explicitly forbids personal attacks
2. **Post-Generation Filter:** Checks for politician/party names
3. **Human Review:** CRITICAL risk claims flagged for manual approval
4. **Source Validation:** Footer rendered programmatically (no hallucination)

---

## Testing

### Unit Tests

```bash
pytest tests/ml/meme/test_concept_generator.py
pytest tests/ml/meme/test_image_renderer.py
pytest tests/ml/meme/test_template_selector.py
```

### Integration Tests

```bash
pytest tests/integration/test_meme_api.py
```

### Manual Quality Checks

**Checklist:**
- [ ] Text is 100% readable (no LLM typos)
- [ ] Sources are accurate
- [ ] No ad hominem content
- [ ] Tone matches claim severity
- [ ] Watermark is visible

---

## Performance

### Metrics

- **Generation Time:** ~2-3 seconds per meme
  - LLM call: ~1-2s
  - Image rendering: ~0.5s
  - Total: < 3s

- **Image Size:** 200-500 KB (PNG, optimized)
- **Storage:** ~500 MB per 1,000 memes

### Optimization

**For Production:**
- Cache template images in Redis
- Use CDN for image serving
- Batch generation for efficiency

---

## Roadmap

### Phase 1: MVP (Week 1-2)
- [x] Core architecture design
- [ ] Implement 3 core components
- [ ] Add 5 meme templates
- [ ] Basic API endpoint

### Phase 2: Quality (Week 3)
- [ ] Ad hominem filter
- [ ] Human review queue
- [ ] Scoreboard metrics

### Phase 3: Scale (Week 4-5)
- [ ] CDN integration
- [ ] Batch generation CLI
- [ ] ML-driven template selection

### Future Enhancements
- [ ] Video memes (MP4)
- [ ] Multilingual support (EN, FR, ES, PL, UA)
- [ ] Real-time monitoring integration

---

## Resources

### Documentation
- **Full Plan:** `docs/MEME_GENERATOR_PLAN.md`
- **Quick Start:** `docs/MEME_GENERATOR_QUICKSTART.md`
- **Dependencies:** `docs/MEME_DEPENDENCIES.md`

### External Resources
- **Meme Templates:** https://imgflip.com/memetemplates
- **Impact Font:** https://fonts.google.com/
- **Pillow Docs:** https://pillow.readthedocs.io/

---

## License & Legal

### Fair Use Rationale
- **Purpose:** Educational (fact-checking)
- **Nature:** Transformative use
- **Amount:** Minimal (template only)
- **Effect:** No market harm

**Recommendation:** Document fair use for each template.

### Watermark
All memes MUST include "TruthShield.eu" watermark for attribution.

---

## Contact

**Questions?** Check `docs/MEME_GENERATOR_PLAN.md` or open an issue.

**Status:** IN DEVELOPMENT (Planning Phase Complete)

**Last Updated:** 2025-12-22
