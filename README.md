# TruthShield API | Cognitive Security Infrastructure

**Classification:** Dual-Use / Defence Ready
**Current Status:** TRL 4 (Prototype validated in lab environment)

## Mission Statement

TruthShield provides an automated kinetic layer for the information space. It bridges the gap between detection (monitoring) and intervention (counter-measures) to protect democratic discourse against hybrid threats and coordinated inauthentic behavior (CIB).

**Current Focus:** TikTok social media prototype with Guardian Avatar for real-time counter-narrative intervention.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TRUTHSHIELD SYSTEM                       │
├─────────────────────────────────────────────────────────────┤
│  DETECTION          ANALYSIS           INTERVENTION         │
│  ─────────          ────────           ────────────         │
│  • RSS Feeds        • Claim Router     • Guardian Avatar    │
│  • API Polling      • IO Detection     • Thompson Sampling  │
│  • MediaWiki        • Source Ranker    • TikTok Response    │
│  • Fact Check API   • Evidence Score   • Learning Loop      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone and setup
git clone <repository>
cd truthshield-api
cp .env.example .env  # Add your API keys

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn src.api.main:app --reload --port 8000

# Or with Docker
docker-compose up --build
```

## Environment Variables

```bash
OPENAI_API_KEY=        # Required: GPT-4-Turbo for fact-checking
GOOGLE_API_KEY=        # Google Fact Check API
NEWS_API_KEY=          # News API integration
```

---

## Guardian Avatar

The primary intervention system for counter-narrative generation.

### Behavioral Rules
- **Never** debate opinions
- **Never** ask questions
- **Never** use irony
- **Always** set clear boundaries
- **Always** cite 3 sources

### TikTok Output Format
```
4-5 sentences, max 450 characters
Sources: A | B | C
```

### Thompson Sampling Tone Selection

4 distinct tone buckets optimized via online learning:

| Tone | Style | Use Case |
|------|-------|----------|
| **EMPATHIC** | "I get why this sounds scary, but..." | Health, science claims |
| **WITTY** | "Nope. Here's what actually happened." | Conspiracies, viral content |
| **FIRM** | "That's false. The data shows..." | High-risk, hate speech |
| **SPICY** | "Wild claim. Reality check:" | Low-risk, engagement focus |

---

## ML Pipeline

### Claim Analysis Flow

```
Claim Text
    │
    ▼
┌───────────────┐
│ Claim Router  │ → Type, Risk, Volatility, Temporal Mode
└───────────────┘
    │
    ▼
┌───────────────┐
│ IO Detection  │ → Weighted scoring (threshold: 0.45)
└───────────────┘
    │
    ▼
┌───────────────┐
│ Response Mode │ → DEBUNK / IO_CONTEXT / LIVE_SITUATION / CAUTIOUS
└───────────────┘
    │
    ▼
┌───────────────┐
│ Source Ranker │ → Pure ranking, topic-fit boost
└───────────────┘
    │
    ▼
┌───────────────┐
│ Bandit Select │ → Thompson Sampling tone selection
└───────────────┘
```

### Response Modes

| Mode | Description | Trigger |
|------|-------------|---------|
| **DEBUNK** | Classic fact-check | Standard false claims |
| **IO_CONTEXT** | Acknowledge narrative campaign | IO score >= 0.45 |
| **LIVE_SITUATION** | Hedge language, fluid facts | Territorial/frontline claims |
| **CAUTIOUS** | Weak evidence, be careful | LIVE + weak evidence |

**Combined Modes:** `LIVE_SITUATION + IO_CONTEXT` for territorial claims with IO framing.

### Source Authority Hierarchy

| Class | Weight | Examples |
|-------|--------|----------|
| PRIMARY_INSTITUTION | 1.00 | EU, UN, Government agencies |
| MULTILATERAL | 0.95 | WHO, UNESCO, OSCE |
| REPUTABLE_NGO | 0.90 | Amnesty, HRW |
| PEER_REVIEWED | 0.88 | PubMed, Nature |
| IFCN_FACTCHECK | 0.85 | Correctiv, Snopes |
| REPUTABLE_MEDIA | 0.70 | Reuters, AP, DW, ERR |

### IO Detection Signals

```python
# HIGH signal (0.35-0.50)
"bloc_framing": 0.45      # "The West admits..."
"peace_pressure": 0.40    # "Negotiate before..."
"known_source": 0.40      # RT, Sputnik, TASS

