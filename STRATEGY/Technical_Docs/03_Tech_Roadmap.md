# TruthShield Technical Roadmap

**Last Updated:** 2025-12-18
**Status:** TRL 4 - Prototype Validated

---

## Current State

### Completed Features

#### Core ML Pipeline
- [x] Claim Router with multi-label typing (10 claim types)
- [x] Risk level assessment (LOW/MEDIUM/HIGH/CRITICAL)
- [x] Temporal awareness (volatility, temporal modes)
- [x] Weighted IO detection (threshold: 0.45)
- [x] Response mode routing (DEBUNK/IO_CONTEXT/LIVE_SITUATION/CAUTIOUS)
- [x] Combined response modes (primary + secondary overlay)
- [x] Evidence quality assessment (STRONG/MEDIUM/WEAK)

#### Source Management
- [x] Source Ranker v2 - pure ranking (no hard filters)
- [x] 75+ domain whitelist across 7 authority classes
- [x] Topic-fit boost for claim-type profiles
- [x] RSS Freshness Service for territorial claims
- [x] Source tier system (A: authoritative, B: needs corroboration)
- [x] Corroboration logic for Tier B sources

#### Thompson Sampling
- [x] 4 tone buckets (EMPATHIC/WITTY/FIRM/SPICY)
- [x] Context-based soft nudges
- [x] Source mix strategies (institution_heavy/balanced/factcheck_heavy)
- [x] Beta distribution with proper exploration/exploitation

#### Learning Safeguards
- [x] Immutable parameters (factual content, authority weights)
- [x] Anti-gaming reward function with negative signals
- [x] Content removal = complete reward nullification
- [x] Bot engagement detection
- [x] Platform flag penalties

#### Bench Infrastructure
- [x] Batch testing CLI
- [x] Quality scoreboard (violation, genericness, escalation)
- [x] Risk-aware boundary detection
- [x] Bandit replay testing
- [x] 4 test batches (EU, NATO, China/UK)

---

## Phase 1: Production Hardening

### 1.1 RSS Integration Complete
- [x] ERR (Estonian Public Broadcasting) - Tier A
- [x] RBC-Ukraine - Tier B with corroboration
- [ ] Add Ukrinform (official Ukrainian agency) - Tier A
- [ ] Add ISW (Institute for Study of War) - Tier A
- [ ] Add LiveUAMap integration

### 1.2 API Stability
- [ ] Rate limiting for external API calls
- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker for failing sources
- [ ] Health check endpoints for each service

### 1.3 Caching Layer
- [ ] Redis caching for RSS poll results
- [ ] Source ranking cache (TTL: 1 hour)
- [ ] Claim analysis cache (TTL: 15 minutes)

---

## Phase 2: TikTok Integration

### 2.1 Comment Monitoring
- [ ] TikTok Research API integration
- [ ] Real-time comment stream processing
- [ ] Claim extraction from comments
- [ ] Viral content detection (views/engagement thresholds)

### 2.2 Response Deployment
- [ ] Semi-automated response queue
- [ ] Human-in-the-loop approval workflow
- [ ] Response timing optimization
- [ ] A/B testing framework for tone variants

### 2.3 Engagement Tracking
- [ ] 1h/6h/24h outcome snapshots
- [ ] Reply quality assessment
- [ ] Toxicity detection in reply chains
- [ ] Bot engagement detection

---

## Phase 3: Learning Loop Activation

### 3.1 Feedback Collection
- [ ] Automated engagement metric scraping
- [ ] Report rate tracking
- [ ] Platform flag monitoring
- [ ] Reply chain analysis

### 3.2 Bandit Updates
- [ ] Online learning pipeline activation
- [ ] Drift detection for arm distributions
- [ ] Performance degradation alerts
- [ ] Weekly bandit state snapshots

### 3.3 Quality Assurance
- [ ] Red team weekly testing
- [ ] Boundary compliance monitoring
- [ ] Source authority audit trail
- [ ] Response genericness tracking

---

## Phase 4: Scale & Resilience

### 4.1 Multi-Platform
- [ ] X/Twitter integration
- [ ] YouTube Shorts support
- [ ] Instagram Reels monitoring

### 4.2 Multi-Language
- [ ] German (DE) full support
- [ ] Ukrainian (UK) detection
- [ ] Russian (RU) IO pattern detection
- [ ] Language-specific source profiles

### 4.3 Infrastructure
- [ ] Kubernetes deployment
- [ ] Auto-scaling based on load
- [ ] Geographic distribution (EU data sovereignty)
- [ ] Backup and recovery procedures

---

## Future Considerations

### C2PA Integration
- Cryptographic provenance for generated responses
- Chain of custody for source verification
- Asset authentication standards

### On-Premise Deployment
- Air-gapped version for government use
- Local LLM fallback (Llama/Mistral)
- Offline source database

### Advanced IO Detection
- Network graph analysis for coordinated behavior
- Cross-platform IO campaign tracking
- Temporal clustering for burst detection

---

## Technical Debt

### Known Issues
- [ ] RSS poll intervals not configurable per-source at runtime
- [ ] No persistent bandit state storage (in-memory only)
- [ ] Missing unit tests for RSS corroboration logic
- [ ] ai_engine.py needs refactoring (>1000 lines)

### Documentation Gaps
- [ ] API endpoint documentation (OpenAPI spec)
- [ ] Source ranking algorithm deep-dive
- [ ] IO signal weight calibration methodology

---

## Metrics & Success Criteria

### Quality Targets
| Metric | Current | Target |
|--------|---------|--------|
| Violation Rate | ~0% | < 5% |
| Genericness | ~0% | < 5% |
| Escalation Risk | ~0% | < 2% |
| Boundary Detection | ~100% | > 85% |

### Performance Targets
| Metric | Target |
|--------|--------|
| Claim Analysis Latency | < 500ms |
| Full Pipeline Latency | < 3s |
| RSS Poll Interval | 10-30 min |
| Response Generation | < 2s |

### Learning Targets
| Metric | Target |
|--------|--------|
| Bandit Exploration | > 10% |
| Tone Diversity | All 4 buckets used |
| Source Mix Variance | > 3 strategies |

---

*Roadmap maintained by TruthShield Engineering Team*
