# TruthShield — Strategic & Technical Whitepaper
**Cognitive Security Infrastructure for Democratic Information Spaces**
*The Connective Tissue. One Crew, Many Nations.*

| | |
|---|---|
| Classification | Dual-Use · Defence Ready · Unclassified |
| Edition | **v5.0 Unified Edition** — June 2026 (supersedes Strategic v3.1 and Technical Whitepaper Dec 2025) |
| Technology Readiness | **TRL 4** (prototype validated through expert review and computational simulation) |
| Canonical source | TruthShield Master v1.1 — this document is a projection of the master |
| Founder | Dionysios Andres · contact@truthshield.eu · www.truthshield.eu |

---

## 1 · Executive Summary

TruthShield is a research-driven cognitive security infrastructure that closes the structural gap between disinformation **detection** and **communicative impact at the point of exposure**. A small fraction of accounts produces a disproportionate share of misleading content, systematically distorting collective norm perception in digital public spaces. The core hypothesis: visible, evidence-based counter-speech functions as social proof that restores accurate norm perception and reactivates bystander engagement — **Bystander Effect Reversal (BER)**.

The system is **human-gated and machine-paced**. Machine speed where it is safe (detection, sourcing, candidate generation: median 5 seconds); human judgment where it is constitutional (every published intervention is human-approved, mean 87 seconds, declared as AI-assisted). This is the categorical opposite of the autonomous disinformation machines documented by NATO StratCom COE: the offensive side conceals its origin and fabricates positions; TruthShield declares its methods and amplifies positions the majority already holds but cannot make visible.

**It does not invent consensus. It restores it.** *They fabricate consensus. We restore it.*

Architecturally, TruthShield deploys as sovereign national **nodes** — each a full local pipeline in local language under local compliance — connected through a **mesh** at the detection and orchestration layer only. When a narrative wave is countered in one node, neighbouring nodes are pre-armed before the wave translates into their language space. *The mesh proposes; sovereignty disposes.*

The project is embedded in a pan-European consortium preparing a Horizon Europe Cluster 2 resubmission under **HORIZON-CL2-2026-01-DEMOCRACY-08** (electoral integrity / FIMI; deadline 23 September 2026), carries a pre-registered evaluation programme (OSF: osf.io/95jm2; SocArXiv preprint: osf.io/preprints/socarxiv/37bvc_v1), and was independently validated in threat-model terms by the NATO StratCom COE assessment "Beyond Spam Bots" (April 2026), published more than a year after prototype development began.

---

## 2 · Strategic Context and Threat Landscape

### 2.1 The distribution problem
Conventional responses — detection, fact-checking, media literacy — are necessary but insufficient, because they do not address the core asymmetry: false information spreads faster, reaches further, and engages more deeply than corrections. Vosoughi, Roy & Aral (2018) documented ~6× diffusion velocity for false news. Grinberg et al. (2019): 0.1 percent of users generated 80 percent of fake-news exposures. Pew (2019): the 10 percent most active users produced ~97 percent of political tweets. The Media Ecosystem Observatory (2026) found ~100 accounts responsible for ~70 percent of conspiracy content among influential Canadian accounts. Disinformation is not diffuse; it is extremely source-concentrated. The problem is not that democracies cannot verify. It is that they have not designed the capacity to distribute.

### 2.2 The Funhouse Mirror
Robertson, del Rosario & Van Bavel (2024) describe social media as a funhouse mirror that distorts collective norm perception. Three mechanisms operate as one inference process on the feed: the bystander effect (Latané & Darley 1970), pluralistic ignorance (Katz & Allport 1931), and the spiral of silence (Noelle-Neumann 1974). The moderate majority observes a feed dominated by extremes, infers that the extreme position is mainstream, perceives itself as a minority, and withdraws. Each withdrawal makes the next more likely.

