# CLAUDE.md - TruthShield API

## Project Overview
TruthShield is a FastAPI-based cognitive security platform for detecting disinformation and coordinated inauthentic behavior. It provides automated fact-checking, persona-driven counter-narratives, and compliance monitoring for digital information integrity.

**Current Focus:** TikTok social media prototype with Guardian Avatar for real-time counter-narrative intervention.

## Tech Stack
- **Framework**: Python 3.11, FastAPI (async), Uvicorn
- **AI/ML**: OpenAI GPT-4-Turbo (reasoning, JSON mode), Thompson Sampling Bandit (custom implementation)
- **OCR/Vision**: EasyOCR, Pillow
- **Data Processing**: NumPy
- **Database**: SQLAlchemy 2.0, SQLite (dev)
- **Infrastructure**: Docker, Redis (caching), HTTPX
- **Testing**: pytest, black, flake8, mypy
- **External APIs**: Google Fact Check, Google Custom Search, News API, ClaimBuster, MediaWiki
- **Social Media**: Tweepy (Twitter/X)
- **RSS Feeds**: feedparser for compliance-safe source ingestion
- **Web Scraping**: BeautifulSoup4 for fact-checker sites (FactCheck.org, Snopes, Correctiv)

## Project Structure
```
src/
├── api/           # FastAPI routes (detection, monitoring, content, compliance, ml, meme)
├── core/          # Business logic (ai_engine, detection, threat_scoring, prioritization, virality)
├── models/        # Pydantic models
├── services/      # External integrations
│   ├── rss_freshness.py      # RSS-based freshness checking for territorial claims
│   ├── google_factcheck.py   # Google Fact Check API
│   ├── google_custom_search.py  # Google Custom Search
│   ├── claimbuster_api.py    # ClaimBuster API
│   ├── wiki_api.py           # MediaWiki integration
│   ├── news_api.py           # News API integration
│   ├── web_scraper.py        # Web scraping for fact-checkers (FactCheck.org, Snopes, Correctiv)
│   ├── social_monitor.py     # Twitter/social media monitoring with prioritization
│   └── ocr_service.py        # EasyOCR text extraction from images
└── ml/            # Machine Learning Pipeline
    ├── guardian/  # Claim Router, Source Ranker, Response Generator
    ├── learning/  # Thompson Sampling Bandit, Feedback Collector, ML Logging
    └── meme/      # Meme Generator (PLANNING PHASE)
tests/             # pytest test files
bench/             # Batch testing infrastructure
├── batches/       # Test claim batches (euronews_v1, v2, starmer_china)
├── run_batch.py   # Batch runner CLI
└── replay.py      # Bandit replay testing
configs/           # Configuration files
demo_data/         # Demo/test data + ML logs + memes
docs/              # Documentation, HTML demo, Meme Generator plan
```

## Common Commands

### Run Development Server
```bash
uvicorn src.api.main:app --reload --port 8000
# OR
python main.py
```

### Run Tests
```bash
pytest tests/
pytest -v  # verbose
```

### Run Batch Tests
```bash
python bench/run_batch.py --input bench/batches/euronews_v1.json --output demo_data/ml
```

## Environment Variables
Required in `.env`:
```
OPENAI_API_KEY=        # OpenAI GPT-4-Turbo access (required)
GOOGLE_API_KEY=        # Google Custom Search / Fact Check
NEWS_API_KEY=          # News API integration
HUGGINGFACE_API_KEY=   # HuggingFace models (optional)
TWITTER_API_KEY=       # Twitter/X API (for social monitoring)
TWITTER_API_SECRET=    # Twitter/X API secret
```

---

## Guardian Avatar System

### Primary Avatar
- **Role**: `boundary_enforcement` - De-escalation and protection
- **Tone**: Low emotionality, high authority, neutral empathy, NO humor
- **Use Cases**: Hate speech, dehumanization, threats, misinformation, territorial claims, IO patterns
- **Behavioral Rules**: Never debate, never ask questions, never use irony, always set boundaries

### TikTok Output Rules
```yaml
output_length:
  sentences: "4-5"
  max_chars: 450
sources:
  required: 3
  format_en: "Sources: A | B | C"
learning_mode: dynamic
no_static_templates: true
```

---

## ML Pipeline (Guardian Learning Loop)

### Pipeline Steps
1. **Claim Intake** → Raw text input
2. **Claim Analysis** → Type, risk, volatility, temporal mode, IO detection
3. **Response Mode** → DEBUNK / IO_CONTEXT / LIVE_SITUATION / CAUTIOUS
4. **Source Retrieval** → External APIs + RSS freshness
5. **Source Ranking** → Pure ranking with topic-fit boost (no hard filters)
6. **Response Generation** → Tone variant selection via Thompson Sampling
7. **Learning Loop** → Engagement feedback updates bandit arms

