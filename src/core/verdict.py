"""
Verdict determination and special-case override logic.
Extracted from ai_engine.py (P3.7).
"""
import logging
import unicodedata
from typing import Dict, List

from src.core.source_aggregation import Source

logger = logging.getLogger(__name__)


def determine_verdict(ai_analysis: Dict, sources: List[Source]) -> Dict:
    """Enhanced verdict logic with clearer thresholds for better misinformation detection"""

    # Default to uncertain
    verdict = {
        "is_fake": False,
        "confidence": 0.5,
        "explanation": "Insufficient information to make determination",
        "category": "uncertain"
    }

    try:
        plausibility = ai_analysis.get("plausibility_score", 50)
        red_flags = ai_analysis.get("red_flags", [])
        misinformation_indicators = ai_analysis.get("misinformation_indicators", [])
        reasoning = ai_analysis.get("reasoning", "")
        factual_basis = ai_analysis.get("factual_basis", "")

        logger.info(f"Verdict analysis: plausibility={plausibility}, red_flags={len(red_flags)}, indicators={len(misinformation_indicators)}")

        # Very strong indicators of misinformation
        if plausibility <= 25:
            confidence_score = 0.9  # Very confident it's false
            verdict.update({
                "is_fake": True,
                "confidence": confidence_score,
                "explanation": f"Very low plausibility ({plausibility}%). {reasoning}. {factual_basis}",
                "category": "misinformation"
            })
        elif plausibility <= 40:
            confidence_score = 0.85  # Confident it's false
            verdict.update({
                "is_fake": True,
                "confidence": confidence_score,
                "explanation": f"Low plausibility ({plausibility}%) with red flags: {', '.join(red_flags[:3])}",
                "category": "likely_false"
            })
        elif len(red_flags) >= 3 or len(misinformation_indicators) >= 2:
            confidence_score = 0.8  # Multiple indicators = likely false
            verdict.update({
                "is_fake": True,
                "confidence": confidence_score,
                "explanation": f"Multiple misinformation indicators: {', '.join(misinformation_indicators[:3])}",
                "category": "likely_false"
            })
        elif plausibility >= 80 and len(sources) > 0:
            confidence_score = 0.8  # High plausibility with sources
            verdict.update({
                "is_fake": False,
                "confidence": confidence_score,
                "explanation": f"High plausibility ({plausibility}%) supported by {len(sources)} sources",
                "category": "likely_true"
            })
        elif plausibility >= 60:
            confidence_score = 0.7  # Moderately likely true
            verdict.update({
                "is_fake": False,
                "confidence": confidence_score,
                "explanation": f"Moderate plausibility ({plausibility}%) - appears accurate",
                "category": "likely_true"
            })
        else:
            # Truly uncertain cases
            verdict.update({
                "confidence": 0.6,
                "explanation": f"Mixed indicators: plausibility {plausibility}%, {len(red_flags)} concerns, needs more verification",
                "category": "needs_verification"
            })

        logger.info(f"Final verdict: is_fake={verdict['is_fake']}, confidence={verdict['confidence']}, category={verdict['category']}")

    except Exception as e:
        logger.error(f"Verdict determination failed: {e}")

    return verdict


def apply_special_case_overrides(text: str, sources: List[Source], verdict: Dict) -> Dict:
    """
    Apply deterministic verdict overrides for high-sensitivity civic claims.
    Ensures EU institutional misinformation (e.g., Ursula von der Leyen legitimacy)
    never slips through with a "likely true" classification due to AI variance.
    """
    text_lower = (text or "").lower()
    candidate_texts = {text_lower}

    def _strip_diacritics(value: str) -> str:
        return "".join(
            ch for ch in unicodedata.normalize("NFKD", value)
            if not unicodedata.combining(ch)
        )

    candidate_texts.add(_strip_diacritics(text_lower))

    # Handle malformed UTF-8 sequences coming from certain user agents
    try:
        cp1252_fixed = (text or "").encode("latin-1").decode("utf-8").lower()
        candidate_texts.add(cp1252_fixed)
        candidate_texts.add(_strip_diacritics(cp1252_fixed))
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    def _contains(term: str) -> bool:
        return any(term in variant for variant in candidate_texts)

    # Ursula von der Leyen election denial claims
    if any(_contains(keyword) for keyword in ["ursula", "von der leyen", "leyen"]) and \
       any(_contains(neg) for neg in [
           "nicht gewählt", "nicht gewaehlt", "wurde nicht gewählt", "wurde nicht gewaehlt",
           "not elected", "was not elected", "nicht bestätigt", "not confirmed", "abgewählt"
       ]):

        eu_parl_url = "https://www.europarl.europa.eu/news/de/press-room/20240710IPR22812/parlament-wahlt-ursula-von-der-leyen-erneut-zur-kommissionsprasidentin"
        if not any(src.url == eu_parl_url for src in sources):
            sources.insert(0, Source(
                url=eu_parl_url,
                title="Europäisches Parlament bestätigt Ursula von der Leyen",
                snippet="Am 18. Juli 2024 erhielt Ursula von der Leyen 401 Stimmen und wurde erneut zur EU-Kommissionspräsidentin gewählt.",
                credibility_score=0.97,
                date_published="2024-07-18"
            ))

        verdict.update({
            "is_fake": True,
            "category": "misinformation",
            "confidence": max(verdict.get("confidence", 0.0), 0.95),
            "explanation": "Offizielles Ergebnis des Europäischen Parlaments vom 18. Juli 2024: Ursula von der Leyen wurde mit 401 Stimmen zur Kommissionspräsidentin gewählt."
        })

    return verdict