### 2.3 The intervention gap — four failure modes
1. **Institutional authority without platform presence.** EUvsDisinfo, VIGINUM, the Swedish Psychological Defence Agency produce rigorous attribution — in reports and briefings, outside the platforms, days late, in formats no platform user encounters.
2. **Community intervention without scale.** #IchBinHier, the Lithuanian Elves, Cofacts intervene at the correct location but face structural volunteer burnout and cannot match coordinated volume.
3. **Commercial detection without intervention.** Narrative-intelligence vendors deliver dashboards, alerts, and reports — analysis for analysts, not responses for audiences.
4. **Government intervention without transparency.** Direct state-platform channels collapse under censorship perception. **Civil-society anchoring is a design requirement, not a preference.**

The most resourced platform-native alternative confirms the gap: in Community Notes' first six months of US rollout, only 6 percent of proposed notes were published, median delays reached 26 hours, and 74 percent of accurate notes were never displayed (Oversight Board 2026). The counter-speech exists; it produces no norm signal — epistemically present, socially inert.

### 2.4 The fragmentation problem
The NATO StratCom COE ("Beyond Spam Bots," 2026) and the Hybrid CoE survey of 23 Participating States (Kalenský & Hanhijärvi 2025) document the same structural failure one level up: European counter-disinformation capability is fragmented across national lines. Detection is well developed (70 percent of states monitor systematically); rapid debunking exists in 38 percent; intervention at the point of exposure is near zero, and no European-level standard for counter-speech intervention exists. Adversaries treat Europe as one information space; defenders treat it as 27 separate ones. The same narrative surfaces in Polish at hour one, German at hour three, Romanian at hour six — and each national response, where it occurs at all, arrives independently and late. This cannot be solved by political coordination; sovereignty over information policy is non-negotiable. The problem is missing infrastructure. Section 6 specifies the architectural answer.

---

## 3 · Theoretical Foundation — The Seven Anchors

1. **The Visibility Gap.** Verification capacity and algorithmic reach are decoupled. Defenders cluster in the high-verification/low-reach quadrant; attackers occupy low-verification/high-reach; the high/high quadrant is empty — until infrastructure exists to occupy it without becoming the thing it counters.
2. **The Funhouse Mirror.** Source concentration × algorithmic amplification = systematic misperception of collective norms (§2.2).
3. **Bystander Effect Reversal.** If absence of visible counter-speech signals that extreme positions are uncontested, presence signals the opposite. Experimental grounding: Traberg (2025), five studies, >20,000 participants — susceptibility is mediated by perceived social consensus, not reasoning deficits. **The addressee shift is the operative core: the intervention targets the observer, not the producer.**
4. **Population Intelligence (POPINT).** Tatham (2015): institutional communication fails when conceived top-down rather than built on empirical audience understanding. Social proof fails on register-mismatch alone; persona differentiation replaces the institutional single voice.
5. **Kairotic competitiveness.** Regulation and media literacy work in Chronos; disinformation works in Kairos. The kairological resolution (Tillich 1922) neither waits for structural reform nor fights all noise: it acts at the decisive discursive moments. Operative bound: 26 hours (consensus moderation) versus 5 seconds (candidate generation).
6. **Lighthouse + parasocial persistence.** Extreme source concentration makes blanket intervention unnecessary; concentrate where one intervention shifts an entire thread. Persistent, recognisable personas (Horton & Wohl 1956; Munger 2017) turn one-shot corrections into accumulating source-recognition. *A lighthouse does not light the whole ocean.*
7. **Immutable constraints.** The system optimises **how** it says something, never **what** it says. Without this separation, adaptive learning converges on the same emotionally polarising optima as the offensive systems (§5.2.4).

---

## 4 · Architecture I — The Five Inversions

The offensive architecture documented by NATO is its own blueprint for defence: the same structural logic, inverted under transparency and epistemic constraints.

| # | Offensive ("Beyond Spam Bots") | Defensive (TruthShield) |
|---|---|---|
| 1 | Fabricated consensus — five-persona engagement cluster | Restored norm perception — five-persona counter-speech cluster |
| 2 | Concealed automation, fabricated identity | Declared AI-assistance, full audit trail, human-in-the-loop |
| 3 | Unconstrained optimisation, no epistemic floor | Mutable/immutable separation, epistemic floor |
| 4 | Peak-hour seeding, 45-minute choreography | 5 s candidate generation, 87 s human review |
| 5 | Psychological vulnerability mapping | Lighthouse concentration + parasocial persistence |