### Thompson Sampling Bandit

**4 Tone Buckets:**
```python
EMPATHIC = "empathic"   # "I get why this sounds scary, but..."
WITTY = "witty"         # "Nope. Here's what actually happened."
FIRM = "firm"           # "That's false. The data shows..."
SPICY = "spicy"         # "Wild claim. Reality check:"
```

**Context-Based Soft Nudges:**
- Health/science claims → EMPATHIC preference
- Conspiracy claims → WITTY/SPICY preference
- High risk → FIRM preference (no jokes)
- Hate/threats → FIRM only (clear boundary)

**Source Mix Strategies:**
- `institution_heavy` - Prioritize PRIMARY_INSTITUTION
- `balanced` - Even mix across source classes
- `factcheck_heavy` - Prioritize IFCN_FACTCHECK

### Source Class Hierarchy
```python
PRIMARY_INSTITUTION: 1.00   # Government, EU, UN agencies
MULTILATERAL: 0.95          # WHO, UNESCO, OSCE
REPUTABLE_NGO: 0.90         # Amnesty, HRW, Reporter ohne Grenzen
PEER_REVIEWED: 0.88         # PubMed, Nature, IPCC
IFCN_FACTCHECK: 0.85        # AFP Faktenfinder, Correctiv, Snopes
REPUTABLE_MEDIA: 0.70       # Reuters, AP, DW, ERR, RBC-Ukraine
WIKIPEDIA: 0.40             # Meta-Wiki (with caution)
UNKNOWN: 0.20               # Unclassified sources
```

### Source Ranking Formula (v2 - Pure Ranking)
```python
final_score = (
    0.35 * relevance +      # Keyword overlap
    0.30 * authority +      # Source class weight
    0.20 * topic_fit +      # Claim-type profile match
    0.10 * recency +        # Freshness (exponential decay)
    0.05 * prior            # Retrieval rank signal
) * accessibility           # Soft paywall penalty
```

**No hard filters** - all sources compete, best ones float to top.

---

## Temporal Awareness (TikTok Time-Sensitive Claims)

### Claim Volatility
```python
STABLE = "stable"           # Facts don't change (science, history)
LOW = "low"                 # Slow-moving topics
MEDIUM = "medium"           # Default
HIGH = "high"               # Daily changes (elections, policy)
VERY_HIGH = "very_high"     # Hourly changes (active frontline)
```

### Temporal Modes
```python
LIVE_REQUIRED = "live_required"   # Must use fresh sources (< 72h)
ARCHIVE_OK = "archive_ok"         # Established fact-checks OK
AMBIGUOUS = "ambiguous"           # Unclear timeframe - be cautious
```

### Response Modes
```python
DEBUNK = "debunk"               # Classic fact-check
IO_CONTEXT = "io_context"       # Information Operation context
LIVE_SITUATION = "live_situation"  # Fluid facts, hedge everything
CAUTIOUS = "cautious"           # Weak evidence, be careful
```

**Response Mode Routing Matrix:**
1. **Gate 1: TEMPORAL** - Is this LIVE_REQUIRED?
2. **Gate 2: EVIDENCE** - Is evidence WEAK → CAUTIOUS
3. **Gate 3: IO OVERLAY** - Is this IO pattern? (secondary mode, not replacement)

**Combined Modes:** `LIVE_SITUATION + IO_CONTEXT` for territorial claims with IO framing.

---

## Information Operation (IO) Detection

### Weighted IO Scoring
```python
IO_THRESHOLD = 0.45  # Score threshold for IO classification

IO_SIGNAL_WEIGHTS = {
    # HIGH signal (0.35-0.50)
    "bloc_framing": 0.45,         # "The West admits..."
    "peace_pressure": 0.40,       # "Negotiate before..."
    "known_source": 0.40,         # RT, Sputnik, TASS
    "territorial_multi": 0.35,    # Territorial + multi-location combo
    "whitelist_names_io": 0.30,   # Whitelist source explicitly names IO
    # MEDIUM signal (0.15-0.30)
    "victory_frame": 0.25,        # Victory/defeat narratives
    "frontline_collapse": 0.25,   # "Frontline is collapsing"
    "map_claims": 0.20,           # "Look at the map"
    # LOW signal (0.05-0.15)
    "multi_location": 0.15,       # Multiple locations in claim
    "absolutist": 0.10,           # "Completely destroyed"
}
```

