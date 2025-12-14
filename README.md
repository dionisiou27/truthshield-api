# TruthShield API | Cognitive Security Infrastructure
**Classification:** Dual-Use / Defence Ready
**Current Status:** TRL 4 (Prototype validated in lab environment)

## Mission Statement
TruthShield provides an automated kinetic layer for the information space. It bridges the gap between detection (monitoring) and intervention (counter-measures) to protect democratic discourse against hybrid threats and coordinated inauthentic behavior (CIB).

## System Architecture
The architecture is designed for sovereignty, resilience, and compliance by design.

* **Detection Engine:** Hybrid sensor fusion utilizing commercial APIs (TikTok/X) combined with custom scrapers for "Grey Zone" monitoring. Multi-source fact-checking via Google Fact Check API, News API, ClaimBuster, and MediaWiki.
* **Intervention Layer:** Automated generation of persona-driven counter-narratives using 5 specialized AI avatars based on Inoculation Theory.
* **Compliance Core:** Native integration of EU AI Act (Art. 50) transparency protocols and DSA audit logging.

## Avatar Persona System

TruthShield deploys 5 specialized AI avatars for targeted counter-narrative generation:

| Avatar | Role | Use Cases |
|--------|------|-----------|
| **GuardianAvatar** | Boundary enforcement, de-escalation | Hate speech, threats, harassment, misinformation |
| **PolicyAvatar** | EU regulatory compliance | DSA/AI Act violations, platform policy |
| **MemeAvatar** | Satirical debunking | Viral misinformation, humor-based counter-narratives |
| **EuroShieldAvatar** | Geopolitical defense | EU-focused disinformation, foreign influence |
| **ScienceAvatar** | Scientific accuracy | Health, climate, technology misinformation |

### Guardian Avatar Specification
The primary avatar follows strict behavioral protocols:
- **Tone:** Low emotionality, high authority, no humor
- **Structure:** 5-sentence format (boundary, violation, risk, redirect, sources)
- **Rules:** Never debate opinions, never ask questions, never use irony
- **Sources:** EU Fundamental Rights, UN Hate Speech Guidance, bpb

## TikTok Platform Output Rules

All avatar responses are optimized for TikTok engagement:

```
Output: 4-5 sentences, max 450 characters
Sources: 3 required, format "Quellen: A | B | C" (DE) / "Sources: A | B | C" (EN)
Mode: Dynamic generation (no static templates)
Optimization: Top comment probability, reply quality, engagement metrics
```

## Core Capabilities (Live)
* **Rapid Response:** < 60 seconds from detection to draft generation
* **Human-in-the-Loop (HITL):** Dashboard for manual review of AI-generated interventions before posting
* **Multimodal Analysis:** Detection of text and visual patterns in disinformation
* **OCR Pipeline:** Image upload with text extraction and fact-checking
* **Multi-language:** German (de) and English (en) support

## API Endpoints

### Fact-Checking
```
POST /api/v1/detect/fact-check      # AI-powered fact-check with avatar response
POST /api/v1/detect/universal       # Guardian Avatar universal checker
POST /api/v1/detect/quick-check     # Fast check without AI response
POST /api/v1/detect/fact-check/image # OCR + fact-check pipeline
```

### Monitoring
```
GET /api/v1/detect/health           # Detection engine health
GET /api/v1/detect/status           # Full capabilities status
GET /api/v1/detect/companies        # Supported companies/avatars
GET /api/v1/detect/guardian/examples # Guardian Avatar examples
```

## Quick Start

```bash
# Clone and setup
git clone <repository>
cd truthshield-api
cp .env.example .env  # Add your API keys

# Run with Docker
docker-compose up --build

# Or run directly
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000
```

## Environment Variables
```
OPENAI_API_KEY=        # Required: GPT-4-Turbo for fact-checking
GOOGLE_API_KEY=        # Google Fact Check API
NEWS_API_KEY=          # News API integration
HUGGINGFACE_API_KEY=   # Optional: HuggingFace models
```

## ML Pipeline (Guardian Learning Loop)

The Guardian Avatar uses online learning for response optimization:

### Pipeline Flow
```
Claim → Typing → Source Retrieval → Source Ranking → Response Generation → Learning Loop
```

### Source Authority Hierarchy
| Class | Weight | Examples |
|-------|--------|----------|
| PRIMARY_INSTITUTION | 1.00 | EU, UN, Government agencies |
| MULTILATERAL | 0.95 | WHO, UNESCO, OSCE |
| REPUTABLE_NGO | 0.90 | Amnesty, HRW |
| PEER_REVIEWED | 0.88 | PubMed, Nature |
| IFCN_FACTCHECK | 0.85 | Correctiv, Snopes |
| REPUTABLE_MEDIA | 0.70 | Reuters, AP, DW |

### Thompson Sampling Bandit
Optimizes tone variant and source mix selection based on engagement feedback:
- **Tone:** Strict / Firm / Educational
- **Source Mix:** Institution-Heavy / Balanced / Factcheck-Heavy
- **Reward:** Engagement metrics with anti-gaming penalties (reports, toxicity)

### ML API Endpoints
```
POST /api/v1/ml/analyze-claim      # Claim typing
POST /api/v1/ml/rank-sources       # Source ranking
POST /api/v1/ml/prepare-guardian   # Full ML pipeline
POST /api/v1/ml/feedback           # Engagement feedback
GET  /api/v1/ml/bandit/stats       # Bandit arm statistics
```

## Tech Roadmap (In Development)
* **C2PA Signing:** Cryptographic provenance standards for asset authentication
* **Resilience Mesh:** Decentralized distribution layer for crisis resilience
* **On-Premise Deployment:** Air-gapped version for secure government environments

## Tech Stack
* **Core:** Python 3.11, FastAPI (Async)
* **AI/ML:** OpenAI GPT-4-Turbo (JSON mode), Thompson Sampling Bandit
* **External APIs:** Google Fact Check, News API, ClaimBuster, MediaWiki
* **Infrastructure:** Dockerized, Cloud-Agnostic, Redis caching

---
*2025 TruthShield Consortium. All rights reserved.*