**Role mapping (Inversion 1):** authority figure → **Guardian** (institutional source anchoring) · emotional amplifier → **Meme** (humour disrupts engineered escalation) · solution provider → **Science** (verified evidence as the alternative pathway) · controlled opposition → **Policy** (regulatory and legal context restored) · conversion narrative → **EuroShield** (democratic identity as reference point). Same psychological function, same communicative mechanism, opposite epistemic commitment.

---

## 5 · Architecture II — The Node (Technical Deep Dive)

One **node** = one full instance of the four-layer pipeline, deployed in one national or institutional context.

### 5.1 Detection layer

**5.1.1 Multi-channel ingest.** Hybrid access combining academic research APIs (TikTok Research API, X Academic), commercial developer interfaces, RSS feeds from trusted outlets, monitored fact-checker output, OCR extraction from viral image content, and institutional data streams (EDMO and partner feeds). Redundancy is methodological necessity: documented API gaps (e.g. TikTok Research API under-reporting during the 2024 European elections) and the Accountability Paradox (Jungherr et al. 2025) make any single channel a research risk. No single point of failure; robots.txt-compliant collection.

**5.1.2 Claim routing.** Multi-label claim typing (health, territorial, policy, science-denial, hate-adjacent, and further classes), risk scoring (LOW / MEDIUM / HIGH / CRITICAL) by harm potential, and evidence-quality grading (STRONG / MEDIUM / WEAK) by source authority and corroboration. Latency target: < 500 ms per claim analysis.

**5.1.3 Temporal assessment.** Claims are classified **STABLE** (settled science, history), **LIVE_REQUIRED** (evolving events: war, elections, breaking health situations), or **AMBIGUOUS**. This temporal layer operationalises the Kairos anchor at the technical level: it determines hedging, freshness requirements, and admissible response modes. LIVE_REQUIRED claims demand Tier-A fresh sourcing before any candidate is generated.

**5.1.4 Information-operation detection.** Probabilistic, not binary: a weighted signal model with deployment threshold 0.45.

| Signal class | Weight | Example pattern |
|---|---|---|
| bloc_framing | 0.45 | "The West admits…" |
| peace_pressure | 0.40 | "Negotiate before it is too late…" |
| known_source | 0.40 | claim lineage to known IO outlets |
| victory_frame | 0.25 | victory/defeat narratives |
| frontline_collapse | 0.25 | "the frontline is collapsing" |
| map_claims | 0.20 | "look at the map" |
| multi_location | 0.15 | multi-theatre claim bundling |
| absolutist | 0.10 | "completely destroyed" |

Scores combine per claim; the threshold gates the IO_CONTEXT response mode (§5.2.2). Signal vocabularies are locale-specific assets maintained per node.

**5.1.5 Lighthouse prioritisation.** Of everything false, what is *visible*? Ranking by Risk × Reach × Coordination, with virality prediction for early intervention. Derived directly from the concentration evidence (§2.1): if 0.1 percent of accounts produce 80 percent of exposures, blanket response is waste. The system concentrates on high-visibility nodes where a single intervention shifts the norm perception of an entire thread.

### 5.2 Intervention layer

**5.2.1 The crew.** Five adaptive persona profiles operationalise distinct communication logics (§4 role mapping), assigned by rule-based heuristics from claim category and audience register. Personas are roles, not entities: each node instantiates them locally with full local biography, language, and cultural register (§6.3). Every generated intervention carries transparency indicators disclosing the basis of assessment (temporal inconsistency, missing sources, emotional framing, false causality).

