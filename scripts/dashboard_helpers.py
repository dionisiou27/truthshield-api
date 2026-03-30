"""
Helper functions for the TruthShield Streamlit dashboard.
Mock data generation, API status checks, and response building.
"""
import os
from datetime import datetime
from typing import List, Dict

from src.ml.guardian.claim_router import ClaimAnalysis
from src.ml.guardian.source_ranker import SourceCandidate, SourceClass
from src.ml.learning.bandit import ToneVariant
from src.core.platform_config import get_platform_spec


TONE_COLORS = {
    "empathic": "#4CAF50",
    "witty": "#FF9800",
    "firm": "#F44336",
    "spicy": "#9C27B0",
}

AVATARS = [
    "GuardianAvatar",
    "ScienceAvatar",
    "MemeAvatar",
    "PolicyAvatar",
    "EuroShieldAvatar",
]

PLATFORMS = ["tiktok", "twitter", "reddit"]


def mock_source_candidates(claim_analysis: ClaimAnalysis) -> List[SourceCandidate]:
    """Generate plausible mock source candidates based on claim type."""
    claim_type = (
        claim_analysis.claim_types[0].value if claim_analysis.claim_types else "unknown"
    )

    pools = {
        "health_misinformation": [
            ("WHO Fact Sheet – mRNA Vaccines", "https://www.who.int/news-room/feature-stories/detail/mRNA-vaccines", "WHO", SourceClass.PRIMARY_INSTITUTION),
            ("PubMed: mRNA Safety Review 2024", "https://pubmed.ncbi.nlm.nih.gov/12345678", "PubMed", SourceClass.PEER_REVIEWED),
            ("AFP Faktencheck: DNA-Veraenderung", "https://faktencheck.afp.com/mRNA-DNA", "AFP Faktencheck", SourceClass.IFCN_FACTCHECK),
            ("CDC – Understanding mRNA", "https://www.cdc.gov/vaccines/mRNA.html", "CDC", SourceClass.PRIMARY_INSTITUTION),
            ("Correctiv Faktencheck", "https://correctiv.org/faktencheck/mRNA", "Correctiv", SourceClass.IFCN_FACTCHECK),
        ],
        "foreign_influence": [
            ("EUvsDisinfo: Kremlin Narratives", "https://euvsdisinfo.eu/report/kremlin-narratives", "EUvsDisinfo", SourceClass.IFCN_FACTCHECK),
            ("ERR News: Foreign Influence Ops", "https://news.err.ee/foreign-influence", "ERR", SourceClass.REPUTABLE_MEDIA),
            ("NATO StratCom", "https://stratcomcoe.org/analysis", "NATO StratCom", SourceClass.PRIMARY_INSTITUTION),
            ("Reuters Fact Check", "https://www.reuters.com/fact-check", "Reuters", SourceClass.REPUTABLE_MEDIA),
            ("EEAS – Foreign Information Manipulation", "https://www.eeas.europa.eu/eeas/foreign-information-manipulation", "EEAS", SourceClass.PRIMARY_INSTITUTION),
        ],
        "conspiracy_theory": [
            ("Snopes Fact Check", "https://www.snopes.com/fact-check/conspiracy", "Snopes", SourceClass.IFCN_FACTCHECK),
            ("Full Fact UK", "https://fullfact.org/health", "Full Fact", SourceClass.IFCN_FACTCHECK),
            ("DW Fact Check", "https://www.dw.com/en/fact-check", "DW", SourceClass.REPUTABLE_MEDIA),
            ("bpb.de – Verschwoerungstheorien", "https://www.bpb.de/themen/verschwoerungstheorien", "bpb", SourceClass.PRIMARY_INSTITUTION),
        ],
    }

    default_pool = [
        ("Reuters Fact Check", "https://www.reuters.com/fact-check", "Reuters", SourceClass.REPUTABLE_MEDIA),
        ("Correctiv Faktencheck", "https://correctiv.org/faktencheck", "Correctiv", SourceClass.IFCN_FACTCHECK),
        ("European Commission", "https://ec.europa.eu", "EU Commission", SourceClass.PRIMARY_INSTITUTION),
        ("AP News Fact Check", "https://apnews.com/hub/fact-checking", "AP News", SourceClass.REPUTABLE_MEDIA),
        ("bpb.de", "https://www.bpb.de", "bpb", SourceClass.PRIMARY_INSTITUTION),
    ]

    raw = pools.get(claim_type, default_pool)
    candidates = []
    for i, (title, url, publisher, src_class) in enumerate(raw):
        candidates.append(
            SourceCandidate(
                url=url,
                title=title,
                snippet=f"Relevant source for: {claim_analysis.normalized_claim[:80]}",
                publisher=publisher,
                source_class=src_class,
                retrieval_rank=i + 1,
            )
        )
    return candidates


def build_mock_response_text(
    claim_analysis: ClaimAnalysis,
    tone: ToneVariant,
    sources: List[Dict],
    platform: str,
) -> str:
    """Build a template-based response (no OpenAI call)."""
    spec = get_platform_spec(platform)
    lang = claim_analysis.language
    claim_short = claim_analysis.normalized_claim[:120]

    source_names = []
    for s in sources[: spec.required_sources]:
        name = s.get("publisher") or s.get("title", "Source")[:25]
        source_names.append(name)
    while len(source_names) < spec.required_sources:
        source_names.append("EU Commission")

    src_line = " | ".join(source_names)
    src_line = f"Quellen: {src_line}" if lang == "de" else f"Sources: {src_line}"

    tone_openers = {
        "empathic": {"de": "Ich verstehe, warum das beunruhigend klingt.", "en": "I get why this sounds alarming."},
        "witty": {"de": "Nope. Hier ist, was wirklich passiert.", "en": "Nope. Here's what actually happened."},
        "firm": {"de": "Das ist falsch. Die Daten zeigen Folgendes:", "en": "That's false. The data shows:"},
        "spicy": {"de": "Wilde Behauptung. Reality-Check:", "en": "Wild claim. Reality check:"},
    }

    tone_val = tone.value if isinstance(tone, ToneVariant) else tone
    opener = tone_openers.get(tone_val, {}).get(lang, "Fact check:")
    risk_note = (
        f" Risk: {claim_analysis.risk_level.value.upper()}."
        if claim_analysis.risk_level.value in ("high", "critical")
        else ""
    )
    types_str = ", ".join(
        ct.value.replace("_", " ").title() for ct in claim_analysis.claim_types[:2]
    )

    response = (
        f"{opener} "
        f'The claim "{claim_short}" has been classified as {types_str}.{risk_note} '
        f"Multiple authoritative sources confirm this assessment. "
        f"{src_line}"
    )
    if len(response) > spec.max_chars:
        response = response[: spec.max_chars - 3] + "..."
    return response


def check_api_status() -> Dict[str, bool]:
    """Quick check which API keys are configured."""
    keys = {
        "OpenAI": "OPENAI_API_KEY",
        "Google Fact Check": "GOOGLE_API_KEY",
        "News API": "NEWS_API_KEY",
        "ClaimBuster": "CLAIMBUSTER_API_KEY",
        "CORE.ac.uk": "CORE_API_KEY",
        "Twitter/X": "TWITTER_API_KEY",
    }
    return {
        label: bool(os.environ.get(env_var, "").strip())
        for label, env_var in keys.items()
    }
