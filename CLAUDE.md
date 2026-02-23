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
├── api/           # FastAPI routes
│   ├── main.py            # App entry, startup, CORS, debug gating
│   ├── detection.py       # Detection endpoints
│   ├── monitoring.py      # Monitoring & prioritization endpoints
│   ├── content.py         # Content generation endpoints
│   ├── compliance.py      # EU compliance endpoints
│   ├── ml.py              # ML pipeline endpoints
│   └── ml_feedback.py     # Bandit feedback endpoints
├── core/          # Business logic
│   ├── ai_engine.py           # Orchestrator (386 LOC) — delegates to:
│   ├── prompt_builder.py      # Tone, opening, temporal, response mode instructions
│   ├── source_aggregation.py  # Source search, prioritization, secondary sources
│   ├── response_builder.py    # Single response generation with OpenAI
│   ├── verdict.py             # Verdict determination + special case overrides
│   ├── config.py              # Pydantic Settings singleton (all env access)
│   ├── database.py            # Async SQLAlchemy engine, session factory
│   ├── personas.py            # Company & avatar persona definitions
│   ├── text_detection.py      # Astroturfing, contradiction detection
│   ├── detection.py           # Content detection logic
│   ├── coordinated_behavior.py # CIB detection
│   ├── threat_scoring.py      # Threat level scoring
│   ├── prioritization.py      # Content prioritization engine
│   ├── virality.py            # Virality prediction
│   ├── audit.py               # Audit logging
│   ├── evidence.py            # Evidence aggregation
│   ├── kpi.py                 # KPI tracking
│   ├── qa.py                  # Quality assurance sampling
│   ├── content_templates.py   # Response templates
│   ├── playbooks.py           # Intervention playbooks
│   ├── publish.py             # Publishing logic
│   ├── ml_learning.py         # ML learning utilities
│   └── watchlist.py           # Entity watchlists
├── models/        # Database models (SQLAlchemy 2.0 DeclarativeBase)
│   ├── monitoring.py      # MonitoredContent, MonitoringKeyword
│   └── claims.py          # ClaimAnalysisRecord, BanditDecisionRecord, AuditLogEntry
├── services/      # External integrations (15 API connectors)
│   ├── rss_freshness.py       # RSS freshness (territorial claims)
│   ├── rss_news.py            # RSS news aggregation
│   ├── google_factcheck.py    # Google Fact Check API
│   ├── google_custom_search.py # Google Custom Search
│   ├── claimbuster_api.py     # ClaimBuster API
│   ├── wiki_api.py            # MediaWiki
│   ├── news_api.py            # News API
│   ├── web_scraper.py         # Fact-checker scraping (FactCheck.org, Snopes, Correctiv)
│   ├── social_monitor.py      # Twitter/social media monitoring
│   ├── ocr_service.py         # EasyOCR text extraction
│   ├── arxiv_api.py           # arXiv academic search
│   ├── pubmed_api.py          # PubMed medical literature
│   ├── semantic_scholar_api.py # Semantic Scholar
│   ├── core_api.py            # CORE.ac.uk academic search
│   └── who_api.py             # WHO health data API
└── ml/            # Machine Learning Pipeline
    ├── guardian/   # ClaimRouter, SourceRanker, ResponseGenerator
    ├── learning/   # Thompson Sampling Bandit, Feedback, Logging, Scoreboard
    └── meme/       # Meme Generator (PLANNING)