**5.2.2 Response-mode routing.** Four modes, combinable:
- **DEBUNK** — stable facts, clear evidence: direct, sourced correction.
- **IO_CONTEXT** — IO score ≥ 0.45: the response addresses the campaign pattern, not only the claim.
- **LIVE_SITUATION** — volatile claims: hedged language, timestamped, Tier-A fresh sources mandatory ("As of 14:00 UTC, no confirmation from…").
- **CAUTIOUS** — LIVE_REQUIRED + WEAK evidence: explicit uncertainty framing.
Combined modes (e.g. LIVE_SITUATION + IO_CONTEXT for territorial claims with IO framing) produce nuanced responses for complex cases.

**5.2.3 Source authority hierarchy (immutable).** A curated whitelist of 75+ domains in seven authority classes:

| Class | Weight | Examples |
|---|---|---|
| PRIMARY_INSTITUTION | 1.00 | EU institutions, UN, national agencies |
| MULTILATERAL | 0.95 | WHO, OSCE, NATO StratCom |
| REPUTABLE_NGO | 0.90 | Amnesty, HRW, RSF |
| PEER_REVIEWED | 0.88 | PubMed, Nature, IPCC |
| IFCN_FACTCHECK | 0.85 | IFCN-certified fact-checkers, EUvsDisinfo |
| REPUTABLE_MEDIA | 0.70 | Reuters, AP, DW, ERR |
| META_WIKI | 0.40 | Wikipedia/Wikidata (with caution) |

Pure ranking, no hard filters above threshold; topic-fit boosting; diversity constraints (maximum one source per domain, minimum two source classes per intervention). Below threshold: never enters the pipeline. **These weights are immutable: the learning mechanism cannot learn to prefer weaker sources, regardless of engagement.**

**5.2.4 Adaptive delivery — Thompson Sampling.** A Bayesian bandit balances exploration of untested persona-tone combinations with exploitation of proven ones, over four tone buckets — EMPATHIC, WITTY, FIRM, SPICY — with context nudges: health/science → EMPATHIC preference; conspiracy → WITTY; HIGH/CRITICAL risk → FIRM only (no humour); hate-adjacent → FIRM only, boundary register. The reward function is anti-gaming by construction:

```
reward = 0.35·top_comment_proxy + 0.20·reply_quality + 0.15·like_reply_ratio
       + 0.10·shares_proxy
       − 0.30·reports_rate − 0.15·toxicity_in_replies
       − 0.50·platform_flag − 0.40·bot_engagement
```

**Learnable:** tone variant, source-mix strategy, length within constraints, timing. **Immutable:** factual content, evidence, source weights, claim classification logic, boundary definitions, IO thresholds. Computational simulation confirms that this separation prevents convergence on adversarial optima under reward-poisoning conditions; corpus and parameters are pre-registered (osf.io/95jm2).

**5.2.5 The constitutional gate — human-in-the-loop.** Median system latency from detection to sourced candidate: 5 seconds. Human review: 87 seconds mean. **Nothing publishes without human approval; four-eyes principle for sensitive topics.** Every published intervention is declared AI-assisted and human-reviewed, with full audit trail. Output discipline (platform-native): 4–5 sentences, ≤ 450 characters, three hyperlinked citations. This is the opposite of a botnet — and the design answer to the field evidence that undeclared automation collapses on exposure.

### 5.3 Education layer — micro-inoculation
Every intervention doubles as a learning unit: beyond the correction, it discloses the manipulation technique (emotional framing, false causality, missing sourcing, temporal inconsistency). A correction cures one case; technique transparency inoculates against the next (Roozenbeek & van der Linden 2019). Delivery occurs at the point and moment of exposure — the inverse of the ad-based delivery that failed in the field (§7.3). Persona platform profiles extend first contact into cumulative resilience building.

### 5.4 Evaluation layer
Validation corpus: 1,247 high-frequency TikTok claims (health, climate, politics; Jan 2024–Mar 2025). Mixed-effects regressions with fixed effects for persona and claim type, random intercepts for rater and claim. The Lighthouse Hypothesis is tested explicitly: do interventions at high-reach nodes achieve disproportionate counter-speech visibility versus matched random claims? All procedures pre-registered (osf.io/95jm2). Quality targets: violation rate < 5 %, genericness < 5 %, escalation risk < 2 %, boundary detection > 85 %. Performance targets: claim analysis < 500 ms, full pipeline < 3 s, candidate generation < 2 s. Learning health: exploration share > 10 %, all four tone buckets in use, ≥ 3 source-mix strategies live.

