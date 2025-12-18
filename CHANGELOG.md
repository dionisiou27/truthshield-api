# CHANGELOG

## 2025-12-18

### Added - Temporal Awareness, IO Detection & RSS Freshness

#### Response Mode System (`src/ml/guardian/claim_router.py`)
- `ResponseModeResult` class with primary + secondary (overlay) modes
- Combined modes: `LIVE_SITUATION + IO_CONTEXT` for territorial IO claims
- `EvidenceQuality` enum (STRONG/MEDIUM/WEAK) for response confidence gating
- Proper routing matrix: Gate 1 (Temporal) → Gate 2 (Evidence) → Gate 3 (IO Overlay)

#### Weighted IO Detection (`src/ml/guardian/claim_router.py`)
- Replaced simple 2+ count with weighted scoring system
- `IO_THRESHOLD = 0.45` for IO pattern classification
- `IO_SIGNAL_WEIGHTS`:
  - HIGH (0.35-0.50): bloc_framing, peace_pressure, known_source, territorial_multi
  - MEDIUM (0.15-0.30): victory_frame, frontline_collapse, map_claims
  - LOW (0.05-0.15): multi_location, absolutist
- `apply_external_io_boost()` for RSS freshness IO signals
- `assess_evidence_quality()` heuristic before source retrieval

#### RSS Freshness Service (`src/services/rss_freshness.py`)
- NEW service for compliance-safe source ingestion via RSS feeds
- No HTML scraping - respects robots.txt restrictions
- Source tiers: A (authoritative) and B (requires corroboration)
- `RSSSourceConfig` with corroboration_required_for field
- Registered sources:
  - **Tier A**: ERR News (Estonia), Reuters, AP, DW, EUvsDisinfo
  - **Tier B**: RBC-Ukraine (fast signals, needs corroboration for frontline)
- `check_territorial_freshness()` helper with corroboration analysis
- IO boost when whitelist source explicitly names IO campaign

#### Source Ranker v2 - Pure Ranking (`src/ml/guardian/source_ranker.py`)
- Removed all hard filters (min_relevance, min_final_score)
- Pure ranking with weighted scoring - best sources float to top
- Topic-fit boost for claim-type-specific source profiles
- New scoring formula: 0.35×relevance + 0.30×authority + 0.20×topic_fit + 0.10×recency + 0.05×prior
- Added source profiles: territorial_control, policy_mobilization
- Whitelist additions: ERR, Baltic broadcasters (LRT, LSM), RBC-Ukraine

#### Thompson Sampling Bandit (`src/ml/learning/bandit.py`)
- Expanded to 4 tone buckets: EMPATHIC, WITTY, FIRM, SPICY
- Context-based soft nudges (not hard rules):
  - Health/science → EMPATHIC preference
  - Conspiracy → WITTY/SPICY preference
  - High risk → FIRM preference
  - Hate/threats → FIRM only

### Changed
- `src/core/ai_engine.py`: Updated to handle ResponseModeResult with primary+secondary modes
- `requirements.txt`: Added `feedparser>=6.0.0` for RSS parsing

### Removed
- Obsolete documentation files:
  - `API_SOURCE_ANALYSIS_REPORT.md`
  - `IMPLEMENTATION_STATUS.md`
  - `PHASE_1_IMPROVEMENTS.md`
  - `API_SETUP.md`

---

## 2025-12-14 (Update 5)

### Added - China/UK Security Batch Testing & Reward Poisoning Tests

#### China/UK Security Test Batches
- `bench/batches/euronews_starmer_china_v1.json`: 8 direct claims
  - Clusters: threat_downplay, propaganda_frame, power_deflection, uk_delegitimization, expansion_denial, submission_frame, colonial_blame_shift, influence_denial
  - Results: 8/8 PASS, 0% violation rate
- `bench/batches/euronews_starmer_china_v2.json`: 12 grey-zone claims
  - Clusters: provocation_frame, empire_legacy_hypocrisy, restitution_deflection, economic_dependence_trap, selective_threat_framing, kinetic_reduction, cold_war_projection, sovereignty_reversal, domestic_distraction, influence_normalisation, rules_order_skepticism, security_inflation
  - Test focus: grey_zone_handling, whataboutism_without_dismissal, partial_truth_acknowledgment, no_false_equivalence
  - Results: 12/12 PASS, 0% violation rate

