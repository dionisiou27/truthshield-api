# Meme Generator - Dependencies & Resources

## Python Dependencies

### Required Packages

```toml
# Add to pyproject.toml [tool.poetry.dependencies]
Pillow = "^10.0.0"              # Image manipulation and rendering
```

**Installation:**
```bash
poetry add Pillow

# OR via pip
pip install Pillow
```

### Already Available (TruthShield Existing)

These packages are already in the TruthShield API and will be reused:

```toml
openai = "^1.0.0"               # LLM concept generation
fastapi = "^0.104.0"            # API endpoints
pydantic = "^2.0.0"             # Data validation
httpx = "^0.25.0"               # Async HTTP client
```

---

## Asset Requirements

### 1. Fonts

| Font | Purpose | License | Source |
|------|---------|---------|--------|
| **Impact** | Meme text (top/bottom) | Free | [Google Fonts](https://fonts.google.com/) or system fonts |
| **Arial** | Footer citations | System Font | Pre-installed on most systems |

**Download Impact Font:**
```bash
# Option 1: From Google Fonts (if available)
wget https://fonts.google.com/download?family=Anton -O anton.zip
unzip anton.zip -d assets/fonts/

# Option 2: Use system font (Linux)
cp /usr/share/fonts/truetype/msttcorefonts/Impact.ttf assets/fonts/impact.ttf

# Option 3: Use Impact alternative (Anton font)
# Anton is very similar to Impact and freely available
```

**Fallback Strategy:**
If Impact font is not available, the code will use PIL's default font (functional but less stylistic).

---

### 2. Meme Templates

**Required Templates (Minimum 5 for MVP):**

| Template Name | Description | Recommended Size | Format |
|---------------|-------------|------------------|--------|
| drake | Drake approval/disapproval | 650x500px | PNG |
| panik_kalm | Panik/Kalm character | 500x600px | PNG |
| distracted_boyfriend | Guy looking at other girl | 650x400px | PNG |
| lisa_simpson_presentation | Lisa showing chart | 640x480px | PNG |
| two_buttons | Sweating guy choosing button | 600x600px | PNG |

**Acquisition Sources:**

1. **Imgflip (Free Templates):**
   - URL: https://imgflip.com/memetemplates
   - Download blank templates
   - **License:** Most templates are public domain/fair use

2. **Know Your Meme:**
   - URL: https://knowyourmeme.com/
   - Image galleries for popular memes

3. **Manual Creation:**
   - Use GIMP/Photoshop to create custom templates
   - Ensures full copyright ownership

4. **API (Advanced):**
   - Imgflip API: https://imgflip.com/api
   - Can fetch templates programmatically

**Copyright Considerations:**
- Meme templates typically fall under **transformative fair use**
- Using templates for fact-checking/education strengthens fair use claim
- Consider creating custom TruthShield-branded templates for legal safety

---

### 3. Watermark

**TruthShield Watermark:**
- **Format:** PNG with transparency
- **Dimensions:** 200x50 pixels
- **Content:** "TruthShield.eu" text or logo
- **Opacity:** 30-40% (applied programmatically)

**Creation Options:**

1. **Canva (Free):**
   - Create text logo
   - Export as PNG with transparent background

2. **GIMP (Open Source):**
   ```bash
   # Create watermark with GIMP
   # 1. New image: 200x50px
   # 2. Add text layer: "TruthShield.eu"
   # 3. Export as PNG
   ```

3. **Online Tool:**
   - https://www.watermarkly.com/
   - https://www.adobe.com/express/create/logo

**File Location:**
```
assets/watermark.png
```

---

## Directory Structure

```bash
# Create all required directories
mkdir -p assets/templates
mkdir -p assets/fonts
mkdir -p demo_data/memes
mkdir -p src/ml/meme
mkdir -p tests/ml/meme
```

**Expected Structure:**
```
truthshield-api/
├── assets/
│   ├── templates/
│   │   ├── drake.png
│   │   ├── panik_kalm.png
│   │   ├── distracted_boyfriend.png
│   │   ├── lisa_simpson_presentation.png
│   │   └── two_buttons.png
│   ├── fonts/
│   │   ├── impact.ttf
│   │   └── arial.ttf
│   └── watermark.png
├── demo_data/
│   └── memes/                    # Generated memes output
│       └── {uuid}.png
└── src/
    └── ml/
        └── meme/
            ├── __init__.py
            ├── concept_generator.py
            ├── template_selector.py
            └── image_renderer.py
```

---

## Storage Estimates

### Disk Space Requirements

**Assets (Static):**
- Fonts: ~500 KB
- Templates (5 images): ~2 MB
- Watermark: ~50 KB
- **Total Assets:** ~3 MB

**Generated Memes (Dynamic):**
- Each meme: ~200-500 KB (PNG, optimized)
- 100 memes: ~50 MB
- 1,000 memes: ~500 MB
- 10,000 memes: ~5 GB

**Recommendations:**
- **Development:** Local storage sufficient
- **Production:** Use CDN (Cloudflare, AWS S3)
- **Cleanup Policy:** Archive memes older than 30 days

---

## API Rate Limits

### OpenAI (Concept Generation)

**Current TruthShield Usage:**
- Model: `gpt-4-turbo-preview`
- Already integrated in `ai_engine.py`

**Meme Generation Impact:**
- Each meme: 1 LLM call (~200-300 tokens)
- Cost: ~$0.002 per meme (GPT-4 Turbo pricing)
- **100 memes/day:** ~$0.20/day

**Rate Limit Considerations:**
- OpenAI Tier 1: 500 requests/minute
- Meme generation is async, no blocking

---

## Optional Enhancements

### 1. Image Optimization

**For Production:**
```bash
# Install optimization tools
pip install Pillow-SIMD  # Faster Pillow variant

# OR use external tools
apt-get install optipng  # PNG optimization
```

**Benefits:**
- 30-50% smaller file sizes
- Faster CDN delivery

### 2. Template Caching

**Redis Cache for Templates:**
```toml
redis = "^5.0.0"
```

**Use Case:**
- Cache loaded template images in memory
- Reduce disk I/O for high-volume generation

### 3. Video Meme Support (Future)

**For Video Memes:**
```toml
moviepy = "^1.0.0"      # Video editing
opencv-python = "^4.8.0" # Video processing
```

**Not needed for MVP, but enables:**
- Animated GIF memes
- Short video memes (MP4)
- TikTok/Instagram Reels format

---

## Setup Checklist

### Prerequisites

- [ ] Python 3.11+ installed
- [ ] Poetry or pip available
- [ ] OpenAI API key in `.env`

### Installation

- [ ] Install Pillow: `poetry add Pillow`
- [ ] Create directories:
  ```bash
  mkdir -p assets/{templates,fonts}
  mkdir -p demo_data/memes
  ```
- [ ] Download Impact font → `assets/fonts/impact.ttf`
- [ ] Download 5 meme templates → `assets/templates/`
- [ ] Create watermark PNG → `assets/watermark.png`

### Validation

- [ ] Test font loading:
  ```python
  from PIL import ImageFont
  font = ImageFont.truetype("assets/fonts/impact.ttf", 48)
  print("✅ Font loaded")
  ```
- [ ] Test template access:
  ```python
  from PIL import Image
  img = Image.open("assets/templates/drake.png")
  print(f"✅ Template loaded: {img.size}")
  ```

---

## Cost Analysis

### Development Phase (MVP)

**One-Time Costs:**
- Developer time: ~40-60 hours
- Asset acquisition: Free (public domain templates)
- Infrastructure: $0 (local development)

**Ongoing Costs:**
- OpenAI API: ~$0.20/day (100 memes)
- Storage: Free (< 1 GB)
- **Total:** ~$6/month

### Production Phase (1000 memes/day)

**Costs:**
- OpenAI API: ~$2/day × 30 = **$60/month**
- CDN (Cloudflare): Free tier (up to 100 GB)
- Storage (AWS S3): ~$5/month (50 GB)
- **Total:** ~$65/month

**Scaling:**
- 10,000 memes/day: ~$650/month
- Primarily driven by OpenAI costs
- Can reduce costs by caching templates

---

## Legal Compliance

### Copyright Checklist

- [ ] **Fonts:** Use open-source or system fonts (Impact is widely available)
- [ ] **Templates:** Ensure fair use or create custom templates
- [ ] **Watermark:** TruthShield.eu branding (original work)
- [ ] **Citations:** Always include authoritative sources in footer

### Fair Use Doctrine (Meme Templates)

**Transformative Use:**
✅ Educational purpose (fact-checking)
✅ Non-commercial (public service)
✅ Minimal use (template only, not original content)
✅ No market harm (promotes critical thinking)

**Recommendation:** Document fair use rationale in legal file.

---

## Support & Resources

### Pillow Documentation
- Official Docs: https://pillow.readthedocs.io/
- Text Rendering: https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html

### Font Resources
- Google Fonts: https://fonts.google.com/
- Font Squirrel: https://www.fontsquirrel.com/

### Meme Research
- Know Your Meme: https://knowyourmeme.com/
- Meme Templates: https://imgflip.com/memetemplates

---

**Last Updated:** 2025-12-22
**Status:** READY FOR IMPLEMENTATION
