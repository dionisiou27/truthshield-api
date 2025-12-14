# CHANGELOG

## 2025-12-14

### Added - Guardian ML Pipeline

#### Claim Classification (`src/ml/guardian/claim_router.py`)
- Multi-label claim typing with 10 categories:
  - `hate_or_dehumanization`, `threat_or_incitement`, `delegitimization_frame`
  - `blanket_generalization`, `opinion_with_factual_premise`, `policy_aid_oversight`
  - `health_misinformation`, `science_denial`, `conspiracy_theory`, `foreign_influence`
- Risk level assessment (LOW, MEDIUM, HIGH, CRITICAL)
- Pattern-based detection for German and English
- Entity and keyword extraction for source retrieval
- `PolicyClaimRouter` extension for geopolitical claims

#### Source Ranking (`src/ml/guardian/source_ranker.py`)
- 70-domain whitelist across 7 authority classes:
  - PRIMARY_INSTITUTION (1.00): europa.eu, un.org, who.int, bundesregierung.de
  - MULTILATERAL (0.95): worldbank.org, nato.int, osce.org
  - REPUTABLE_NGO (0.90): amnesty.org, hrw.org, rsf.org
  - PEER_REVIEWED (0.88): pubmed.ncbi.nlm.nih.gov, nature.com, thelancet.com
  - IFCN_FACTCHECK (0.85): correctiv.org, snopes.com, politifact.com
  - REPUTABLE_MEDIA (0.70): reuters.com, bbc.com, dw.com, zeit.de
  - WIKIPEDIA (0.40): wikipedia.org (with caution)
- Scoring formula: `0.45×relevance + 0.25×authority + 0.15×recency + 0.10×specificity + 0.05×prior`
- Diversity constraints: max 1 per domain, min 2 source classes
- Hard filters: min_relevance=0.55, min_final_score=0.60

#### Thompson Sampling Bandit (`src/ml/learning/bandit.py`)
- Online learning for response optimization
- Tone variant arms:
  - `boundary_strict` - "Stop. This is misinformation."
  - `boundary_firm` - "This claim is demonstrably false."
  - `boundary_educational` - "Let's clarify the facts here."
- Source mix strategy arms:
  - `institution_heavy` - Prioritize PRIMARY_INSTITUTION
  - `balanced` - Even mix across source classes
  - `factcheck_heavy` - Prioritize IFCN_FACTCHECK
- Beta distribution with Thompson Sampling for arm selection
- Context-aware adjustments (risk level, topic, claim type)

#### Reward Function with Anti-Gaming (`src/ml/learning/feedback.py`)
- Engagement metrics collection (likes, replies, shares, views)
- Derived metrics calculation:
  - `top_comment_proxy` - Position in comments (1=best)
  - `reply_quality` - Constructive reply ratio + sentiment
  - `like_reply_ratio` - Engagement balance
  - `shares_proxy` - Share velocity (normalized)
- Anti-gaming penalties:
  - `reports_rate` (-0.30 weight) - Penalizes reported content
  - `toxicity_in_replies` (-0.15 weight) - Penalizes toxic reactions
- Reward formula: `0.35×top_comment + 0.20×reply_quality + 0.15×like_ratio + 0.10×shares - 0.30×reports - 0.15×toxicity`

#### ML API Endpoints (`src/api/ml.py`)
- `POST /api/v1/ml/analyze-claim` - Claim typing and risk assessment
- `POST /api/v1/ml/rank-sources` - Source ranking with authority scoring
- `POST /api/v1/ml/prepare-guardian` - Full ML pipeline for response preparation
- `POST /api/v1/ml/feedback` - Submit engagement metrics for bandit learning
- `GET /api/v1/ml/bandit/stats` - Thompson Sampling arm statistics
- `GET /api/v1/ml/learning/summary` - ML pipeline summary statistics
- `GET /api/v1/ml/source-whitelist` - Domain whitelist by source class
- `GET /api/v1/ml/training-data` - Export training data for offline analysis

#### ML Logging (`src/ml/learning/logging.py`)
- JSONL event logging for ML pipeline
- Event types: claim_analysis, source_ranking, bandit_decision, bandit_update, response_generated
- Learning summary statistics

#### Response Generator (`src/ml/guardian/response_generator.py`)
- Pipeline orchestration: Claim → Typing → Sources → Bandit → Response
- Tone-specific prompt generation (DE/EN)
- Source line formatting for TikTok (max 3 sources)
- Response constraints (5 sentences, 450 chars max)

### Changed
- `src/api/main.py`: Added ML router integration
- `CLAUDE.md`: Added ML Pipeline documentation with full technical details
- `README.md`: Added ML Pipeline section with source hierarchy table

### Technical Details
- All ML components use Pydantic v2 for validation
- Singleton pattern for global instances (bandit, collector, logger)
- JSONL storage in `demo_data/ml/` for training data
- Async FastAPI endpoints for ML operations

---

## 2025-12-13

### Added - Avatar Persona System

#### Guardian Avatar (`src/core/ai_engine.py`)
- Primary avatar for boundary enforcement and de-escalation
- Behavioral rules: never debate, never ask questions, never use irony
- 5-sentence structure: boundary, violation, risk, redirect, sources
- Source priority: EU Fundamental Rights, UN Hate Speech Guidance, bpb

#### TikTok Platform Output Rules
- 4-5 sentences, max 450 characters
- 3 sources required, format: "Quellen: A | B | C" (DE) / "Sources: A | B | C" (EN)
- Dynamic generation (no static templates)
- Optimization targets: top_comment_probability, reply_quality, like_reply_ratio

### Changed
- `CLAUDE.md`: Added Avatar Persona System documentation
- `README.md`: Added Avatar table and Guardian specification

---

## 2025-10-31

### Added
- Watchlist + Virality prefilter (views/growth/followers/spike) with ROI scaling.
- Coordinated Behavior (Astro-Score 0–10) with A–E rule-based features.
- Routing pipeline (prefilter → astro → KPI) with evidence/provenance.
- KPI & Watchlists endpoints (harm weights, ROI multipliers).
- Triage endpoints (item/batch/action) with audit logging and clipboard text.
- QA sampling and red-team scenarios; config endpoint.
- Content amplification templates (Claim vs. Proof, Investigative Thread) with co-branding and transparency notices.
- Compliance endpoints (transparency, DPA clauses) and provenance archiving.
- Capacity estimator and staff model endpoints.
- Bench prerequisites: requirements for metrics, stats, CLI, crypto.
- Example config: `configs/exp_astro.yaml`.

### Changed
- README: Added “NEW Today” endpoints and technical features updates.

### Notes
- Next: scaffold bench CLI and reporting (run/report/verify) and produce sample run artifacts.