#### Topic-Aware Mock Sources (`bench/run_batch.py`)
- `MOCK_SOURCES_CHINA_UK`: 8 authoritative sources for UK security topics
  - gov.uk (Integrated Review), mi5.gov.uk, ncsc.gov.uk, nato.int, worldbank.org, chathamhouse.org, iiss.org, amnesty.org
- `select_sources_for_bench()` detects topic from batch params

#### Reward Poisoning Test (`bench/test_reward_poisoning.py`)
- Test C: Validates NegativeSignals anti-gaming protection
- 7 poisoning scenarios:
  - high_engagement_high_reports (viral but reported)
  - content_removed (complete nullification)
  - toxic_replies (60% toxicity)
  - bot_engagement_spike (like velocity anomaly)
  - reply_escalation (provocative content)
  - platform_flagged (moderation flags)
  - clean_high_engagement (control - should NOT be penalized)
- Bandit drift test: 50 rounds provocative vs clean content
- Results: 7/7 scenarios PASS, no bandit drift detected

#### Sentence-Start Boundary Detection (`src/ml/learning/scoreboard.py`)
- `HARD_BOUNDARY_STARTS`: stop., this is false, this is misinformation, etc.
- `SOFT_BOUNDARY_STARTS`: this omits, this reverses, this conflates, this assumes, etc.
- Complements regex patterns to prevent pattern-list gaming
- Checks first sentence start position, not just regex match

#### Extended Grey-Zone Boundary Patterns
- New SOFT_BOUNDARY_PATTERNS for China/UK v2:
  - `conflates`, `substitutes`, `assumes`, `narrows`, `dismisses`
  - `raises a valid`, `does not answer`, `both can be true`, `does not cancel`
  - `inverts established`, `real and documented`, `does not negate`
  - `misrepresents how`, `absence of.*does not equal`

### Changed
- `bench/run_batch.py`: Added 20 Guardian response templates (v1_001-v1_008, v2_001-v2_012)
- `src/ml/learning/scoreboard.py`: Added sentence-start detection in score_response()
- `CLAUDE.md`: Added China/UK batch documentation

---

## 2025-12-14 (Update 4)

### Added - Risk-Aware Boundary Detection & Batch Testing

#### Risk-Aware Boundary Detection (`src/ml/learning/scoreboard.py`)
- `BoundaryType` enum: HARD, SOFT, NONE
- Risk-level-aware violation logic:
  - HIGH/CRITICAL risk: Requires **hard** boundary (stop, false, misinformation)
  - MEDIUM risk: Requires hard OR **soft** boundary
  - LOW risk: Boundary optional (no violation)
- Hard boundary patterns: stop, halt, false, wrong, misinformation, factually wrong
- Soft boundary patterns (v2): misleading, misconception, distorts, framing, inverts, omits, misrepresents, erases, reverses, removes agency
- `score_response()` now accepts `risk_level` and `claim_types` parameters

#### Batch Processing Infrastructure (`bench/run_batch.py`)
- Complete batch testing CLI for Guardian responses
- Mock source candidates for offline testing (EU/Ukraine topic)
- Pre-defined Guardian response templates (18 TikTok-ready responses)
- `select_sources_for_bench()` simplified source selection
- Batch definition format with claims, clusters, and common params

#### Test Batches
- `bench/batches/euronews_v1.json`: 10 EU delegitimization claims
  - Clusters: democratic_delegitimization, eu_war_framing, blame_shift, foreign_influence
- `bench/batches/euronews_v2.json`: 8 NATO/war framing claims
  - Clusters: blame_reversal, aggressor_victim_inversion, false_causality, proxy_war_narrative
  - Focus: causal chain breaking, false balance avoidance, no NATO debate drift

#### Results
- Batch v1: 0% violation rate, 100% boundary detection (8 soft, 2 hard)
- Batch v2: 0% violation rate, 100% boundary detection (7 soft, 1 hard)
- All responses pass quality targets: escalation_risk=0%, genericness=0%

### Changed
- `CLAUDE.md`: Added Bench Infrastructure documentation
- `README.md`: Added Bench Infrastructure section with commands and quality targets

---

## 2025-12-14 (Update 3)

### Added - Bench Infrastructure & Quality Metrics

