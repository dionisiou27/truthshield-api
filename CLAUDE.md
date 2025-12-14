# CLAUDE.md - TruthShield API

## Project Overview
TruthShield is a FastAPI-based cognitive security platform for detecting disinformation and coordinated inauthentic behavior. It provides automated fact-checking, persona-driven counter-narratives, and compliance monitoring for digital information integrity.

## Tech Stack
- **Framework**: Python 3.11, FastAPI (async)
- **AI/ML**: OpenAI GPT-4-Turbo (reasoning, JSON mode)
- **Database**: SQLAlchemy 2.0, SQLite (dev), Alembic migrations
- **Infrastructure**: Docker, Redis (caching)
- **Testing**: pytest, black, flake8, mypy
- **External APIs**: Google Fact Check, News API, ClaimBuster, MediaWiki

## Project Structure
```
src/
├── api/           # FastAPI routes (detection, monitoring, content, compliance, ml)
├── core/          # Business logic (ai_engine, detection, threat_scoring, etc.)
├── models/        # Pydantic models
├── services/      # External integrations (Google, ClaimBuster, Wiki, News APIs)
└── ml/            # Machine Learning Pipeline
    ├── guardian/  # Claim Router, Source Ranker, Response Generator
    └── learning/  # Thompson Sampling Bandit, Feedback Collector, ML Logging
tests/             # pytest test files
configs/           # Configuration files
demo_data/         # Demo/test data + ML logs
docs/              # Documentation and HTML demo
```

## Avatar Persona System

TruthShield uses 5 specialized AI avatars for generating counter-narrative responses:

### Guardian Avatar (Primary)
- **Role**: `boundary_enforcement` - De-escalation and protection
- **Tone**: Low emotionality, high authority, neutral empathy, NO humor
- **Use Cases**: Hate speech, dehumanization, threats, targeted harassment, escalation dynamics, misinformation
- **5-Sentence Structure**:
  1. Clear stop / boundary
  2. Name harm or rule violation
  3. Explain risk (violence, normalization, harm)
  4. Redirect to acceptable discourse
  5. Sources
- **Source Priority**: EU Fundamental Rights, UN Hate Speech Guidance, bpb

### Other Avatars
- **PolicyAvatar**: EU regulatory compliance, DSA/AI Act expertise
- **MemeAvatar**: Satirical counter-narratives for viral debunking
- **EuroShieldAvatar**: EU-focused geopolitical disinformation
- **ScienceAvatar**: Scientific misinformation (health, climate, tech)

## TikTok Platform Output Rules (Global)

All avatar responses follow these platform-specific rules:

```yaml
output_length:
  sentences: "4-5"
  max_chars: 450
sources:
  required: 3
  format_de: "Quellen: A | B | C"
  format_en: "Sources: A | B | C"
learning_mode: dynamic
no_static_templates: true
optimization_targets:
  - top_comment_probability
  - reply_quality
  - like_reply_ratio
  - share_proxy
```

## Common Commands

### Run Development Server
```bash
uvicorn src.api.main:app --reload --port 8000
# OR
python main.py
```

### Run with Docker
```bash
docker-compose up --build
```

### Run Tests
```bash
pytest tests/
pytest -v  # verbose
```

### Code Quality
```bash
black src/ tests/        # format code
flake8 src/ tests/       # lint
mypy src/                # type check
```

## API Endpoints

### Detection Endpoints (`/api/v1/detect/`)
- `POST /fact-check` - AI-powered fact-checking with brand response
- `POST /universal` - Guardian Avatar universal fact-checker
- `POST /quick-check` - Fast fact-check without AI response
- `POST /fact-check/image` - OCR + fact-check for images
- `POST /ocr` - Extract text from images
- `GET /health` - Detection engine health
- `GET /status` - Full detection status with capabilities
- `GET /companies` - List supported companies/avatars
- `GET /guardian/examples` - Guardian Avatar example queries

### ML Pipeline Endpoints (`/api/v1/ml/`)
- `POST /analyze-claim` - Claim typing and risk assessment
- `POST /rank-sources` - Source ranking with authority scoring
- `POST /prepare-guardian` - Full ML pipeline for response preparation
- `POST /feedback` - Submit engagement metrics for bandit learning
- `GET /bandit/stats` - Thompson Sampling arm statistics
- `GET /learning/summary` - ML pipeline summary statistics
- `GET /source-whitelist` - Domain whitelist by source class
- `GET /training-data` - Export training data for offline analysis