---

## 6 · Architecture III — The Mesh (Cross-Border Layer)

A single pipeline instance is a node. The mesh connects nodes into a transnational defence network without political coordination overhead.

**Local sovereignty.** Each node carries the full crew in local language, locally calibrated compliance (BSI, ANSSI, CERT-RO, equivalents), and local cultural register. Cross-node communication operates **exclusively** at the detection/orchestration layer: pattern metadata — narrative structure, manipulation technique, originator typology, temporal envelope — **never content, never personal data**. Local analysts decide whether, when, and how to deploy. *The mesh proposes; sovereignty disposes.*

**Operational example.** An anti-EU narrative surfaces in Polish comment sections at 09:00. Guardian-PL detects coordinated patterns by 09:30 and deploys. The mesh signals Guardian-DE and Guardian-RO. When the narrative appears in German at 12:00, Guardian-DE counters with the Polish response visible as cross-referenced precedent; Romanian bystanders at 15:00 see both. *The wave never lands in clean ground. Coordinated defence; no coordination meeting required.*

**What the mesh is not.** Not a federation (no central directives) · not a content-sharing network (reference and timing, no republication) · not a fact-check pool (verification stays local) · not a substitute for political coordination · not a defence alliance (civilian-led, EU-compliance-first; defence-relevant exportability secondary).

**6.3 Crew localisation — one role, many faces.** Guardian is a function, not a person. Local instances are full instances with their own biographies, not regional skins; family resemblance is carried by function and the cross-node graph the bystander sees in real time. Institutional clients receive the same logic at brand level: tone calibration without altering the role architecture.

**6.4 Compounding effects.** The Bayesian learning is not local: standardised offensive patterns (emotional triggering, coordinated amplification, manufactured consensus) recur across languages and jurisdictions, so posteriors trained in one deployment context are directly informative in another. The data flywheel — community-scale intervention data improving the institutional product, attracting partners, generating further signal — combined with the mesh structure constitutes the strategic moat: detection can be replicated and dashboards copied; a compounding cross-lingual dataset of successful counter-speech cannot.

**Immune-system frame (precision against misreading).** Personas = T-cells (first response) · human community = antibodies (scale, authenticity) · Bayesian engine = adaptive memory · immutable constraints = autoimmune control. The axis of distinction is **automated versus organic — never correct versus incorrect, never us versus them**. The body removes nothing. It responds.

---

## 7 · Evidence Base and Use-Case Walkthroughs

### 7.1 Buffer-hypothesis refutation
Generalised institutional trust offers no protection against misinformation; only specific trust matters (Roozenbeek et al. 2025, NL representative study). TruthShield therefore strengthens individual veracity discernment rather than appealing to institutional authority.

### 7.2 Delivery evidence
Two pre-registered field campaigns delivering inoculation as platform advertisements to ~1M users produced null effects — only 7.5 percent of the target audience was reached (Roozenbeek et al. 2025). The failure was the delivery architecture, not the content. In-thread placement at the point of exposure is design-validated by this result.

### 7.3 Walkthrough A — health claim (DEBUNK)
Viral claim: "mRNA vaccines alter DNA." Detection: OCR + social monitor, 50k+ views. Routing: HEALTH, risk HIGH, IO score 0.15 (below threshold), temporal STABLE → mode DEBUNK. Bandit: EMPATHIC (health nudge). Sources: WHO, PubMed-class, national agency. Candidate in 5 s → **human review** → published, declared AI-assisted: a calm recipe-vs-cookbook explanation with three citations.

