#!/usr/bin/env python3
"""
Batch Processing Script for Guardian ML Pipeline

Runs a batch of claims through the Guardian pipeline and generates
guardian_responses.jsonl for offline analysis.

Usage:
    python bench/run_batch.py --input bench/batches/euronews_v1.json
    python bench/run_batch.py --input bench/batches/euronews_v1.json --mock-sources
"""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import uuid

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ml.guardian.claim_router import ClaimRouter, PolicyClaimRouter, ClaimType, RiskLevel
from src.ml.guardian.source_ranker import SourceRanker, SourceCandidate, SourceClass
from src.ml.guardian.response_generator import GuardianResponseGenerator, get_generator
from src.ml.learning.bandit import get_bandit, BanditContext
from src.ml.learning.feedback import get_collector, ResponseLog
from src.ml.learning.scoreboard import get_scoreboard


# Mock sources for offline testing (EU/Ukraine topic)
# Note: URLs must match DOMAIN_WHITELIST in source_ranker.py
# Snippets contain keywords that match claim analysis for relevance scoring
MOCK_SOURCES_CHINA_UK = [
    {
        "url": "https://gov.uk/integrated-review-refresh-2023",
        "title": "UK Integrated Review Refresh 2023",
        "snippet": "China represents a systemic challenge to the UK. Security agencies identify cyber operations, espionage, and influence activities. UK government treats China as epoch-defining challenge requiring coordinated response across government.",
        "publisher": "UK Government"
    },
    {
        "url": "https://mi5.gov.uk/threats",
        "title": "MI5 Threat Assessment",
        "snippet": "China poses significant threat to UK national security. Intelligence services document cyber intrusions, economic coercion, and espionage targeting UK institutions. MI5 public statements warn of systematic Chinese state activity.",
        "publisher": "MI5"
    },
    {
        "url": "https://ncsc.gov.uk/threats/china",
        "title": "UK National Cyber Security Centre",
        "snippet": "China-linked cyber actors target UK critical infrastructure. NCSC documents persistent cyber operations, intellectual property theft, and state-sponsored hacking. UK cyber security assessment identifies China as significant threat actor.",
        "publisher": "NCSC"
    },
    {
        "url": "https://nato.int/strategic-concept",
        "title": "NATO Strategic Concept",
        "snippet": "China's stated ambitions and coercive policies challenge Alliance interests, security and values. NATO identifies systemic challenges from China including cyber operations, hybrid tactics, and attempts to control key technologies.",
        "publisher": "NATO"
    },
    {
        "url": "https://worldbank.org/data",
        "title": "World Bank Global Economic Data",
        "snippet": "China is second largest economy by GDP. Trade data shows China leads global manufacturing, supply chains, technology exports. Economic metrics document China major actor in international trade and institutions.",
        "publisher": "World Bank"
    },
    {
        "url": "https://transparency.org/cpi",
        "title": "Transparency International Reports",
        "snippet": "UK faces money laundering vulnerabilities through property and shell companies. Economic crime reforms address gaps. Corruption Perception Index tracks global financial integrity including UK reforms.",
        "publisher": "Transparency International"
    },
    {
        "url": "https://reuters.com/world/china",
        "title": "Reuters China Coverage",
        "snippet": "China asserts South China Sea claims, enacts Hong Kong National Security Law, increases pressure on Taiwan. Documented territorial expansion and geopolitical influence activities. China trade and foreign policy analysis.",
        "publisher": "Reuters"
    },
    {
        "url": "https://chathamhouse.org/china",
        "title": "Chatham House China Analysis",
        "snippet": "International relations governed by law, alliances, and deterrence. China foreign influence includes diplomatic pressure, information campaigns, strategic investments. Analysis of China global strategy and UK response.",
        "publisher": "Chatham House"
    }
]

