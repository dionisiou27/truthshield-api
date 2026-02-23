"""
TruthShield Text-Level Astroturfing & Contradiction Detection

Heuristic detectors for coordinated inauthentic behavior patterns,
political astroturfing, and logical contradictions in text.

Extracted from ai_engine.py for maintainability.
Note: For network-level coordinated behavior detection,
see src/core/coordinated_behavior.py (14-feature weighted model).
"""

from typing import Dict, List, Optional, Any

# ---------------------------------------------------------------------------
# Political Astroturfing
# ---------------------------------------------------------------------------

# Known legitimate politicians who are often targeted by astroturfing
ELECTED_POLITICIANS = [
    "angela merkel", "merkel", "angela",
    "emmanuel macron", "macron", "emmanuel",
    "olaf scholz", "scholz", "olaf",
    "joe biden", "biden", "joseph biden",
    "donald trump", "trump", "donald",
    "volodymyr zelensky", "zelensky", "volodymyr",
]

APPOINTED_OFFICIALS = [
    "ursula von der leyen", "von der leyen", "ursula",
]

LEGITIMATE_POLITICIANS = ELECTED_POLITICIANS + APPOINTED_OFFICIALS

CORRUPTION_PATTERNS = [
    "corrupt", "crooked", "dirty", "shady", "sleazy",
    "bribed", "bought", "sold out", "in pocket",
    "criminal", "fraud", "scam", "con artist",
]

CONSPIRACY_LANGUAGE = [
    "deep state", "establishment", "elites", "elite",
    "mainstream media", "controlled media", "fake news",
    "sheeple", "sheep", "wake up", "open your eyes",
    "the truth", "they don't want you to know",
    "mainstream won't tell you", "controlled narrative",
]


def detect_political_astroturfing(text_lower: str) -> Dict[str, Any]:
    """Detect specific political astroturfing patterns."""
    targets_elected = any(p in text_lower for p in ELECTED_POLITICIANS)
    targets_appointed = any(p in text_lower for p in APPOINTED_OFFICIALS)
    targets_politician = targets_elected or targets_appointed
    has_corruption = any(p in text_lower for p in CORRUPTION_PATTERNS)
    has_conspiracy = any(p in text_lower for p in CONSPIRACY_LANGUAGE)

    score = 0.0
    if targets_politician and has_corruption:
        score += 0.6 if targets_elected else 0.4
    if has_conspiracy:
        score += 0.3
    if targets_politician and has_conspiracy:
        score += 0.2

    return {
        "targets_legitimate_politician": targets_politician,
        "targets_elected_politician": targets_elected,
        "targets_appointed_official": targets_appointed,
        "has_corruption_accusations": has_corruption,
        "has_conspiracy_language": has_conspiracy,
        "political_astroturfing_score": min(score, 1.0),
        "is_political_astroturfing": score > 0.7,
        "detected_patterns": {
            "corruption_terms": [p for p in CORRUPTION_PATTERNS if p in text_lower],
            "conspiracy_terms": [p for p in CONSPIRACY_LANGUAGE if p in text_lower],
            "targeted_politicians": [p for p in LEGITIMATE_POLITICIANS if p in text_lower],
            "targeted_elected": [p for p in ELECTED_POLITICIANS if p in text_lower],
            "targeted_appointed": [p for p in APPOINTED_OFFICIALS if p in text_lower],
        },
    }


# ---------------------------------------------------------------------------
# Astroturfing Indicators (Text + Context)
# ---------------------------------------------------------------------------

COORDINATED_PHRASES = [
    "i'm just a regular person", "as a concerned citizen", "i'm not political but",
    "i've never posted before", "i usually don't comment", "i'm just sharing",
    "this needs to be shared", "everyone needs to know", "spread the word",
    "wake up people", "open your eyes", "the truth is out there",
    "they don't want you to know", "mainstream media won't tell you",
    "i'm not a bot", "i'm real", "this is not fake",
    "corrupt politician", "crooked politician", "dirty politician",
    "they're all corrupt", "politicians are all the same",
    "wake up sheeple", "sheeple", "sheep", "wake up",
    "the establishment", "deep state", "elites",
    "mainstream media", "fake news", "controlled media",
]

EMOTIONAL_TRIGGERS = [
    "outraged", "disgusted", "shocked", "appalled", "furious",
    "this is unacceptable", "how dare they", "i can't believe",
    "this is sick", "disgraceful", "unbelievable",
]