### 7.4 Walkthrough B — territorial claim under IO framing (LIVE_SITUATION + IO_CONTEXT)
Claim: a contested city "has fallen" (unverified, evolving). Routing: TERRITORIAL, volatility VERY_HIGH; IO signals victory_frame + known_source = 0.65 → combined mode. Freshness check against Tier-A feeds. Tone: FIRM (no humour on war claims). Candidate: timestamped, hedged, citing absence of Tier-A confirmation and noting circulation in IO-linked channels → **human review** → published. Outcome logic: de-escalation and context, not narrative combat.

### 7.5 Walkthrough C — visual counter-format (planned)
Meme-format counter-content (concept generation + templated rendering, watermark, mandatory source footer) under the identical gate: technique disclosure required, no ad-hominem, human approval before publication. Status: design phase; subject to the same immutable constraints.

---

## 8 · Governance, Ethics, and Dual Use

**Principles (node and mesh level).** Human-in-the-loop for all interventions · full transparency (declared AI-assistance, complete audit trail, C2PA content credentials where applicable) · source-first methodology (style is optimised, facts never) · EU AI Act Article 14 human-oversight compliance, DSA-conformant data access, GDPR-conformant processing (no personal user data collected; anonymous engagement metrics; EU data residency) · independent ethics board (civil society, academia, European institutions).

**Red lines (non-negotiable).** No election interference · no micro-targeting of individuals · no covert operations or astroturfing · no exploitation of psychological vulnerabilities · no undisclosed automation · no licensing to non-democratic actors. Red lines bind every node and the mesh; violation triggers immediate de-meshing.

**Conduct boundaries.** Prohibited: ad-hominem attacks, cynicism toward victims, humour on hate/violence topics, false authority claims, engagement bait. Permitted: attacking methods (cherry-picking, whataboutism), exposing data inconsistencies, humour against logical fallacies, media-literacy content.

**Dual-use position.** The deeper answer is positional, not procedural: the categorical difference between offensive information operations and TruthShield is not one of degree but of kind — the former conceals origin and fabricates positions; the latter declares methods and restores visibility to positions the majority already holds. A mesh of sovereign nodes under shared red lines is structurally incompatible with covert operation: any participant can audit any other, and any participant can withdraw. Defence-relevant exportability (including on-premise, air-gapped deployment with local-model fallback for government environments) is a secondary capability built on the identical transparency architecture.

**Acknowledged boundary conditions (honest limits).** Whether declared AI-assisted counter-speech suffers a credibility penalty that undeclared content avoids is an open empirical question testable only in the field. Whether audiences perceive the transparent/covert distinction under rapid-scrolling conditions is equally open. This document advances an architecture argument validated at TRL 4 (expert review, computational simulation), not a field-effectiveness claim.

---

## 9 · Validation, Standing, and Consortium

**Threat-model validation.** NATO StratCom COE, "Beyond Spam Bots" (9 April 2026): five-phase offensive pipeline, five-persona engagement clusters, ratchet dynamics (47 tactics, 12 persona templates captured per campaign), 85,000 users reached in seven days. TruthShield's architecture was developed independently, predating the report by more than a year — independent convergence between NATO's threat assessment and this solution architecture.

**Programme validation.** First Horizon Europe submission (DEMOCRACY-09) scored 9/15 (threshold 10); evaluators confirmed the approach as relevant and ambitious. Identified gaps — SSH integration, single-entity dominance, missing fact-checking partner — are systematically addressed in the resubmission. NATO Innovation Challenge 2026-1: rejected at finalist stage; EIC Accelerator identified as the primary commercial-track instrument in parallel to the research track.

**Academic programme (stable assets).** Pre-registered evaluation (osf.io/95jm2, 3 April 2026; 1,247 claims, two-phase design). Design-science architecture paper available as SocArXiv preprint (osf.io/preprints/socarxiv/37bvc_v1). Three papers — on algorithmic visibility ("Back Into the Cave"), the DSR architecture ("Closing the Visibility Gap"), and the design inversions ("Inverting the Machine") — are in the peer-review pipeline alongside conference submissions (IWC Scholars Colloquium, bidt, DSI Zürich). Live review states are tracked outside this document.