### Other Endpoints
- `GET /` - API info and available endpoints
- `GET /health` - Health check
- `GET /demo` - HTML demo interface
- `GET /docs` - Swagger/OpenAPI documentation
- `/api/v1/monitor/` - Monitoring endpoints
- `/api/v1/content/` - Content analysis endpoints
- `/api/v1/compliance/` - EU compliance endpoints

## Environment Variables
Required in `.env`:
```
OPENAI_API_KEY=        # OpenAI GPT-4-Turbo access (required)
GOOGLE_API_KEY=        # Google Custom Search / Fact Check
NEWS_API_KEY=          # News API integration
HUGGINGFACE_API_KEY=   # HuggingFace models (optional)
```

## Key Files
- `main.py` - Application entry point
- `src/api/main.py` - FastAPI app configuration and routes
- `src/api/detection.py` - Detection API routes
- `src/core/ai_engine.py` - AI engine with avatar personas and TikTok rules
- `src/core/detection.py` - Disinformation detection logic
- `src/services/` - External API integrations

## API Response Structure

Fact-check responses include:
- `is_synthetic` / `is_fake` - Boolean detection result
- `confidence` - 0.0-1.0 confidence score
- `fact_check` - Detailed fact-check analysis with sources
- `ai_response` - Avatar-generated counter-narrative
- `details.verified_sources` - Curated top 5 sources
- `details.all_sources_checked` - Complete source list (Raw JSON)
- `details.api_usage` - Token usage statistics

## ML Pipeline (Guardian Learning Loop)

### Overview
The ML pipeline implements online learning for Guardian Avatar response optimization using Thompson Sampling.

### Pipeline Steps
1. **Claim Intake** → Raw text input
2. **Claim Typing** → Classification: hate, threat, health misinformation, policy, etc.
3. **Source Retrieval** → External API calls (Google, News, Wiki)
4. **Source Ranking** → Authority-weighted scoring with diversity constraints
5. **Response Generation** → Tone variant selection via bandit
6. **Learning Loop** → Engagement feedback updates bandit arms

### Source Class Hierarchy
```python
PRIMARY_INSTITUTION: 1.00   # Government, EU, UN agencies
MULTILATERAL: 0.95          # WHO, UNESCO, OSCE
REPUTABLE_NGO: 0.90         # Amnesty, HRW, Reporter ohne Grenzen
PEER_REVIEWED: 0.88         # PubMed, Nature, IPCC
IFCN_FACTCHECK: 0.85        # AFP Faktenfinder, Correctiv, Snopes
REPUTABLE_MEDIA: 0.70       # Reuters, AP, DW, Zeit
WIKIPEDIA: 0.40             # Meta-Wiki (with caution)
UNKNOWN: 0.20               # Unclassified sources
```

### Source Ranking Formula
```
final_score = 0.45×relevance + 0.25×authority + 0.15×recency + 0.10×specificity + 0.05×prior
```

### Thompson Sampling Bandit

**Tone Variants:**
- `boundary_strict` - "Stop. This is misinformation."
- `boundary_firm` - "This claim is demonstrably false."
- `boundary_educational` - "Let's clarify the facts here."

**Source Mix Strategies:**
- `institution_heavy` - Prioritize PRIMARY_INSTITUTION
- `balanced` - Even mix across source classes
- `factcheck_heavy` - Prioritize IFCN_FACTCHECK

### Reward Function (Anti-Gaming)
```python
reward = 0.35 * top_comment_proxy      # Position in comments
       + 0.20 * reply_quality          # Constructive replies
       + 0.15 * like_reply_ratio       # Engagement balance
       + 0.10 * shares_proxy           # Share velocity
       - 0.30 * reports_rate           # Report penalty (anti-gaming)
       - 0.15 * toxicity_in_replies    # Toxicity penalty
```

### Key Files
- `src/ml/guardian/claim_router.py` - Claim classification (ClaimType, RiskLevel)
- `src/ml/guardian/source_ranker.py` - Source ranking (70 domain whitelist)
- `src/ml/guardian/response_generator.py` - Pipeline orchestration
- `src/ml/learning/bandit.py` - Thompson Sampling implementation
- `src/ml/learning/feedback.py` - Engagement metrics collection
- `src/ml/learning/logging.py` - ML event logging (JSONL)
- `src/api/ml.py` - ML API endpoints

## Development Notes
- CORS is configured for localhost and production domains
- Demo mode available via `ENVIRONMENT=demo`
- All API routes are async
- Pydantic v2 used for request/response validation
- OpenAI uses `response_format={"type": "json_object"}` for reliable JSON parsing
- Guardian Avatar behavioral rules: never debate, never ask questions, never use irony, always set boundaries
- ML logs stored in `demo_data/ml/` (JSONL format)