### IO Response Handling
- IO claims require **narrative acknowledgment**, not just fact correction
- IO_CONTEXT can be **overlay** on LIVE_SITUATION (both modes active)
- Evidence quality gates response confidence level

---

## RSS Freshness Service

### Purpose
Compliance-safe ingestion of trusted sources via RSS feeds for territorial/frontline claims.
No HTML scraping - only RSS polling + link pinning.

### Source Registry
```python
RSS_SOURCE_REGISTRY = {
    # TIER A - Authoritative
    "ERR_NEWS_EN": RSSSourceConfig(
        base_domain="news.err.ee",
        trust_tier="A",
        rss_url="https://news.err.ee/rss",
        names_io_campaigns=True,  # ERR explicitly names IO campaigns
        topics=["territorial_control", "foreign_influence"],
    ),
    "REUTERS": RSSSourceConfig(..., trust_tier="A"),
    "AP_NEWS": RSSSourceConfig(..., trust_tier="A"),
    "DW_EN": RSSSourceConfig(..., trust_tier="A"),
    "EUVSDISINFO": RSSSourceConfig(..., trust_tier="A", names_io_campaigns=True),

    # TIER B - Fast signals, require corroboration
    "RBC_UKRAINE_EN": RSSSourceConfig(
        base_domain="newsukraine.rbc.ua",
        trust_tier="B",
        names_io_campaigns=True,
        topics=["territorial_control", "policy_mobilization"],
        corroboration_required_for=["territorial_control", "frontline_update"],
    ),
}
```

### Corroboration Logic
- **Tier A sources**: Authoritative, no corroboration needed
- **Tier B sources**: Good for freshness signals, but territorial claims need second source
- **Corroborated** = 1+ Tier A hit OR 2+ total sources

### Integration
```python
from src.services.rss_freshness import check_territorial_freshness

result = await check_territorial_freshness(
    claim_keywords=["Kupiansk", "advance"],
    locations=["Kupiansk"],
    claim_type="territorial_control"
)
# Returns: has_fresh_coverage, corroboration status, IO boost, evidence boost
```

---

## Guardian Source Profiles

Topic-specific source preferences:
```python
GUARDIAN_SOURCE_PROFILES = {
    "hate_or_dehumanization": ["fra.europa.eu", "ohchr.org", "bpb.de", "amnesty.org"],
    "health_misinformation": ["who.int", "cdc.gov", "nih.gov", "pubmed.ncbi.nlm.nih.gov"],
    "delegitimization_frame": ["transparency.org", "worldbank.org", "ec.europa.eu"],
    "foreign_influence": ["euvsdisinfo.eu", "eeas.europa.eu", "news.err.ee", "nato.int"],
    "territorial_control": ["news.err.ee", "euvsdisinfo.eu", "reuters.com", "newsukraine.rbc.ua"],
    "policy_mobilization": ["newsukraine.rbc.ua", "news.err.ee", "reuters.com"],
    "science_denial": ["ipcc.ch", "nature.com", "science.org"],
}
```

---

## Learning Safeguards (Defence/EU Review Compliance)

### LEARNABLE Parameters (stylistic only)
- Tone variant (EMPATHIC/WITTY/FIRM/SPICY) - HOW the message is framed
- Source mix strategy - WHICH source class priority
- Response length within constraints

### IMMUTABLE Parameters (never optimized)
- Factual content and claims
- Source class authority weights
- Boundary definitions and rules
- Guardian behavioral constraints
- Source whitelist membership
- Risk level assessments
- Claim type classifications
- IO detection thresholds

### Reward Function (Anti-Gaming)
```python
# Positive signals
reward = 0.35 * top_comment_proxy
       + 0.20 * reply_quality
       + 0.15 * like_reply_ratio
       + 0.10 * shares_proxy

# Negative signals
       - 0.30 * reports_rate
       - 0.15 * toxicity_in_replies
       - 0.50 * platform_flag
       - 0.20 * reply_chain_escalation
       - 0.40 * bot_engagement
       - 0.30 * spam_pattern

# Content removal = complete reward nullification (-1.0)
```

---

## Bench Infrastructure

### Available Batches
```bash
bench/batches/euronews_v1.json       # EU delegitimization (10 claims)
bench/batches/euronews_v2.json       # NATO/war framing (8 claims)
bench/batches/euronews_starmer_china_v1.json  # China/UK direct (8 claims)
bench/batches/euronews_starmer_china_v2.json  # China/UK grey-zone (12 claims)
```