MOCK_SOURCES_EU_UKRAINE = [
    {
        "url": "https://europa.eu/solidarity-ukraine",
        "title": "EU Democratic Process and Ukraine Solidarity",
        "snippet": "The European Commission President is democratically elected through EU institutions. EU Member States vote in Council. The EU Parliament directly represents European citizens in democratic governance. Europe stands united supporting Ukraine against Russian aggression.",
        "publisher": "European Commission"
    },
    {
        "url": "https://consilium.europa.eu/ukraine-response",
        "title": "EU Council Democratic Decisions on Ukraine",
        "snippet": "The Council of the EU, representing democratically elected governments, decides EU policy. EU leadership is not dictator but elected representative. Europe responds to Putin Russia invasion with democratic consensus.",
        "publisher": "Council of the EU"
    },
    {
        "url": "https://europarl.europa.eu/democracy",
        "title": "European Parliament: Voice of EU Citizens",
        "snippet": "EU citizens vote directly for European Parliament members. This democratic institution approves EU Commission President. The EU is not a dictatorship - it has elected representatives who vote for European leadership.",
        "publisher": "European Parliament"
    },
    {
        "url": "https://nato.int/ukraine-support",
        "title": "NATO Response to Russian Aggression",
        "snippet": "NATO and EU support Ukraine's sovereignty against Putin's invasion. Russia, not Europe, started the war. Europe is not weak - it provides billions in military and humanitarian aid. European defense is coordinated, not paper tiger.",
        "publisher": "NATO"
    },
    {
        "url": "https://reuters.com/europe-ukraine",
        "title": "Reuters Analysis: EU Ukraine Policy",
        "snippet": "Europe democratic institutions respond to Russia war in Ukraine. EU voted sanctions against Putin. European leaders elected by citizens support Ukraine. EU is not dictator, not gagging for war - providing defensive support.",
        "publisher": "Reuters"
    },
    {
        "url": "https://dw.com/eu-democracy",
        "title": "How EU Democracy Works",
        "snippet": "EU Commission President elected by vote of Member State governments and European Parliament. EU is democratic institution where citizens vote. European people have representation. Not dictator but elected leadership.",
        "publisher": "Deutsche Welle"
    },
    {
        "url": "https://bpb.de/europa-demokratie",
        "title": "EU Demokratie erklärt",
        "snippet": "European Union democratic process explained. EU citizens vote for Parliament. Council represents elected governments. Commission President confirmed by democratic vote. Europe is democracy, not dictatorship. EU supports Ukraine sovereignty.",
        "publisher": "bpb"
    },
    {
        "url": "https://correctiv.org/ukraine-disinfo",
        "title": "Faktencheck: EU und Ukraine",
        "snippet": "CORRECTIV fact-check: EU is democratic institution. Claims EU is dictator are false misinformation. European citizens vote. Putin Russia started war in Ukraine, not EU pushing war. Europe provides defensive aid, not aggression.",
        "publisher": "CORRECTIV"
    }
]


