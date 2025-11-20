from typing import List, Dict, Optional


def claim_vs_proof_script(
    claim: str,
    proofs: List[Dict[str, str]],
    persona: str = "GuardianAvatar",
    language: str = "en",
    brand_name: Optional[str] = None,
    co_brand: bool = False,
) -> Dict:
    """Return a short-form video/script outline for the Claim vs. Proof series.

    proofs: list of {"title", "url"}
    """
    opener = {
        "en": f"{persona} here. Claim vs. Proof — 30 seconds.",
        "de": f"{persona} hier. Claim vs. Proof — 30 Sekunden."
    }[language]

    brand_tag = None
    if co_brand and brand_name:
        brand_tag = {
            "en": f"Co-presented with {brand_name}.",
            "de": f"Gemeinsam mit {brand_name}."
        }[language]

    proof_lines = []
    for i, p in enumerate(proofs[:3], 1):
        proof_lines.append({
            "en": f"Proof {i}: {p.get('title','Source')} ({p.get('url','')})",
            "de": f"Beleg {i}: {p.get('title','Quelle')} ({p.get('url','')})"
        }[language])

    closer = {
        "en": "Share facts. Tag a friend who saw the claim.",
        "de": "Teile Fakten. Markiere eine Person, die die Behauptung gesehen hat."
    }[language]

    return {
        "format": "claim_vs_proof",
        "language": language,
        "persona": persona,
        "branding": {
            "co_brand": co_brand,
            "brand_name": brand_name,
            "brand_tag": brand_tag,
        },
        "beats": [
            {"type": "hook", "text": opener},
            {"type": "claim", "text": claim},
            {"type": "proofs", "lines": proof_lines},
            {"type": "cta", "text": closer},
        ],
        "suggested_hashtags": ["#TruthShield", "#ClaimVsProof"],
    }


def investigative_thread(
    topic: str,
    key_findings: List[str],
    sources: List[Dict[str, str]],
    astro_score: Optional[float] = None,
    persona: str = "GuardianAvatar",
    language: str = "en",
    brand_name: Optional[str] = None,
    co_brand: bool = False,
) -> Dict:
    """Return a structured thread outline for investigative posts."""
    header = {
        "en": f"INVESTIGATION: {topic}",
        "de": f"UNTERSUCHUNG: {topic}"
    }[language]

    astro_line = None
    if astro_score is not None:
        astro_line = {
            "en": f"Coordinated behavior score: {astro_score}/10",
            "de": f"Koordinations-Score: {astro_score}/10"
        }[language]

    src_lines = []
    for s in sources[:5]:
        src_lines.append(f"{s.get('title','Source')}: {s.get('url','')}")

    closing = {
        "en": "We invite independent review. Full evidence archived.",
        "de": "Wir laden zur unabhängigen Prüfung ein. Vollständige Evidenz archiviert."
    }[language]

    return {
        "format": "investigative_thread",
        "language": language,
        "persona": persona,
        "branding": {
            "co_brand": co_brand,
            "brand_name": brand_name,
        },
        "thread": [
            header,
            *(key_findings[:4]),
            *(src_lines),
            *( [astro_line] if astro_line else [] ),
            closing,
        ],
        "suggested_hashtags": ["#TruthShield", "#Investigation"],
    }