#### LLM Scoreboard (`src/ml/learning/scoreboard.py`)
- Automatic quality scoring for Guardian responses
- Rule violation detection:
  - `asked_question` - Guardian never asks questions
  - `used_irony` - No irony/sarcasm allowed
  - `exceeded_length` - Over 450 chars
  - `insufficient_sources` - Less than 3 sources
  - `generic_response` - "Needs verification" blabla
  - `missing_boundary` - No clear boundary statement
- Genericness score (0-1): Detection of vague responses
- Escalation risk (0-1): Responses that might escalate
- Source relevance QA: SUPPORTED / REFUTED / UNRELATED labels

#### Outcome Snapshots (`src/ml/learning/feedback.py`)
- `OutcomeSnapshot` model for engagement at 1h/6h/24h
- Tracks engagement trajectory over time
- Enables proper learning signal development

#### Bandit Replay CLI (`bench/replay.py`)
- Offline bandit testing before online deployment
- Commands: `run`, `report`, `verify`
- Sanity checks for logical vs suspicious updates
- State change tracking for arm distributions

#### Scoreboard API Endpoints
- `POST /api/v1/ml/scoreboard/score` - Score a response
- `POST /api/v1/ml/scoreboard/source-qa` - Submit QA labels
- `GET /api/v1/ml/scoreboard/summary` - Aggregate metrics
- `GET /api/v1/ml/scoreboard/problems` - Problem responses

### Changed
- `EngagementMetrics` now includes `snapshot_1h`, `snapshot_6h`, `snapshot_24h`
- `src/api/ml.py`: Added scoreboard endpoints

---

## 2025-12-14 (Update 2)

### Added - Learning Safeguards & Anti-Gaming (Defence/EU Review Compliance)

#### Immutable Constraints (`src/ml/learning/bandit.py`)
- `ImmutableConstraints` class defines parameters never subject to optimization:
  - Source class authority weights
  - Guardian behavioral rules
  - Claim classification logic
  - Risk level definitions
  - Boundary definitions
- `MIN_SOURCE_AUTHORITY: 0.70` - No source below REPUTABLE_MEDIA
- `MAX_ENGAGEMENT_WEIGHT: 0.50` - Prevents engagement > accuracy drift

#### Negative Optimization Signals (`src/ml/learning/bandit.py`)
- `NegativeSignals` class with anti-gaming penalties:
  - `REPORT_RATE_WEIGHT: -0.30` - Heavy penalty for reports
  - `CONTENT_REMOVAL_PENALTY: -1.0` - Complete reward nullification
  - `PLATFORM_FLAG_PENALTY: -0.50` - Moderation flags
  - `TOXICITY_IN_REPLIES_WEIGHT: -0.15` - Toxic reactions
  - `REPLY_CHAIN_ESCALATION: -0.20` - Provocation prevention
  - `BOT_ENGAGEMENT_PENALTY: -0.40` - Inauthentic engagement
  - `SPAM_PATTERN_PENALTY: -0.30` - Repetitive patterns

#### Guardian Source Profiles (`src/ml/guardian/source_ranker.py`)
- `GUARDIAN_SOURCE_PROFILES` - Context-sensitive sources per ClaimType:
  - `hate_or_dehumanization`: fra.europa.eu, ohchr.org, bpb.de, amnesty.org
  - `health_misinformation`: who.int, cdc.gov, nih.gov, pubmed
  - `delegitimization_frame`: transparency.org, worldbank.org, ec.europa.eu
  - `foreign_influence`: eeas.europa.eu, nato.int, euvsdisinfo.eu
  - `science_denial`: ipcc.ch, nature.com, science.org

#### Source Usage Types (`src/ml/guardian/source_ranker.py`)
- `SourceUsageType` enum: `RETRIEVAL` vs `AUTHORITY`
- `RETRIEVAL_ONLY_SOURCES`: Wikipedia (discovery, context, NOT citable)
- `AUTHORITY_SOURCES`: Government, UN, Factcheck (may be cited as evidence)

### Changed
- `calculate_reward()` now uses `NegativeSignals` class weights
- Content removal triggers complete reward nullification (return 0.0)
- Extended reward calculation with bot_engagement, spam_pattern, reply_escalation
- `CLAUDE.md`: Added Learning Safeguards, Source Profiles documentation

---

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