tests/
├── conftest.py            # Shared fixtures (router, bandit, ranker)
├── test_ml_pipeline.py    # 81 unit tests (ClaimRouter, Bandit, SourceRanker, TextDetection)
├── test_database.py       # 15 database tests (schema, CRUD)
├── exploratory/           # Manual test scripts
└── integration/           # Integration tests
bench/             # Batch testing infrastructure
configs/           # Configuration files
docs/              # Documentation, HTML demo
```

## Common Commands

### Run Development Server
```bash
uvicorn src.api.main:app --reload --port 8000
```

### Run Tests
```bash
pytest tests/ -v                          # All tests
pytest tests/ -v --tb=short               # Short traceback
pytest tests/ -v --ignore=tests/integration  # Skip integration tests
pytest tests/test_ml_pipeline.py -v       # ML pipeline only
pytest tests/test_database.py -v          # Database only
```

### Run CI Tests (without heavy deps)
```bash
pip install -r requirements-ci.txt
pytest tests/ -v --tb=short --ignore=tests/integration
```

### Lint
```bash
flake8 src/ --max-line-length=120 --ignore=E501,W503
```

### Run Batch Tests
```bash
python bench/run_batch.py --input bench/batches/euronews_v1.json --output demo_data/ml
```

## Environment Variables
All variables accessed through `src/core/config.py` Settings singleton. Zero direct `os.getenv()` in codebase.

Required in `.env`:
```
OPENAI_API_KEY=        # OpenAI GPT-4-Turbo (required)
GOOGLE_API_KEY=        # Google Custom Search / Fact Check
NEWS_API_KEY=          # News API integration
TWITTER_API_KEY=       # Twitter/X API (social monitoring)
TWITTER_API_SECRET=    # Twitter/X API secret
ENVIRONMENT=development  # development | production (gates debug endpoints, CORS, SSL)
DISABLE_SSL_VERIFY=false # Only effective when ENVIRONMENT=development
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

### Core Engine (Modular)
- `src/core/ai_engine.py` - Orchestrator (386 LOC) — delegates to modules below
- `src/core/prompt_builder.py` - Tone, temporal, response mode prompt construction
- `src/core/source_aggregation.py` - Source search, API integration, prioritization
- `src/core/response_builder.py` - Single response generation with OpenAI
- `src/core/verdict.py` - Verdict determination + special case overrides
- `src/core/personas.py` - Company & avatar persona definitions
- `src/core/text_detection.py` - Astroturfing and contradiction detection
- `src/core/config.py` - Pydantic Settings singleton (all configuration)
- `src/core/database.py` - Async SQLAlchemy engine, session factory

### ML Pipeline
- `src/ml/guardian/claim_router.py` - Claim analysis (type, risk, volatility, IO, response mode)
- `src/ml/guardian/source_ranker.py` - Pure ranking source selection (75+ domain whitelist)
- `src/ml/guardian/response_generator.py` - Pipeline orchestration
- `src/ml/learning/bandit.py` - Thompson Sampling (4 tone buckets)
- `src/ml/learning/feedback.py` - Engagement metrics collection
- `src/ml/learning/scoreboard.py` - Quality metrics and boundary detection

### Database Models
- `src/models/monitoring.py` - MonitoredContent, MonitoringKeyword
- `src/models/claims.py` - ClaimAnalysisRecord, BanditDecisionRecord, AuditLogEntry (AI Act Art. 14)

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
- All API routes are async (FastAPI)
- Pydantic v2 for request/response validation
- Config via Pydantic Settings singleton — zero `os.getenv()` in `src/`
- Database auto-initialized at startup via `init_database()`
- SQLAlchemy 2.0 async with DeclarativeBase
- CI pipeline: GitHub Actions (test + lint) on push/PR to main
- 96 tests: 81 ML pipeline + 15 database
- ML logs stored in `demo_data/ml/` (JSONL format)
- Guardian Avatar behavioral rules: never debate, never ask questions, never use irony
- Source ranking is **pure ranking** (no hard filters, only weighted scores)
- RSS feeds respect robots.txt compliance (no HTML scraping for blocked sources)
- Debug endpoints gated behind `ENVIRONMENT=development`
- CORS restricted to defined origins (not wildcard)
- SSL disable requires both `DISABLE_SSL_VERIFY=true` AND `ENVIRONMENT=development`

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