ASTROTURF_PATTERNS = [
    "grassroots", "organic", "natural", "authentic", "genuine",
    "real people", "ordinary citizens", "regular folks",
    "the silent majority", "the real americans", "patriots",
    "we the people", "enough is enough", "time to act",
    "corrupt", "crooked", "dirty", "shady", "sleazy",
    "establishment", "elite", "elites", "deep state",
    "mainstream", "controlled", "sheeple", "sheep",
    "wake up", "open your eyes", "the truth",
]


def detect_astroturfing_indicators(
    text: str, context: Optional[Dict] = None
) -> Dict[str, Any]:
    """Detect potential astroturfing indicators in text and context."""
    text_lower = text.lower()

    # 1. Coordinated language
    found_coordinated = [p for p in COORDINATED_PHRASES if p in text_lower]

    # 2. Emotional manipulation
    found_emotional = [t for t in EMOTIONAL_TRIGGERS if t in text_lower]

    # 3. Astroturf language
    found_astroturf = [p for p in ASTROTURF_PATTERNS if p in text_lower]

    # 4. Suspicious repetition
    words = text_lower.split()
    word_freq: Dict[str, int] = {}
    for w in words:
        if len(w) > 3:
            word_freq[w] = word_freq.get(w, 0) + 1
    suspicious_repetition = [
        f"{w}({c}x)" for w, c in word_freq.items() if c > 3 and len(w) > 5
    ]

    # 5. Score
    score = (
        len(found_coordinated) * 0.2
        + len(found_emotional) * 0.15
        + len(found_astroturf) * 0.25
        + len(suspicious_repetition) * 0.1
    )

    # 6. Context-based indicators
    context_indicators: List[str] = []
    if context:
        if context.get("post_frequency", 0) > 10:
            context_indicators.append("high_frequency_posting")
            score += 0.3
        if context.get("shared_ips", 0) > 5:
            context_indicators.append("shared_ip_addresses")
            score += 0.4
        if context.get("new_accounts", 0) > 3:
            context_indicators.append("new_account_cluster")
            score += 0.3

    # 7. Political astroturfing sub-score
    political = detect_political_astroturfing(text_lower)

    return {
        "astroturfing_score": min(score, 1.0),
        "has_coordinated_language": len(found_coordinated) > 0,
        "coordinated_phrases": found_coordinated,
        "has_emotional_manipulation": len(found_emotional) > 0,
        "emotional_triggers": found_emotional,
        "has_astroturf_patterns": len(found_astroturf) > 0,
        "astroturf_patterns": found_astroturf,
        "has_suspicious_repetition": len(suspicious_repetition) > 0,
        "suspicious_repetition": suspicious_repetition,
        "context_indicators": context_indicators,
        "is_likely_astroturfing": score > 0.6,
        "political_astroturfing": political,
    }


# ---------------------------------------------------------------------------
# Logical Contradiction Detection
# ---------------------------------------------------------------------------

CONTRADICTION_PAIRS = [
    ("dead", "alive"), ("alive", "dead"),
    ("true", "false"), ("false", "true"),
    ("real", "fake"), ("fake", "real"),
    ("exists", "doesn't exist"), ("doesn't exist", "exists"),
    ("happened", "didn't happen"), ("didn't happen", "happened"),
    ("working", "broken"), ("broken", "working"),
    ("safe", "dangerous"), ("dangerous", "safe"),
    ("proven", "unproven"), ("unproven", "proven"),
    ("confirmed", "denied"), ("denied", "confirmed"),
    ("yes", "no"), ("no", "yes"),
    ("and not", "and"), ("not", "and not"),
]

AMBIGUOUS_PHRASES = [
    "is not dead and alive", "dead and alive",
    "true and false", "false and true",
    "real and fake", "fake and real",
    "both true and false", "neither true nor false",
]


def detect_logical_contradictions(text: str) -> Dict[str, Any]:
    """Detect logical contradictions in the text."""
    text_lower = text.lower()

    found_contradictions = [
        f"{a} and {b}" for a, b in CONTRADICTION_PAIRS
        if a in text_lower and b in text_lower
    ]
    found_ambiguous = [p for p in AMBIGUOUS_PHRASES if p in text_lower]

    return {
        "has_contradictions": len(found_contradictions) > 0,
        "contradictions": found_contradictions,
        "has_ambiguous_phrasing": len(found_ambiguous) > 0,
        "ambiguous_phrases": found_ambiguous,
        "logical_consistency_score": 0.0 if found_contradictions or found_ambiguous else 1.0,
    }