def load_batch(batch_path: Path) -> Dict:
    """Load batch definition from JSON file."""
    with open(batch_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_source_candidates(mock: bool = True, topic: str = "eu_ukraine") -> List[SourceCandidate]:
    """Create source candidates for ranking."""
    if mock:
        from src.ml.guardian.source_ranker import SourceClass, DOMAIN_WHITELIST

        # Select mock sources based on topic
        if "china" in topic.lower() or "uk_security" in topic.lower() or "starmer" in topic.lower():
            mock_sources = MOCK_SOURCES_CHINA_UK
        else:
            mock_sources = MOCK_SOURCES_EU_UKRAINE

        candidates = []
        for i, src in enumerate(mock_sources):
            # Pre-classify source to ensure it passes filters
            url = src["url"]
            domain = url.split("//")[-1].split("/")[0].replace("www.", "")

            # Find source class from whitelist
            source_class = SourceClass.UNKNOWN
            for whitelist_domain, sc in DOMAIN_WHITELIST.items():
                if domain == whitelist_domain or domain.endswith("." + whitelist_domain):
                    source_class = sc
                    break

            candidate = SourceCandidate(
                url=url,
                title=src["title"],
                snippet=src["snippet"],
                publisher=src.get("publisher"),
                retrieval_rank=i,
                source_class=source_class,
            )
            candidates.append(candidate)

        return candidates
    # In production, would call external APIs here
    return []


def select_sources_for_bench(
    candidates: List[SourceCandidate],
    claim_keywords: List[str],
    n: int = 3
) -> List[SourceCandidate]:
    """
    Simplified source selection for bench testing.
    Bypasses strict relevance filters to test full pipeline.
    """
    from src.ml.guardian.source_ranker import SourceClass, SOURCE_CLASS_WEIGHTS

    # Score by authority only for bench
    for src in candidates:
        src.authority_score = SOURCE_CLASS_WEIGHTS.get(src.source_class, 0.2)
        # Simple keyword match
        text = f"{src.title} {src.snippet}".lower()
        hits = sum(1 for kw in claim_keywords if kw.lower() in text)
        src.relevance_score = min(1.0, hits / max(len(claim_keywords), 1) + 0.3)
        src.final_score = 0.6 * src.authority_score + 0.4 * src.relevance_score

    # Sort by final score
    sorted_sources = sorted(candidates, key=lambda s: s.final_score, reverse=True)

    # Select top N, ensuring diversity
    selected = []
    seen_domains = set()
    for src in sorted_sources:
        domain = src.url.split("//")[-1].split("/")[0]
        if domain not in seen_domains and len(selected) < n:
            selected.append(src)
            seen_domains.add(domain)

    return selected


# Pre-defined Guardian responses for testing (real TikTok-ready responses)
GUARDIAN_RESPONSES_TEMPLATES = {
    "democratic_delegitimization": {
        "euronews_001": """Blanket claims like this distort how the EU actually works. The European Commission President is nominated by elected governments and approved by the European Parliament. That is a representative process, not a personal election campaign. Criticism is valid — mislabeling democratic structures is not. Sources: European Parliament | European Commission | EUR-Lex""",
        "euronews_002": """This repeats a common misconception. EU leadership is accountable through elected national governments and the European Parliament. That system differs from direct elections but is still democratic by design. Reducing it to "unelected" oversimplifies and misleads. Sources: European Parliament | EU Treaties (TEU) | European Commission""",
        "euronews_003": """Stop. Calling elected EU leadership "dictator" is factually wrong and delegitimizes democratic institutions. The Commission President is confirmed by elected representatives. Strong disagreement is fine — disinformation framing is not. Sources: European Parliament | EU Council | bpb.de""",
    },
    "eu_war_framing": {
        "euronews_004": """That framing removes crucial context. EU security policy is based on member-state decisions and defensive commitments, not unilateral escalation. Support for Ukraine is tied to international law and collective agreements. Disagreement is legitimate — war-baiting narratives are not. Sources: EU Council | EEAS | United Nations Charter""",
        "euronews_010": """This claim inverts responsibility. Russia invaded Ukraine; the EU supports Ukraine's right to self-defense under international law. EU aid is defensive and decided democratically by member states. Framing defensive support as "wanting war" is misleading. Sources: EU Council | EEAS | UN Charter""",
    },
    "eu_incompetence_frame": {
        "euronews_005": """This oversimplifies complex geopolitics. The EU has mobilized unprecedented sanctions, humanitarian aid, and military support. Effectiveness debates are valid; dismissing all action as "nothing" ignores documented facts. Sources: EU Council | European Commission | Reuters""",
    },
    "blame_shift": {
        "euronews_006": """This inverts documented facts. Russia launched a full-scale invasion of Ukraine in violation of international law. Blaming Europe for the conflict deflects from the aggressor. Criticism of EU policy is valid — rewriting who started the war is not. Sources: UN General Assembly | ICC | OSCE""",
    },
    "foreign_influence_narrative": {
        "euronews_007": """This repeats a Kremlin narrative. Russia invaded Ukraine; NATO expanded because Eastern European states sought protection. Framing Russian aggression as "fighting NATO" distorts documented history. Sources: NATO | OSCE | Council of Europe""",
    },
    "authoritarian_strength_frame": {
        "euronews_008": """This framing promotes authoritarian logic. Wars end through negotiation, resistance, or capitulation — not because one leader "decides." Europe supports Ukraine's right to defend itself. Calling Europe "weak" for supporting international law is a value judgment, not a fact. Sources: EU Council | UN Charter | EEAS""",
        "euronews_009": """This oversimplifies European defense. EU member states have increased military spending and coordination significantly. "Paper tiger" is rhetoric, not analysis. Criticism of EU defense is valid — dismissing all capacity is factually wrong. Sources: EEAS | NATO | European Defence Agency""",
    },

    # ==========================================================================
    # BATCH V2: NATO/War Framing Claims
    # Focus: Causal chain breaking, no false balance, no NATO debate drift
    # ==========================================================================
    "blame_reversal": {
        "v2_001": """This inverts documented causality. Russia launched a full-scale invasion of Ukraine on Feb 24, 2022. NATO is a defensive alliance that did not attack Russia. Reversing aggressor and defender distorts the factual record. Sources: UN General Assembly | ICC | OSCE""",
    },
    "aggressor_victim_inversion": {
        "v2_002": """This reverses documented events. Russia mobilized troops and invaded Ukraine. No European country attacked Russia. Framing the aggressor as "forced to react" rewrites history. Sources: UN Security Council | OSCE | Reuters""",
    },
    "security_framing": {
        "v2_003": """This omits key context. Sovereign nations choose their alliances. Russia's invasion violated Ukraine's territorial integrity under international law. Security concerns do not justify invading a neighbor. Sources: UN Charter Art. 2 | Budapest Memorandum | OSCE""",
    },
    "false_causality": {
        "v2_004": """This is factually incorrect. Russia invaded Ukraine with a large-scale military operation on February 24, 2022. Documented evidence confirms Russia initiated the war. Inverting causality is disinformation. Sources: UN General Assembly A/RES/ES-11/1 | ICC | OSCE SMM""",
    },
    "defensive_war_frame": {
        "v2_005": """This misrepresents international law. Invading a sovereign country is not "defense." NATO expansion occurs through voluntary membership requests by sovereign states. Russia attacked; Ukraine defends. Sources: UN Charter | NATO Treaty Art. 5 | OSCE""",
    },
    "proxy_war_narrative": {
        "v2_006": """This erases Ukrainian agency. Ukraine is defending its territory against Russian invasion. Support from allies does not make Ukraine a "proxy." Ukrainians are fighting for their own country. Sources: UN General Assembly | EU Council | OSCE""",
    },
    "inevitability_frame": {
        "v2_007": """This removes Russian agency. Russia chose to invade. War was not "inevitable" — it was a decision made in Moscow. Framing aggression as unavoidable absolves the aggressor. Sources: UN Security Council records | ICC | OSCE""",
    },
    "ignored_warnings_frame": {
        "v2_008": """This frames aggression as justified response. Diplomatic disagreements do not justify military invasion. Russia had alternatives to war. "Warnings ignored" does not make invasion lawful. Sources: UN Charter | Vienna Convention | OSCE""",
    },

    # ==========================================================================
    # STARMER/CHINA/UK SECURITY BATCH
    # Focus: threat assessment accuracy, no false equivalence, historical nuance
    # ==========================================================================
    "threat_downplay": {
        "v1_001": """This omits documented assessments. UK security agencies and government reviews explicitly identify China as a systemic challenge, citing cyber operations, espionage, and influence activities. Calling this a "non-threat" contradicts official risk evaluations rather than disputing opinions. Sources: UK Integrated Review Refresh 2023 | MI5 public statements | UK Parliament ISC""",
    },
    "propaganda_frame": {
        "v1_002": """This reverses how security threats are defined. Threat assessments are based on capabilities and actions — cyber intrusions, economic coercion, and intelligence activity — not on formal declarations of hostility. Labeling this as propaganda misrepresents the criteria used by security services. Sources: UK National Cyber Security Centre | MI5 | NATO Strategic Concept""",
    },
    "power_deflection": {
        "v1_003": """This oversimplifies global power metrics. China is a leading actor in trade, technology supply chains, and international institutions, regardless of how one ranks military or political influence. Dismissing this ignores measurable economic and technological realities. Sources: World Bank | IMF | OECD trade data""",
    },
    "uk_delegitimization": {
        "v1_004": """This generalises a real problem beyond evidence. The UK has faced serious money-laundering vulnerabilities, particularly via property and shell companies, but also introduced major reforms to address them. Calling the entire system a "machine" removes important legal and regulatory context. Sources: UK National Crime Agency | Transparency International UK | UK Economic Crime Plan""",
    },
    "expansion_denial": {
        "v1_005": """This is factually incomplete. China has asserted territorial claims in the South China Sea, enacted the Hong Kong National Security Law, and increased pressure on Taiwan. These actions show geopolitical expansion of control, even if framed differently from historical conquest. Sources: UNCLOS tribunal ruling 2016 | UK Foreign Office | International Crisis Group""",
    },
    "submission_frame": {
        "v1_006": """This frames security as submission. International relations are governed by law, alliances, and deterrence, not by avoiding disagreement with powerful states. Stability depends on rules and accountability, not on silence toward coercive behavior. Sources: UN Charter | NATO Strategic Concept | Chatham House analyses""",
    },
    "colonial_blame_shift": {
        "v1_007": """This compresses complex histories into a single cause. British colonial decisions contributed to several long-term conflicts, but regional dynamics, post-independence politics, and later interventions also played decisive roles. One-actor explanations distort historical causality. Sources: Oxford History of the British Empire | UN archives | Encyclopaedia Britannica""",
    },
    "influence_denial": {
        "v1_008": """This omits documented foreign influence activity. Alongside trade, China conducts diplomatic pressure, information campaigns, and strategic investments with political conditions attached. Trade and influence are not separate domains. Sources: EU External Action Service | Australian Strategic Policy Institute | UK Parliament reports""",
    },

    # ==========================================================================
    # STARMER/CHINA/UK v2 - GREY ZONE CLAIMS
    # Focus: Acknowledge real core, reframe without dismissal, no false equivalence
    # ==========================================================================
    "provocation_frame": {
        "v2_001": """This inverts established causality. UK naval deployments operate under international law and freedom of navigation, not territorial provocation. China's threat assessment is based on documented cyber operations, espionage, and coercive influence — not UK ship movements. Presence is not escalation; unlawful pressure and interference are. Sources: UK Integrated Review 2023 | UNCLOS | MI5""",
    },
    "empire_legacy_hypocrisy": {
        "v2_002": """This conflates historical responsibility with present-day security analysis. Colonial history is real and documented, but it does not negate current threat assessments based on contemporary actions. Security evaluations measure capabilities, intent, and ongoing operations — not moral balance sheets. Past wrongdoing does not cancel present risks. Sources: UK National Archives | Chatham House | UN Charter""",
    },
    "restitution_deflection": {
        "v2_003": """This substitutes motive speculation for evidence. Restitution debates are legitimate and ongoing. Security assessments are based on documented activities — cyber intrusions, espionage, influence operations — not museum disputes. Conflating the two avoids the actual evidence. Sources: UK Parliament ISC | British Museum policy | MI5""",
    },
    "economic_dependence_trap": {
        "v2_004": """This assumes economic ties preclude security risks. Interdependence is real — and so are documented cyber operations, IP theft, and influence campaigns. Security assessments address risk, not trade volume. The UK's own reviews acknowledge this complexity. Sources: UK Integrated Review | NCSC | World Bank trade data""",
    },
    "selective_threat_framing": {
        "v2_005": """This raises a valid question about consistency — and does not answer it. Double standards in foreign policy exist. That does not make documented Chinese intelligence activity, cyber intrusions, or economic coercion fictional. Both critiques can coexist. Sources: UK Parliament ISC | Amnesty International | MI5""",
    },
    "kinetic_reduction": {
        "v2_006": """This misrepresents how security threats are defined. Modern threats are assessed by capability and behaviour, including cyber intrusion, espionage, and influence operations — not declared wars. UK intelligence agencies have documented sustained China-linked activity targeting institutions and infrastructure. Absence of missiles does not equal absence of threat. Sources: MI5 | UK National Cyber Security Centre | NATO Strategic Concept""",
    },
    "cold_war_projection": {
        "v2_007": """This dismisses assessments as psychology, not evidence. Security reviews cite documented cyber intrusions, espionage cases, and economic pressure — not historical analogy. Labeling analysis as "paranoia" does not address the specific evidence presented. Sources: UK Integrated Review | MI5 public statements | NCSC reports""",
    },
    "sovereignty_reversal": {
        "v2_008": """This compares historical colonialism to current intelligence assessments. Both can be critiqued — but documented cyber operations, espionage, and coercion are not negated by Britain's imperial past. Moral accounting does not replace risk analysis. Sources: UK Parliament ISC | Oxford History | MI5""",
    },
    "domestic_distraction": {
        "v2_009": """This attributes motive without evidence. Governments do use external threats for domestic purposes — and that does not fabricate documented cyber intrusions, espionage cases, or influence operations. Cynicism about motive is not the same as disproving evidence. Sources: UK Integrated Review | MI5 | Transparency International""",
    },
    "influence_normalisation": {
        "v2_010": """This normalises by equivalence. All major powers conduct intelligence — and scale, targeting, and methods differ. UK assessments cite specific Chinese operations, not generic espionage. Saying "everyone does it" does not address documented scope and intent. Sources: UK Parliament ISC | NCSC | Australian ASPI""",
    },
    "rules_order_skepticism": {
        "v2_011": """This critiques selective enforcement — a valid concern. International norms are applied inconsistently. That does not make documented Chinese territorial claims, coercion, or cyber operations compliant with those norms. Critique of enforcement is not evidence of compliance. Sources: UNCLOS tribunal 2016 | UN Charter | Chatham House""",
    },
    "security_inflation": {
        "v2_012": """This questions language, not evidence. "Epoch-defining" is a framing choice — and the underlying assessments cite documented cyber intrusions, espionage cases, and economic leverage. Critiquing rhetoric is valid; dismissing evidence because of word choice is not. Sources: UK Integrated Review | MI5 | NCSC threat reports""",
    },
}


def generate_mock_response(
    claim_text: str,
    claim_id: str,
    cluster: str,
    tone_variant: str,
    sources: List[Dict],
    language: str = "en"
) -> str:
    """
    Generate a Guardian response for bench testing.

    Uses pre-defined templates where available, falls back to generated.
    """
    # Check for pre-defined response
    if cluster in GUARDIAN_RESPONSES_TEMPLATES:
        if claim_id in GUARDIAN_RESPONSES_TEMPLATES[cluster]:
            return GUARDIAN_RESPONSES_TEMPLATES[cluster][claim_id]

    # Fallback: generate response
    source_names = [s.get("publisher", s.get("title", ""))[:25] for s in sources[:3]]
    while len(source_names) < 3:
        defaults = ["EU Commission", "European Parliament", "EEAS"]
        source_names.append(defaults[len(source_names)])
    sources_line = f"Sources: {' | '.join(source_names)}"

    # Tone-specific opening
    openings = {
        "boundary_strict": "Stop. This claim misrepresents EU democratic processes.",
        "boundary_firm": "This claim is demonstrably incorrect and misleading.",
        "boundary_educational": "This requires clarification with documented facts."
    }

    opening = openings.get(tone_variant, openings["boundary_firm"])

    # Build response (4-5 sentences, under 450 chars)
    response_parts = [
        opening,
        "EU leadership is appointed through democratic processes involving elected governments and the European Parliament.",
        "The system is representative democracy, not direct election.",
        "Criticism is valid — mislabeling democratic structures is not.",
        sources_line
    ]

    return " ".join(response_parts)


def run_batch(
    batch_path: Path,
    output_dir: Path,
    use_mock_sources: bool = True,
    generate_responses: bool = True
) -> Dict:
    """
    Run a batch of claims through the Guardian ML pipeline.

    Args:
        batch_path: Path to batch JSON file
        output_dir: Directory for output files
        use_mock_sources: Use mock sources instead of API calls
        generate_responses: Generate mock response texts

    Returns:
        Summary statistics
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load batch
    batch = load_batch(batch_path)
    batch_meta = {k: v for k, v in batch.items() if k != "claims"}
    claims = batch.get("claims", [])

    print(f"Loaded batch: {batch_meta.get('batch_id', 'unknown')}")
    print(f"Claims: {len(claims)}")
    print(f"Mode: {batch_meta.get('mode', 'unknown')}")

    # Initialize components
    generator = get_generator()
    scoreboard = get_scoreboard()

    # Results
    results = []
    response_logs = []

    # Process each claim
    for i, claim in enumerate(claims):
        claim_id = claim.get("claim_id", f"claim_{i}")
        claim_text = claim.get("text", "")
        cluster = claim.get("cluster", "unknown")

        print(f"\n[{i+1}/{len(claims)}] Processing: {claim_id}")
        print(f"  Text: {claim_text[:60]}...")
        print(f"  Cluster: {cluster}")

        # Get source candidates (topic-aware)
        topic = batch_meta.get("common_params", {}).get("topic", "eu_ukraine")
        source_candidates = create_source_candidates(mock=use_mock_sources, topic=topic)

        # Run ML pipeline
        guardian_response = generator.prepare_response(
            claim_text=claim_text,
            source_candidates=source_candidates
        )

        # Use bench source selection (bypasses strict filters)
        selected_sources = select_sources_for_bench(
            source_candidates,
            guardian_response.claim_analysis.keywords,
            n=3
        )

        # Generate response text
        if generate_responses:
            response_text = generate_mock_response(
                claim_text=claim_text,
                claim_id=claim_id,
                cluster=cluster,
                tone_variant=guardian_response.tone_variant,
                sources=[s.model_dump() for s in selected_sources],
                language=guardian_response.claim_analysis.language
            )
        else:
            response_text = ""

        # Score the response with risk-aware boundary detection
        source_urls = [s.url for s in selected_sources]
        claim_type_values = [ct.value for ct in guardian_response.claim_analysis.claim_types]
        risk_level_value = guardian_response.claim_analysis.risk_level.value

        score = scoreboard.score_response(
            response_id=guardian_response.response_id,
            response_text=response_text,
            sources=source_urls,
            risk_level=risk_level_value,
            claim_types=claim_type_values
        )

        # Build result entry
        result = {
            "response_id": guardian_response.response_id,
            "claim_id": claim_id,
            "batch_id": batch_meta.get("batch_id"),
            "timestamp": datetime.now().isoformat(),

            # Input
            "claim_text": claim_text,
            "cluster": cluster,

            # Analysis
            "claim_type": [ct.value for ct in guardian_response.claim_analysis.claim_types],
            "risk_level": guardian_response.claim_analysis.risk_level.value,
            "language": guardian_response.claim_analysis.language,
            "keywords": guardian_response.claim_analysis.keywords,

            # Decision
            "decision_id": guardian_response.decision_id,
            "tone_variant": guardian_response.tone_variant,
            "source_mix": guardian_response.source_mix,

            # Sources (from bench selection)
            "sources_selected": [s.model_dump() for s in selected_sources],
            "source_count": len(selected_sources),
            "source_line": f"Sources: {' | '.join([s.publisher or s.title[:20] for s in selected_sources])}",

            # Response
            "response_text": response_text,
            "char_count": len(response_text),

            # Score
            "violations": [v.value for v in score.violations],
            "violation_count": score.violation_count,
            "genericness_score": score.genericness_score,
            "escalation_risk": score.escalation_risk,

            # Boundary detection (risk-aware)
            "boundary_detected": score.boundary_detected,
            "boundary_type": score.boundary_type.value,

            # Meta
            "mode": batch_meta.get("mode", "shadow"),
            "avatar": batch_meta.get("avatar", "guardian")
        }

        results.append(result)

        # Log for ResponseLog format (for replay.py compatibility)
        response_log = {
            "response_id": guardian_response.response_id,
            "claim_id": claim_id,
            "timestamp": datetime.now().isoformat(),
            "claim_text": claim_text,
            "claim_type": [ct.value for ct in guardian_response.claim_analysis.claim_types],
            "risk_level": guardian_response.claim_analysis.risk_level.value,
            "language": guardian_response.claim_analysis.language,
            "tone_variant": guardian_response.tone_variant,
            "source_mix": guardian_response.source_mix,
            "decision_id": guardian_response.decision_id,
            "response_text": response_text,
            "sources_used": [s.model_dump() for s in selected_sources],
            # Simulated metrics (for replay testing)
            "reward": None,  # Will be filled by feedback
            "metrics": None
        }
        response_logs.append(response_log)

        print(f"  -> Tone: {guardian_response.tone_variant}")
        print(f"  -> Sources: {len(selected_sources)}")
        print(f"  -> Violations: {score.violation_count}")
        print(f"  -> Boundary: {score.boundary_type.value}")
        print(f"  -> Chars: {len(response_text)}")

    # Write outputs
    batch_id = batch_meta.get("batch_id", "batch")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Full results
    results_file = output_dir / f"{batch_id}_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "batch_meta": batch_meta,
            "processed_at": datetime.now().isoformat(),
            "results": results
        }, f, indent=2, ensure_ascii=False)

    # JSONL for replay.py
    responses_file = output_dir / "guardian_responses.jsonl"
    with open(responses_file, 'a', encoding='utf-8') as f:
        for log in response_logs:
            f.write(json.dumps(log, ensure_ascii=False) + "\n")

    # Summary
    summary = {
        "batch_id": batch_meta.get("batch_id"),
        "claims_processed": len(claims),
        "results_file": str(results_file),
        "responses_file": str(responses_file),
        "scoreboard_summary": scoreboard.get_summary().model_dump()
    }

    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)
    print(f"Claims processed: {len(claims)}")
    print(f"Results: {results_file}")
    print(f"Responses JSONL: {responses_file}")
    print(f"\nScoreboard Summary:")
    print(f"  Avg chars: {summary['scoreboard_summary']['avg_chars']}")
    print(f"  Avg violations: {summary['scoreboard_summary']['avg_violations']}")
    print(f"  Violation rate: {summary['scoreboard_summary']['violation_rate']:.1%}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Run claim batch through Guardian ML Pipeline"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to batch JSON file"
    )
    parser.add_argument(
        "--output", "-o",
        default="demo_data/ml",
        help="Output directory for results"
    )
    parser.add_argument(
        "--mock-sources",
        action="store_true",
        default=True,
        help="Use mock sources instead of API calls"
    )
    parser.add_argument(
        "--no-responses",
        action="store_true",
        help="Skip response text generation"
    )

    args = parser.parse_args()

    batch_path = Path(args.input)
    if not batch_path.exists():
        print(f"Error: Batch file not found: {batch_path}")
        sys.exit(1)

    output_dir = Path(args.output)

    summary = run_batch(
        batch_path=batch_path,
        output_dir=output_dir,
        use_mock_sources=args.mock_sources,
        generate_responses=not args.no_responses
    )

    print("\nDone!")


if __name__ == "__main__":
    main()