# MEDIUM signal (0.15-0.30)
"victory_frame": 0.25     # Victory/defeat narratives
"frontline_collapse": 0.25

# LOW signal (0.05-0.15)
"multi_location": 0.15    # Multiple locations
"absolutist": 0.10        # "Completely destroyed"
```

---

## RSS Freshness Service

Compliance-safe source ingestion for territorial/frontline claims.

### Source Tiers

| Tier | Trust Level | Corroboration | Examples |
|------|-------------|---------------|----------|
| **A** | Authoritative | Not required | ERR, Reuters, AP, DW, EUvsDisinfo |
| **B** | Fast signals | Required for territorial claims | RBC-Ukraine |

### Corroboration Logic
- **1+ Tier A hit** = Corroborated
- **2+ total sources** = Corroborated
- **Single Tier B** = Warning: seek corroboration

---

## API Endpoints

### Detection
```
POST /api/v1/detect/fact-check       # Full fact-check with avatar response
POST /api/v1/detect/universal        # Guardian Avatar universal checker
POST /api/v1/detect/quick-check      # Fast check without AI response
GET  /api/v1/detect/health           # Detection engine health
```

### ML Pipeline
```
POST /api/v1/ml/analyze-claim        # Claim typing and risk assessment
POST /api/v1/ml/rank-sources         # Source ranking
POST /api/v1/ml/prepare-guardian     # Full ML pipeline
POST /api/v1/ml/feedback             # Engagement metrics
GET  /api/v1/ml/bandit/stats         # Bandit arm statistics
```

---

## Bench Infrastructure

Offline batch testing for Guardian responses.

### Run Batch Tests
```bash
python bench/run_batch.py --input bench/batches/euronews_v1.json --output demo_data/ml
```

### Available Batches
- `euronews_v1.json` - EU delegitimization (10 claims)
- `euronews_v2.json` - NATO/war framing (8 claims)
- `euronews_starmer_china_v1.json` - China/UK direct (8 claims)
- `euronews_starmer_china_v2.json` - China/UK grey-zone (12 claims)

### Quality Targets

| Metric | Target |
|--------|--------|
| Violation Rate | < 5% |
| Genericness | < 5% |
| Escalation Risk | < 2% |
| Boundary Detection | > 85% |

---

## Learning Safeguards

### Learnable (Stylistic)
- Tone variant selection
- Source mix strategy
- Response length

### Immutable (Never Optimized)
- Factual content
- Source authority weights
- Boundary definitions
- Guardian behavioral rules
- IO detection thresholds

### Anti-Gaming Reward Function
```python
reward = 0.35 * top_comment + 0.20 * reply_quality
       + 0.15 * like_ratio + 0.10 * shares
       - 0.30 * reports - 0.15 * toxicity
       - 0.50 * platform_flag - 0.40 * bot_engagement
```

---

## Tech Stack

- **Core:** Python 3.11, FastAPI (Async)
- **AI/ML:** OpenAI GPT-4-Turbo, Thompson Sampling Bandit
- **Sources:** Google Fact Check, MediaWiki, RSS Feeds
- **Infrastructure:** Docker, Redis (caching)

---

## Documentation

- `CLAUDE.md` - Full technical documentation
- `CHANGELOG.md` - Version history
- `STRATEGY/Technical_Docs/03_Tech_Roadmap.md` - Development roadmap

---

*2025 TruthShield Consortium. All rights reserved.*