### Quality Targets
| Metric | Target | Description |
|--------|--------|-------------|
| `violation_rate` | < 5% | Any rule violation |
| `genericness_rate` | < 5% | Vague/hedging responses |
| `escalation_rate` | < 2% | Potentially escalatory language |
| `missing_boundary` | > 85% | Clear boundary statement present |

### Risk-Aware Boundary Detection
| Risk Level | Boundary Required |
|------------|------------------|
| HIGH/CRITICAL | **Hard** boundary (stop, false, misinformation) |
| MEDIUM | Hard OR **Soft** boundary (misleading, distorts, omits) |
| LOW | Optional |

---

## Key Files

### Core ML Pipeline
- `src/ml/guardian/claim_router.py` - Claim analysis (type, risk, volatility, IO, response mode)
- `src/ml/guardian/source_ranker.py` - Pure ranking source selection (75+ domain whitelist)
- `src/ml/guardian/response_generator.py` - Pipeline orchestration
- `src/ml/learning/bandit.py` - Thompson Sampling (4 tone buckets)
- `src/ml/learning/feedback.py` - Engagement metrics collection
- `src/ml/learning/scoreboard.py` - Quality metrics and boundary detection

### Services
- `src/services/rss_freshness.py` - RSS-based freshness checking
- `src/services/google_factcheck.py` - Google Fact Check API
- `src/services/google_custom_search.py` - Google Custom Search API
- `src/services/wiki_api.py` - MediaWiki integration
- `src/services/news_api.py` - News API integration
- `src/services/claimbuster_api.py` - ClaimBuster API
- `src/services/web_scraper.py` - Web scraping for fact-checkers (FactCheck.org, Snopes, Correctiv)
- `src/services/social_monitor.py` - Twitter/social media monitoring with prioritization engine
- `src/services/ocr_service.py` - EasyOCR text extraction from images

### API
- `src/api/ml.py` - ML pipeline endpoints
- `src/api/detection.py` - Detection endpoints
- `src/core/ai_engine.py` - AI engine with avatar personas

---

## Additional Services & Features

### OCR Service (Image Text Extraction)

**Purpose:** Extract text from images (memes, screenshots, infographics) for analysis.

**Implementation:** `src/services/ocr_service.py`

**Technology:** EasyOCR with multi-language support (EN, DE)

**Key Features:**
- Singleton reader pattern (cached for performance)
- Async execution (non-blocking)
- Support for EN/DE languages
- Returns cleaned, paragraph-formatted text

**Usage:**
```python
from src.services.ocr_service import extract_text_from_image

text = await extract_text_from_image(image_bytes, languages=["en", "de"])
```

**Use Cases:**
- Analyzing text in viral meme images
- Extracting claims from screenshots
- Processing infographics for fact-checking

---

### Social Media Monitor

**Purpose:** Monitor Twitter/X for misinformation, coordinated campaigns, and brand threats.

**Implementation:** `src/services/social_monitor.py`

**Technology:** Tweepy (Twitter API), custom prioritization engine, virality predictor

**Key Components:**
1. **Twitter Monitoring** - Real-time keyword tracking
2. **Prioritization Engine** - Risk/reach/coordination scoring
3. **Virality Predictor** - Engagement trajectory analysis
4. **Company Target Database** - Pre-configured brand protection keywords

**Prioritization Metrics:**
- Track Pool: Min views, growth rate (24h)
- Account Pool: Min followers, follower spike detection
- Coordination Score: Multi-account pattern detection

**Supported Companies:**
- Vodafone, BMW, Bayer, Deutsche Telekom, SAP, Siemens

**Usage:**
```python
from src.services.social_monitor import SocialMediaMonitor

monitor = SocialMediaMonitor()
threats = await monitor.scan_for_threats("vodafone", limit=20)
prioritized = monitor.prioritize_batch(threats)
```

**Features:**
- Real-time Twitter stream monitoring
- Company-specific threat detection
- Virality prediction for early intervention
- Coordination detection (astroturfing, bot networks)

---

### Web Scraper (Fact-Checker Integration)

**Purpose:** Scrape fact-checking websites for dynamic source retrieval when APIs are unavailable.

**Implementation:** `src/services/web_scraper.py`

**Technology:** HTTPX, BeautifulSoup4

**Supported Sites:**
1. **FactCheck.org** (EN) - credibility_score: 0.9
2. **Snopes** (EN) - credibility_score: 0.85
3. **Correctiv** (DE) - credibility_score: 0.9

**Features:**
- Async scraping with timeout protection
- Parallel multi-site scraping
- Automatic URL normalization
- Snippet extraction (max 300 chars)
- Respectful scraping (User-Agent identification)