**Founding team.** Dionysios Andres (Founder & CEO; 25+ years counter-disinformation practice from 1990s IRC forums to AI-enabled intervention systems; enterprise IT senior project management; Impact MBA, Tomorrow University; Phylax project coordinator). Omid Townsend (Co-Founder, LOI March 2026; PhD War Studies, King's College London; former Senior Threat Advisor, Mandiant/Google; former Senior Advisor, Rapid7; US Army Intelligence Reserves).

**Advisory board.** Tea Tutberidze (PhD cand. War Studies KCL; co-founder of Kmara; post-Soviet democratisation under Russian interference) · Goran Georgiev (Senior Analyst, CSD Sofia; FIMI, media capture) · Steve Mullen (Sequoralab; impact business-model strategy, investment readiness). Theoretical framework draws on published work of Traberg (Cambridge, 2025); reference-only, no formal cooperation.

---

## 10 · Business Model

**Frame (canonical decision).** Until v2, the offering sold a tool. From v3 onward, the offering is **membership in a defensive network** whose value grows with each additional node — a network-effect architecture with a political-strategic dimension no purely commercial vendor can match. The revenue channels below operate *within* that frame.

1. **Institutional pilots (first revenue, from MVP).** Bounded deployments for public institutions and regulators whose DSA/AI-Act mandates create demand for compliant, human-overseen intervention infrastructure. The commercial wedge is *your voice, our engine*: the client publishes under its own identity, the client's team holds the HITL approval, TruthShield supplies detection, evidence, and formulation in seconds.
2. **Per-node subscription (steady-state engine).** National or institutional nodes on annual terms, carried by state budgets, EU co-financing, or national consortia; scope-dependent pricing per node and year.
3. **Dual-use licensing.** On-premise/air-gapped deployments and defence-relevant exportability for allied democratic governments, under the red-line regime (no non-democratic actors, de-meshing enforcement).
4. **API and data stream.** Verified counter-speech infrastructure for newsrooms, researchers, and civil-society platforms.

The B2C community is deliberately **not** a revenue pillar: it is the flywheel and the moat — the data engine that makes the institutional product compound (§6.4). Funding pathway: Horizon Europe (research track) · EIC Accelerator Stage 1 (commercial track) · pre-seed round targeting €600k.

---

## 11 · Roadmap 2026–2028 (TRL 4 → TRL 6)

**2026 · Validation, institutional anchoring, mesh design.**
Q3: DEMOCRACY-08 resubmission (23 Sept) · consortium finalised as node topology · pre-seed (€600k) · production hardening of the prototype (rate limiting, retry logic, circuit breakers, caching layer, Tier-A feed expansion). Q4: MVP live on TikTok with the first node (DE) · 1,000 verified, reproducible interventions · semi-automated response queue with HITL approval workflow · engagement snapshots (1h/6h/24h) · education layer 1.0 · B2C community beta.

**2027 · Multi-node scaling and learning-loop activation.**
H1: learning loop live (online bandit updates, drift detection, weekly red-team testing) · median response < 20 min end-to-end, HITL approval ≥ 95 % · **TRL 5** demonstrated in relevant environment · multilingual expansion · nodes two and three (PL, RO target) · Horizon project operational if funded · community 1,000+ active counter-speakers. H2: 2–3 institutional pilots · MRR ≥ €30k · DSA/AI-Act compliance pack verified · Trusted Flagger status · diaspora pilots (Russian-/Turkish-speaking populations in the EU) · first cross-node operational drill.

**2028 · Consolidation and mesh maturity.**
3–5 paying customers · ARR €0.3–0.6M · **TRL 6** (system prototype demonstrated in operational environment) · routine interventions automated with human oversight for edge cases · multi-platform (TikTok, X, YouTube, Instagram, messaging) · community 10,000+ · five or more active nodes across CEE, Southern Europe, BENELUX · European foundation or public-private structure for the mesh · blueprint presentation at international forums.

---

## 12 · Risks and Mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucination in corrections | Factual content is source-bound and immutable; generation selects tone/framing only; HITL gate before publication |
| Source/API downtime or platform API changes | Multi-source redundancy (APIs + RSS + compliant scraping); no single point of failure |
| Perceived manipulation despite disclosure | Declared AI-assistance, visible citations, human approval; the disclosure-penalty question is an acknowledged boundary condition under field test (§8) |
| Tone failure on sensitive topics | Risk-aware tone gating: HIGH/CRITICAL and hate-adjacent → FIRM only; hard exclusion protocol for attacks on vulnerable groups (solidarity-first, humour excluded) |
| Reward gaming / adversarial drift | Anti-gaming reward terms (platform flags −0.50, bot engagement −0.40); immutable parameter set; pre-registered simulation evidence |
| False positives on live events | CAUTIOUS and LIVE_SITUATION modes with hedged, timestamped language and Tier-A freshness requirements |
| Political-bias accusations | Non-partisan immutable source hierarchy; axis of distinction automated/organic, never opinion; independent ethics board |
| Platform ToS exposure | No automated posting without human review; community-guideline compliance; declared accounts |

---

## 13 · References

Andre, P. et al. (2024). *Globally Representative Evidence on the Actual and Perceived Support for Climate Action.* Nature Climate Change 14.
Bär, D. et al. (2024). *LLM-Generated Counter-Speech and Perceived Inauthenticity.* EMNLP 2024.
Bergmanis-Korāts, G. & Chia Tee Hiang, J. (2026). *Beyond Spam Bots: The Rise of AI-Powered Disinformation Machines.* NATO StratCom COE, Riga.
Grinberg, N. et al. (2019). *Fake News on Twitter During the 2016 U.S. Presidential Election.* Science 363.
Horton, D. & Wohl, R. R. (1956). *Mass Communication and Para-Social Interaction.* Psychiatry 19.
Jungherr, A. et al. (2025). *The Accountability Paradox.* arXiv:2505.11577.
Kalenský, J. & Hanhijärvi, H. (2025). *Countering Disinformation in the Euro-Atlantic: Strengths and Gaps.* Hybrid CoE Research Report 15, Helsinki.
Katz, D. & Allport, F. H. (1931). *Students' Attitudes.* Craftsman Press.
Latané, B. & Darley, J. M. (1970). *The Unresponsive Bystander.* Appleton-Century-Crofts.
Mangat, R. (2026). *Communicative Deterrence.* IWC Perspectives.
Media Ecosystem Observatory (2026). *Conspiratorial Claims and Institutional Distrust in Canada's Online Ecosystem.* McGill/Toronto.
Munger, K. (2017). *Tweetment Effects on the Tweeted.* Political Behavior 39.
Noelle-Neumann, E. (1974). *The Spiral of Silence.* Journal of Communication 24.
Oversight Board (2026). *Assessing Meta's Plans to Expand Community Notes.* PAO-2025-01.
Robertson, C. E., del Rosario, K. S. & Van Bavel, J. J. (2024). *Inside the Funhouse Mirror Factory.* Current Opinion in Psychology 60.
Roozenbeek, J. & van der Linden, S. (2019). *Fake News Game Confers Psychological Resistance.* Palgrave Communications 5.
Roozenbeek, J. et al. (2025). *Misinformation Interventions and Online Sharing Behaviour.* Royal Society Open Science 12.
Rushing, B., Hersch, W. & Xu, S. (2026). *Cognitive Warfare: Definition, Framework, and Case Study.* arXiv:2603.05222.
Tatham, S. (2015). *The Solution to Russian Propaganda is Not EU or NATO Propaganda but Advanced Social Science.* NDA Latvia.
Tillich, P. (1922). *Kairós.* Die Tat 14.
Traberg, C. S. (2025). *The Social Cognition of Misinformation.* Doctoral dissertation, University of Cambridge.
Vosoughi, S., Roy, D. & Aral, S. (2018). *The Spread of True and False News Online.* Science 359.

---

*TruthShield Strategic & Technical Whitepaper · v5.0 Unified Edition · June 2026 · TRL 4 · Projection of Master v1.1*