**Usage:**
```python
from src.services.web_scraper import scrape_factcheckers

results = await scrape_factcheckers("COVID vaccines autism", limit_per_site=2)
# Returns: List[Dict] with title, url, snippet, source, credibility_score
```

**Compliance:**
- Respects TruthShield User-Agent identification
- Rate-limited requests
- No aggressive scraping

---

## Meme Generator (PLANNING PHASE)

**Status:** 🚧 **Planning Phase** - Not yet implemented

**Documentation:** `docs/MEME_GENERATOR_PLAN.md`

### Overview

**Concept:** "Inoculation Meme" (Impf-Meme) Generator - Transform factual debunks into viral, shareable memes.

**Goal:** Build digital resilience through humor + facts, exposing disinformation methods without ad hominem attacks.

### Architecture

```
┌─────────────────────────────────────────────┐
│         MEME GENERATOR PIPELINE             │
├─────────────────────────────────────────────┤
│  Claim → Concept (LLM) → Template → Render │
└─────────────────────────────────────────────┘
```

**Components (Planned):**
1. **MemeConceptGenerator** (`src/ml/meme/concept_generator.py`) - LLM-driven concept creation
2. **TemplateSelector** (`src/ml/meme/template_selector.py`) - Meme format selection
3. **ImageRenderer** (`src/ml/meme/image_renderer.py`) - Programmatic PNG generation with Pillow

### Output Format

**MemeSpec:**
```python
visual_template: str        # e.g., "Drake", "Panik/Kalm"
top_text: str               # Hook (emotional/narrative reference)
bottom_text: str            # Payload (hard fact, max 10-12 words)
footer: str                 # Source citation
tone: ToneVariant           # WITTY, EMPATHIC, FACTUAL
aspect_ratio: str           # "1:1" or "9:16"
```

### Quality Safeguards

✅ **Allowed:**
- Attack methods (cherrypicking, whataboutism)
- Attack data inconsistencies
- Use humor to expose logical fallacies

❌ **Forbidden:**
- Ad hominem attacks on individuals/parties
- Cynicism toward victims
- Tone-deaf humor on sensitive topics

### Integration Points

- **ClaimRouter** - Claim analysis for tone selection
- **SourceRanker** - Source citations for footer
- **GuardianBandit** - Tone variant optimization
- **OCR Service** - Analyze competing memes

### Planned API Endpoint

```
POST /api/v1/meme/generate
- Input: narrative, fact_basis, sources
- Output: meme_spec, image_url, claim_analysis
```

**Estimated Timeline:** 4-5 weeks for MVP (5 templates, basic API)

**See:** `docs/MEME_GENERATOR_PLAN.md` for full implementation roadmap

---

## Development Notes
- All API routes are async
- Pydantic v2 used for request/response validation
- ML logs stored in `demo_data/ml/` (JSONL format)
- Guardian Avatar behavioral rules: never debate, never ask questions, never use irony
- Source ranking is **pure ranking** (no hard filters, only weighted scores)
- RSS feeds respect robots.txt compliance (no HTML scraping for blocked sources)

# Global CLAUDE.md

## Identity & Accounts
- GitHub: dionisiou27 (SSH key: ~/.ssh/id_ed25519)
- Docker Hub: authenticated via ~/.docker/config.json
- Deployment: Dokploy (API URL in ~/.env)

## NEVER EVER DO (Security Gatekeeper)
- NEVER commit .env files
- NEVER hardcode credentials
- NEVER publish secrets to git/npm/docker
- NEVER skip .gitignore verification

## New Project Setup (Scaffolding Rules)

### Required Files
- .env (NEVER commit)
- .env.example (with placeholders)
- .gitignore (with all required entries)
- .dockerignore
- README.md
- CLAUDE.md

### Required Structure
project/
├── src/
├── tests/
├── docs/
├── .claude/commands/
└── scripts/

### Required .gitignore
.env
.env.*
node_modules/
dist/
.claude/settings.local.json
CLAUDE.local.md

### Node.js Requirements
- Error handlers in entry point
- TypeScript strict mode
- ESLint + Prettier configured

### Quality Gates
- No file > 300 lines
- All tests must pass
- No linter warnings
- CI/CD workflow required

## Framework-Specific Rules
[Your framework patterns here]

## Required MCP Servers
- context7 (live documentation)
- playwright (browser testing)

## Global Commands
- /new-project — Apply scaffolding rules
- /security-check — Verify no secrets exposed
- /pre-commit — Run all quality gates