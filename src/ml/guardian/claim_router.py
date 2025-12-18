"""
Guardian Claim Router v1
Multi-label classification for claim typing and risk assessment.
"""
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple
from pydantic import BaseModel
import re
import logging

logger = logging.getLogger(__name__)


class ClaimType(str, Enum):
    """Claim type classification."""
    HATE_OR_DEHUMANIZATION = "hate_or_dehumanization"
    THREAT_OR_INCITEMENT = "threat_or_incitement"
    DELEGITIMIZATION_FRAME = "delegitimization_frame"
    BLANKET_GENERALIZATION = "blanket_generalization"
    OPINION_WITH_FACTUAL_PREMISE = "opinion_with_factual_premise"
    POLICY_AID_OVERSIGHT = "policy_aid_oversight"
    HEALTH_MISINFORMATION = "health_misinformation"
    SCIENCE_DENIAL = "science_denial"
    CONSPIRACY_THEORY = "conspiracy_theory"
    FOREIGN_INFLUENCE = "foreign_influence"


class RiskLevel(str, Enum):
    """Risk level for claim severity."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ClaimVolatility(str, Enum):
    """
    How quickly the factual basis of a claim can change.
    Critical for TikTok where upload time ≠ claim time.
    """
    VERY_HIGH = "very_high"   # Territorial control, frontlines - changes hourly
    HIGH = "high"             # Active conflicts, breaking events - changes daily
    MEDIUM = "medium"         # Sanctions, policy - changes weekly
    LOW = "low"               # Historical, scientific - stable
    STABLE = "stable"         # Established facts - rarely changes


class TemporalMode(str, Enum):
    """
    Routing decision: should we check LIVE sources or ARCHIVE is OK?
    """
    LIVE_REQUIRED = "live_required"   # Must check current sources, hedge language
    ARCHIVE_OK = "archive_ok"         # Can use established fact-checks
    AMBIGUOUS = "ambiguous"           # Unclear - be cautious


class ResponseMode(str, Enum):
    """
    How Guardian should frame the response.
    Critical distinction: Debunk vs IO-Context vs Live-Situation.

    Priority (highest to lowest): CAUTIOUS > LIVE_SITUATION > IO_CONTEXT > DEBUNK
    IO_CONTEXT is an OVERLAY, not a replacement for LIVE_SITUATION.
    """
    # Classic fact-check: claim is false, here's the truth
    DEBUNK = "debunk"

    # Information Operation context: claim is part of coordinated campaign
    # Response must acknowledge the narrative, not just the facts
    # NOTE: This is often combined with LIVE_SITUATION, not a replacement
    IO_CONTEXT = "io_context"

    # Live situation: facts are fluid, hedge everything
    LIVE_SITUATION = "live_situation"

    # Mixed/unclear: be cautious - HIGHEST priority
    CAUTIOUS = "cautious"


class EvidenceQuality(str, Enum):
    """
    How strong is the available counter-evidence?
    Determines whether we can make strong claims or must hedge.
    """
    STRONG = "strong"      # Multiple high-quality sources, clear factual basis
    MEDIUM = "medium"      # Some evidence, but not comprehensive
    WEAK = "weak"          # Limited evidence, must hedge significantly


class ResponseModeResult(BaseModel):
    """
    Response mode determination result.
    Supports primary + secondary (overlay) modes.
    e.g., LIVE_SITUATION + IO_CONTEXT
    """
    primary: ResponseMode
    secondary: Optional[ResponseMode] = None  # IO overlay if applicable
    io_score: float = 0.0                     # Weighted IO score (0.0-1.0)
    evidence_quality: EvidenceQuality = EvidenceQuality.MEDIUM
    evidence_reasons: List[str] = []          # Why this evidence quality
    mode_reason: str = ""                     # Audit trail for mode selection


class ClaimAnalysis(BaseModel):
    """Result of claim analysis."""
    claim_id: str
    normalized_claim: str
    language: str
    claim_types: List[ClaimType]
    risk_level: RiskLevel
    confidence: float
    reasoning_brief: str
    entities: List[str]
    keywords: List[str]
    requires_guardian: bool
    # TikTok time-awareness fields
    volatility: ClaimVolatility = ClaimVolatility.MEDIUM
    volatility_reason: str = ""        # Audit trail for volatility assessment
    temporal_mode: TemporalMode = TemporalMode.ARCHIVE_OK
    temporal_signals: List[str] = []   # Detected time markers
    is_territorial: bool = False       # Territorial control claim flag
    # IO (Information Operation) awareness - WEIGHTED scoring
    io_score: float = 0.0              # Weighted IO score (0.0-1.0)
    io_indicators: List[str] = []      # Why we think it's IO
    is_io_pattern: bool = False        # io_score >= IO_THRESHOLD
    # Response mode (primary + optional secondary)
    response_mode_result: Optional[ResponseModeResult] = None
    # Legacy field for backwards compatibility
    response_mode: ResponseMode = ResponseMode.DEBUNK


# Pattern definitions for claim typing
HATE_PATTERNS = {
    "de": [
        r"\b(alle|jeder|sämtliche)\s+\w+\s+(sind|müssen|gehören)",
        r"\b(pack|gesindel|abschaum|ungeziefer|ratten|kakerlaken)\b",
        r"\b(entsorgen|ausrotten|vernichten|abschieben)\b",
        r"\b(volksverräter|lügenpresse|systemling)\b",
        r"\b(nicht.*mensch|untermenschen?)\b",
    ],
    "en": [
        r"\b(all|every|each)\s+\w+\s+(are|must|should)",
        r"\b(vermin|rats|cockroaches|animals|savages)\b",
        r"\b(eliminate|exterminate|get rid of|deport)\b",
        r"\b(traitors?|fake news|sheep|NPCs?)\b",
        r"\b(subhuman|not.*human)\b",
    ]
}

THREAT_PATTERNS = {
    "de": [
        r"\b(umbringen|töten|erschießen|aufhängen|lynchen)\b",
        r"\b(werden.*büßen|werden.*bezahlen|werden.*bereuen)\b",
        r"\b(gewalt|angriff|attentat)\b.*\b(verdient|nötig|muss)\b",
        r"\b(stirb|verreck|krepier)\b",
    ],
    "en": [
        r"\b(kill|shoot|hang|lynch|execute)\b",
        r"\b(will.*pay|will.*regret|deserve.*die)\b",
        r"\b(violence|attack).*\b(deserve|need|must)\b",
        r"\b(die|burn|rot)\b",
    ]
}

DELEGITIMIZATION_PATTERNS = {
    "de": [
        r"\b(korrupt|gekauft|bestechlich)\b.*\b(politiker|regierung|eu|un)\b",
        r"\b(diktatur|regime|junta)\b",
        r"\b(wahlfälschung|wahlbetrug|gestohlen.*wahl)\b",
        r"\b(deep\s*state|geheime.*mächte|strippenzieher)\b",
        r"\b(scheindemokratie|fassade)\b",
    ],
    "en": [
        r"\b(corrupt|bought|bribed)\b.*\b(politician|government|eu|un)\b",
        r"\b(dictatorship|regime|junta)\b",
        r"\b(election.*fraud|stolen.*election|rigged)\b",
        r"\b(deep\s*state|shadow.*government|puppet.*masters?)\b",
        r"\b(fake.*democracy|facade)\b",
    ]
}

GENERALIZATION_PATTERNS = {
    "de": [
        r"\b(alle|jeder|kein)\s+\w+\s+(ist|sind|hat|haben)\b",
        r"\b(immer|nie|niemals)\b.*\b(machen|tun|sind)\b",
        r"\b(typisch|so sind sie|die sind halt so)\b",
    ],
    "en": [
        r"\b(all|every|no)\s+\w+\s+(is|are|has|have)\b",
        r"\b(always|never)\b.*\b(do|are|make)\b",
        r"\b(typical|that's how they are|they're all)\b",
    ]
}

HEALTH_MISINFO_PATTERNS = {
    "de": [
        r"\b(impf|vakzin|mrna|biontech|pfizer|moderna|astrazeneca)\b.*\b(gift|tödlich|unfruchtbar|chip|microchip|nanobots?|magnetisch)\b",
        r"\b(impf|vakzin)\w*\b.*\b(autis|krebs|steril|dna|genveränder)\b",
        r"\b(corona|covid)\b.*\b(lüge|fake|erfunden|plandemie|biowaffe)\b",
        r"\b(5g)\b.*\b(krank|krebs|corona|strahlung)\b",
        r"\b(heilung|heilt|kur)\b.*\b(krebs|diabetes|aids)\b",
        r"\b(microchip|nanobots?|tracking)\b.*\b(impf|spritze|injektion)\b",
    ],
    "en": [
        r"\b(vaccine|vaccines|vax|mrna|pfizer|moderna|biontech|astrazeneca)\b.*\b(poison|deadly|infertile|chip|microchip|nanobots?|magnetic|tracking)\b",
        r"\b(vaccine|vaccines|vax)\w*\b.*\b(autis|cancer|steril|dna|alter|modify)\b",
        r"\b(corona|covid)\b.*\b(hoax|fake|invented|plandemic|bioweapon)\b",
        r"\b(5g)\b.*\b(sick|cancer|corona|radiation)\b",
        r"\b(cure|cures|heals)\b.*\b(cancer|diabetes|aids)\b",
        r"\b(microchip|nanobots?|tracking)\b.*\b(vaccine|injection|shot)\b",
    ]
}

CONSPIRACY_PATTERNS = {
    "de": [
        r"\b(rothschild|soros|gates|wef|bilderberg|illuminati|freimaurer)\b",
        r"\b(great\s*reset|neue\s*weltordnung|nwo|bevölkerungsreduktion)\b",
        r"\b(chemtrail|haarp|wettermanipulation)\b",
        r"\b(flache\s*erde|mondlandung.*fake|reptilien)\b",
    ],
    "en": [
        r"\b(rothschild|soros|gates|wef|bilderberg|illuminati|freemasons?)\b",
        r"\b(great\s*reset|new\s*world\s*order|nwo|depopulation)\b",
        r"\b(chemtrail|haarp|weather\s*control)\b",
        r"\b(flat\s*earth|moon\s*landing.*fake|reptilian)\b",
    ]
}

# =============================================================================
# TEMPORAL / VOLATILITY PATTERNS - TikTok Time-Awareness
# =============================================================================

# Territorial control patterns (VERY_HIGH volatility)
TERRITORIAL_PATTERNS = {
    "keywords": [
        # Control verbs
        r"\b(controls?|captured|fallen|took|seized|liberated|lost)\b",
        r"\b(kontrolliert|eingenommen|gefallen|erobert|befreit|verloren)\b",
        # Military movement
        r"\b(advancing|retreating|surrounded|encircled|breakthrough)\b",
        r"\b(vorrücken|rückzug|eingekesselt|durchbruch)\b",
        # Frontline terms
        r"\b(front\s*line|frontline|front)\b",
        r"\b(frontlinie|front)\b",
    ],
    "locations": [
        # Ukraine conflict hotspots (examples - extend as needed)
        r"\b(kupiansk|kupjansk|siversk|pokrovsk|bakhmut|avdiivka|toretsk)\b",
        r"\b(kherson|kharkiv|charkiw|zaporizhzhia|mariupol|melitopol)\b",
        r"\b(donetsk|luhansk|lugansk|crimea|krim)\b",
        # Generic
        r"\b(city|town|village|region|oblast)\s+(of\s+)?\w+\s+(has\s+)?(fallen|captured)\b",
    ]
}

# Live-indicator patterns (signals claim refers to "now")
LIVE_SIGNAL_PATTERNS = {
    "de": [
        r"\b(jetzt|gerade|aktuell|soeben|momentan|derzeit)\b",
        r"\b(heute|heute\s*morgen|heute\s*nacht)\b",
        r"\b(breaking|eilmeldung|just\s*in)\b",
        r"\b(bestätigt|gemeldet|berichtet)\s+(wird|wurde)\b",
    ],
    "en": [
        r"\b(now|right\s*now|currently|just|at\s*this\s*moment)\b",
        r"\b(today|this\s*morning|tonight|as\s*we\s*speak)\b",
        r"\b(breaking|just\s*in|confirmed|reports?\s*say)\b",
        r"\b(is\s+under\s+control|has\s+fallen|has\s+been\s+captured)\b",
    ]
}

# Archive-ok patterns (signals claim is about past/established facts)
ARCHIVE_SIGNAL_PATTERNS = {
    "de": [
        r"\b(immer|schon\s*immer|seit\s*jahren|historisch)\b",
        r"\b(wissenschaftlich\s*bewiesen|längst\s*widerlegt)\b",
        r"\b(bekannt|etabliert|festgestellt)\b",
    ],
    "en": [
        r"\b(always|has\s*always|for\s*years|historically)\b",
        r"\b(scientifically\s*proven|long\s*debunked)\b",
        r"\b(well\s*known|established|documented)\b",
    ]
}

# =============================================================================
# INFORMATION OPERATION (IO) PATTERNS - WEIGHTED SCORING
# =============================================================================
# These patterns suggest the claim is part of a coordinated narrative campaign,
# not just a single false statement. Response must address the narrative.
#
# WEIGHTED scoring instead of simple count:
# - HIGH signal (0.35-0.5): Strong IO markers (bloc_framing, peace_pressure)
# - MEDIUM signal (0.15-0.25): Moderate IO markers (victory_frame, frontline_collapse)
# - LOW signal (0.05-0.15): Weak IO markers (multi_location, absolutist)
#
# IO threshold: io_score >= 0.45 (or 0.5)

IO_THRESHOLD = 0.45  # Score threshold to consider claim as IO pattern

# Signal weights by category
IO_SIGNAL_WEIGHTS = {
    # HIGH signal (0.35-0.50) - Strong IO indicators
    "bloc_framing": 0.45,         # "The West admits..." - classic propaganda
    "peace_pressure": 0.40,       # "Negotiate before X happens" - pressure narrative
    "known_source": 0.40,         # RT, Sputnik, etc.
    "territorial_multi": 0.35,    # Territorial + multi-location combo
    "whitelist_names_io": 0.30,   # Whitelist source explicitly names IO campaign
    # MEDIUM signal (0.15-0.30) - Moderate IO indicators
    "victory_frame": 0.25,        # Victory/defeat narratives
    "frontline_collapse": 0.25,   # "Frontline is collapsing"
    "map_claims": 0.20,           # "Look at the map"
    # LOW signal (0.05-0.15) - Weak IO indicators (common in legit discourse too)
    "multi_location": 0.15,       # Multiple locations in one claim
    "absolutist": 0.10,           # "Completely destroyed"
}

IO_INDICATOR_PATTERNS = {
    # LOW signal: Multiple locations in single claim (typical IO amplification)
    "multi_location": [
        # List of locations followed by control verb
        r"\b(\w+),\s*(\w+),?\s*(and|und)\s*(\w+)\b.*\b(control|fallen|captured|kontrolliert)\b",
        # Control verb followed by list of locations
        r"\b(controls?|captured|taken|lost)\s+\w+,\s*\w+,?\s*(and|und)\s*\w+",
        # Three locations with commas
        r"\b(kupiansk|pokrovsk|avdiivka|bakhmut|toretsk|siversk)\b.*,.*\b(kupiansk|pokrovsk|avdiivka|bakhmut|toretsk|siversk)\b",
    ],
    # LOW signal: Absolutist framing (IO loves certainty)
    "absolutist": [
        r"\b(completely|fully|totally|entirely)\s+(under\s+control|captured|destroyed)\b",
        r"\b(komplett|vollständig|völlig)\s+(unter\s+kontrolle|eingenommen|zerstört)\b",
        # Absolutist at end of sentence
        r"\b(captured|destroyed|controlled)\s+(completely|fully|totally)\b",
        r"\b\w+\s+(completely|fully|totally|entirely)$",
    ],
    # MEDIUM signal: Victory/defeat framing
    "victory_frame": [
        r"\b(victory|defeat|collapse|surrender|capitulation)\b",
        r"\b(sieg|niederlage|zusammenbruch|kapitulation)\b",
    ],
    # HIGH signal: "The West" / bloc framing - strong propaganda marker
    "bloc_framing": [
        r"\b(the\s+west|western\s+powers|nato\s+forces)\s+(\w+\s+)?(admit|acknowledge|confirm)s?\b",
        r"\b(der\s+westen|westliche\s+mächte)\s+(\w+\s+)?(gibt\s+zu|bestätigt)\b",
        r"\b(western\s+media|mainstream\s+media)\s+(finally|now)\s+(admit|acknowledge)s?\b",
        r"\b(westliche\s+medien)\s+(geben\s+zu|müssen\s+zugeben)\b",
        r"\b(even\s+)?(the\s+west|nato|western\s+experts?)\s+(\w+\s+)?(admit|concede|acknowledge)\b",
    ],
    # HIGH signal: Peace talks pressure narrative
    "peace_pressure": [
        r"\b(peace\s+talks?|negotiations?|ceasefire)\b.*\b(before|until|unless)\b",
        r"\b(friedensverhandlungen?|waffenstillstand)\b.*\b(bevor|bis|wenn\s+nicht)\b",
        r"\b(negotiate\s+now|time\s+is\s+running\s+out)\b",
        r"\b(jetzt\s+verhandeln|die\s+zeit\s+läuft)\b",
    ],
    # MEDIUM signal: Map/territory claims with present tense
    "map_claims": [
        r"\b(map\s+shows?|look\s+at\s+the\s+map)\b",
        r"\b(karte\s+zeigt|schau\s+auf\s+die\s+karte)\b",
    ],
    # MEDIUM signal: Frontline collapse narrative
    "frontline_collapse": [
        r"\b(frontline|front\s*line|defense)\s+(is\s+)?(collapsing|crumbling|breaking)\b",
        r"\b(frontlinie|verteidigung)\s+(bricht|kollabiert|zerbricht)\b",
        r"\b(mass\s+surrender|thousands\s+surrendering)\b",
        r"\b(massenkapitulation|tausende\s+ergeben\s+sich)\b",
    ],
}

# Known IO source patterns (domains/accounts that frequently push IO)
IO_SOURCE_INDICATORS = [
    r"\b(rt\.com|sputnik|tass|ria)\b",
    r"\b(telegram|t\.me)\b.*\b(official|channel)\b",
    r"\b(военкор|z\-blogger)\b",
]

# Volatility by claim type
CLAIM_TYPE_VOLATILITY = {
    ClaimType.FOREIGN_INFLUENCE: ClaimVolatility.HIGH,  # War/geopolitics
    ClaimType.DELEGITIMIZATION_FRAME: ClaimVolatility.MEDIUM,
    ClaimType.HEALTH_MISINFORMATION: ClaimVolatility.LOW,  # Science is stable
    ClaimType.SCIENCE_DENIAL: ClaimVolatility.STABLE,
    ClaimType.CONSPIRACY_THEORY: ClaimVolatility.LOW,
    ClaimType.HATE_OR_DEHUMANIZATION: ClaimVolatility.STABLE,
    ClaimType.THREAT_OR_INCITEMENT: ClaimVolatility.MEDIUM,
}


class ClaimRouter:
    """
    Guardian Claim Router
    Classifies claims into types, assesses risk level, and determines temporal mode.
    TikTok-aware: understands that upload time ≠ claim time.
    """

    def __init__(self):
        self.patterns = {
            ClaimType.HATE_OR_DEHUMANIZATION: HATE_PATTERNS,
            ClaimType.THREAT_OR_INCITEMENT: THREAT_PATTERNS,
            ClaimType.DELEGITIMIZATION_FRAME: DELEGITIMIZATION_PATTERNS,
            ClaimType.BLANKET_GENERALIZATION: GENERALIZATION_PATTERNS,
            ClaimType.HEALTH_MISINFORMATION: HEALTH_MISINFO_PATTERNS,
            ClaimType.CONSPIRACY_THEORY: CONSPIRACY_PATTERNS,
        }
        self.territorial_patterns = TERRITORIAL_PATTERNS
        self.live_patterns = LIVE_SIGNAL_PATTERNS
        self.archive_patterns = ARCHIVE_SIGNAL_PATTERNS
        logger.info("ClaimRouter initialized with %d pattern types + temporal awareness", len(self.patterns))

    def detect_language(self, text: str) -> str:
        """Simple language detection (DE vs EN)."""
        text_lower = text.lower()
        german_markers = [" der ", " die ", " das ", " nicht ", " ist ", " und ", " mit ", " für ", " oder "]
        german_count = sum(1 for marker in german_markers if marker in text_lower)

        if german_count >= 2 or any(c in text_lower for c in "äöüß"):
            return "de"
        return "en"

    def extract_entities(self, text: str) -> List[str]:
        """Extract named entities (simplified)."""
        entities = []

        # Common entity patterns
        entity_patterns = [
            r"\b(EU|UN|NATO|WHO|WEF|IMF|OECD)\b",
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b",  # Multi-word proper nouns
            r"\b(Deutschland|Germany|Ukraine|Russia|USA|China)\b",
            r"\b(Merkel|Scholz|Biden|Trump|Putin|Zelensky)\b",
        ]

        for pattern in entity_patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], str):
                    entities.extend(matches)
                else:
                    entities.extend([m[0] if isinstance(m, tuple) else m for m in matches])

        return list(set(entities))[:10]  # Dedupe and limit

    def extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords for source retrieval."""
        # Remove common stop words and extract significant terms
        stop_words = {
            "de": {"der", "die", "das", "ist", "sind", "hat", "haben", "und", "oder", "aber", "dass", "ein", "eine"},
            "en": {"the", "is", "are", "has", "have", "and", "or", "but", "that", "a", "an", "of", "to", "in"}
        }

        language = self.detect_language(text)
        words = re.findall(r'\b\w{4,}\b', text.lower())  # Words with 4+ chars
        keywords = [w for w in words if w not in stop_words.get(language, set())]

        # Dedupe and return top keywords
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords[:15]

    def classify_claim(self, text: str) -> List[ClaimType]:
        """Classify claim into types (multi-label)."""
        language = self.detect_language(text)
        text_lower = text.lower()
        detected_types: Set[ClaimType] = set()

        for claim_type, patterns in self.patterns.items():
            lang_patterns = patterns.get(language, patterns.get("en", []))
            for pattern in lang_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    detected_types.add(claim_type)
                    break

        return list(detected_types)

    def assess_risk_level(self, claim_types: List[ClaimType]) -> RiskLevel:
        """Assess risk level based on claim types."""
        # Critical types
        critical_types = {ClaimType.THREAT_OR_INCITEMENT}
        high_types = {ClaimType.HATE_OR_DEHUMANIZATION, ClaimType.DELEGITIMIZATION_FRAME}
        medium_types = {
            ClaimType.HEALTH_MISINFORMATION,
            ClaimType.CONSPIRACY_THEORY,
            ClaimType.BLANKET_GENERALIZATION
        }

        claim_type_set = set(claim_types)

        if claim_type_set & critical_types:
            return RiskLevel.CRITICAL
        if claim_type_set & high_types:
            return RiskLevel.HIGH
        if claim_type_set & medium_types:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def should_guardian_respond(self, risk_level: RiskLevel, claim_types: List[ClaimType]) -> bool:
        """Determine if Guardian should respond to this claim."""
        # Always respond to medium+ risk
        if risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL}:
            return True

        # Always respond to certain claim types regardless of risk assessment
        guardian_types = {
            ClaimType.HATE_OR_DEHUMANIZATION,
            ClaimType.THREAT_OR_INCITEMENT,
            ClaimType.DELEGITIMIZATION_FRAME,
            ClaimType.HEALTH_MISINFORMATION,
        }

        return bool(set(claim_types) & guardian_types)

    # =========================================================================
    # TEMPORAL AWARENESS - TikTok-specific (upload time ≠ claim time)
    # =========================================================================

    def detect_territorial_claim(self, text: str) -> bool:
        """
        Detect if claim is about territorial control (VERY HIGH volatility).
        These claims can change hourly during active conflicts.
        """
        text_lower = text.lower()

        # Check for control keywords
        for pattern in self.territorial_patterns["keywords"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Also needs a location reference
                for loc_pattern in self.territorial_patterns["locations"]:
                    if re.search(loc_pattern, text_lower, re.IGNORECASE):
                        logger.info("🎯 Territorial claim detected (VERY_HIGH volatility)")
                        return True
        return False

    def detect_temporal_signals(self, text: str, language: str) -> List[str]:
        """
        Extract temporal signals from claim text.
        These indicate whether the claim refers to "now" or established facts.
        """
        text_lower = text.lower()
        signals = []

        # Check live signals
        live_patterns = self.live_patterns.get(language, self.live_patterns["en"])
        for pattern in live_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                signals.append(f"LIVE:{match.group()}")

        # Check archive signals
        archive_patterns = self.archive_patterns.get(language, self.archive_patterns["en"])
        for pattern in archive_patterns:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                signals.append(f"ARCHIVE:{match.group()}")

        return signals

    def determine_volatility(self, text: str, claim_types: List[ClaimType]) -> ClaimVolatility:
        """
        Determine claim volatility - how quickly facts can change.
        """
        # Territorial claims are always VERY_HIGH
        if self.detect_territorial_claim(text):
            return ClaimVolatility.VERY_HIGH

        # Check claim type volatility
        for ct in claim_types:
            if ct in CLAIM_TYPE_VOLATILITY:
                type_vol = CLAIM_TYPE_VOLATILITY[ct]
                if type_vol == ClaimVolatility.VERY_HIGH:
                    return ClaimVolatility.VERY_HIGH
                if type_vol == ClaimVolatility.HIGH:
                    return ClaimVolatility.HIGH

        # Default based on primary claim type
        if claim_types:
            return CLAIM_TYPE_VOLATILITY.get(claim_types[0], ClaimVolatility.MEDIUM)

        return ClaimVolatility.MEDIUM

    def determine_temporal_mode(
        self,
        text: str,
        volatility: ClaimVolatility,
        temporal_signals: List[str]
    ) -> TemporalMode:
        """
        Route decision: LIVE_REQUIRED vs ARCHIVE_OK.

        Logic:
        - VERY_HIGH/HIGH volatility + any LIVE signal → LIVE_REQUIRED
        - VERY_HIGH volatility (even without signals) → LIVE_REQUIRED
        - Only ARCHIVE signals + LOW/STABLE volatility → ARCHIVE_OK
        - Mixed or unclear → AMBIGUOUS
        """
        live_count = sum(1 for s in temporal_signals if s.startswith("LIVE:"))
        archive_count = sum(1 for s in temporal_signals if s.startswith("ARCHIVE:"))

        # VERY_HIGH volatility = always LIVE
        if volatility == ClaimVolatility.VERY_HIGH:
            logger.info("⚡ LIVE_REQUIRED: Very high volatility claim")
            return TemporalMode.LIVE_REQUIRED

        # HIGH volatility + any live signal = LIVE
        if volatility == ClaimVolatility.HIGH and live_count > 0:
            logger.info("⚡ LIVE_REQUIRED: High volatility + live signals")
            return TemporalMode.LIVE_REQUIRED

        # Strong archive signals + low volatility = ARCHIVE OK
        if archive_count > 0 and live_count == 0:
            if volatility in [ClaimVolatility.LOW, ClaimVolatility.STABLE]:
                logger.info("📚 ARCHIVE_OK: Low volatility + archive signals")
                return TemporalMode.ARCHIVE_OK

        # Mixed signals or medium volatility = AMBIGUOUS
        if live_count > 0 and archive_count > 0:
            logger.info("❓ AMBIGUOUS: Mixed temporal signals")
            return TemporalMode.AMBIGUOUS

        # Default: HIGH volatility without signals = LIVE, otherwise ARCHIVE
        if volatility == ClaimVolatility.HIGH:
            return TemporalMode.LIVE_REQUIRED

        return TemporalMode.ARCHIVE_OK

    # =========================================================================
    # INFORMATION OPERATION (IO) DETECTION - WEIGHTED SCORING
    # =========================================================================

    def detect_io_patterns(self, text: str) -> Tuple[float, List[str], bool]:
        """
        Detect if claim shows Information Operation patterns.
        Returns (io_score, list of indicators found, is_io_threshold_met).

        WEIGHTED scoring instead of simple count:
        - HIGH signal (0.35-0.5): bloc_framing, peace_pressure, known_source
        - MEDIUM signal (0.15-0.25): victory_frame, frontline_collapse, map_claims
        - LOW signal (0.05-0.15): multi_location, absolutist

        IO claims need different response framing:
        - Not just "this is false" but "this is part of a campaign"
        - Acknowledge the narrative, not just the facts
        """
        text_lower = text.lower()
        indicators = []
        io_score = 0.0

        # Check each IO pattern category and sum weighted scores
        for category, patterns in IO_INDICATOR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    indicators.append(f"IO:{category}")
                    weight = IO_SIGNAL_WEIGHTS.get(category, 0.10)
                    io_score += weight
                    logger.debug(f"IO indicator: {category} (weight={weight})")
                    break  # One match per category is enough

        # Check for known IO source patterns (HIGH signal)
        for pattern in IO_SOURCE_INDICATORS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                indicators.append("IO:known_source")
                io_score += IO_SIGNAL_WEIGHTS.get("known_source", 0.40)
                break

        # Special case: territorial + multi-location = strong IO signal
        if self.detect_territorial_claim(text):
            if any("multi_location" in ind for ind in indicators):
                if "IO:territorial_multi" not in indicators:
                    indicators.append("IO:territorial_multi")
                    io_score += IO_SIGNAL_WEIGHTS.get("territorial_multi", 0.35)

        # Cap score at 1.0
        io_score = min(1.0, io_score)

        # Threshold check
        is_io = io_score >= IO_THRESHOLD

        if is_io:
            logger.info(f"🎯 IO pattern detected (score={io_score:.2f}): {indicators}")
        elif io_score > 0:
            logger.debug(f"IO indicators below threshold (score={io_score:.2f}): {indicators}")

        return io_score, indicators, is_io

    def apply_external_io_boost(
        self,
        base_io_score: float,
        base_indicators: List[str],
        freshness_data: Optional[Dict] = None,
    ) -> Tuple[float, List[str], bool]:
        """
        Apply external IO boost from RSS freshness service.

        When a whitelist source (like ERR) explicitly names an IO campaign
        in their coverage, that's a strong signal to boost IO score.

        Args:
            base_io_score: IO score from detect_io_patterns()
            base_indicators: Indicators from detect_io_patterns()
            freshness_data: Output from rss_freshness.check_territorial_freshness()

        Returns:
            Updated (io_score, indicators, is_io_threshold_met)
        """
        if not freshness_data:
            return base_io_score, base_indicators, base_io_score >= IO_THRESHOLD

        io_score = base_io_score
        indicators = base_indicators.copy()

        # Check if whitelist source named IO frame
        if freshness_data.get("has_io_frame_named", False):
            io_boost = freshness_data.get("io_boost", IO_SIGNAL_WEIGHTS.get("whitelist_names_io", 0.30))
            io_score += io_boost
            indicators.append("IO:whitelist_names_io")
            logger.info(f"📰 IO boost from whitelist source: +{io_boost:.2f}")

        # Fresh coverage can also provide evidence boost (for routing)
        if freshness_data.get("has_fresh_coverage", False):
            # This doesn't affect IO score, but is useful metadata
            indicators.append(f"FRESH:{freshness_data.get('article_count', 0)}_articles")

        # Cap and threshold
        io_score = min(1.0, io_score)
        is_io = io_score >= IO_THRESHOLD

        if is_io and "IO:whitelist_names_io" in indicators:
            logger.info(f"🎯 IO confirmed by whitelist source (score={io_score:.2f})")

        return io_score, indicators, is_io

    def assess_evidence_quality(
        self,
        claim_types: List[ClaimType],
        volatility: ClaimVolatility,
        is_territorial: bool,
        temporal_mode: TemporalMode,
    ) -> Tuple[EvidenceQuality, List[str]]:
        """
        Assess how strong the available counter-evidence is likely to be.

        This is a HEURISTIC assessment before source retrieval:
        - STRONG: Stable facts, well-documented claims, institutional sources available
        - MEDIUM: Some evidence available but situation is evolving
        - WEAK: Highly volatile, limited verifiable sources, must hedge

        Returns (evidence_quality, reasons)
        """
        reasons = []

        # === WEAK evidence indicators ===
        # Very high volatility = evidence likely outdated quickly
        if volatility == ClaimVolatility.VERY_HIGH:
            reasons.append("WEAK: Very high volatility (hourly changes)")
            return EvidenceQuality.WEAK, reasons

        # Territorial claims in LIVE mode = facts changing too fast
        if is_territorial and temporal_mode == TemporalMode.LIVE_REQUIRED:
            reasons.append("WEAK: Territorial claim requiring live verification")
            return EvidenceQuality.WEAK, reasons

        # Ambiguous temporal = can't be sure which timeframe claim refers to
        if temporal_mode == TemporalMode.AMBIGUOUS:
            reasons.append("WEAK: Ambiguous temporal reference")
            return EvidenceQuality.WEAK, reasons

        # === STRONG evidence indicators ===
        # Science denial = well-documented, stable evidence
        if ClaimType.SCIENCE_DENIAL in claim_types:
            reasons.append("STRONG: Science denial - well-documented consensus")
            return EvidenceQuality.STRONG, reasons

        # Health misinformation = institutional sources (WHO, CDC)
        if ClaimType.HEALTH_MISINFORMATION in claim_types:
            reasons.append("STRONG: Health claim - institutional sources available")
            return EvidenceQuality.STRONG, reasons

        # Conspiracy theories = well-debunked, stable patterns
        if ClaimType.CONSPIRACY_THEORY in claim_types:
            reasons.append("STRONG: Conspiracy theory - well-documented debunks")
            return EvidenceQuality.STRONG, reasons

        # Stable volatility = facts don't change
        if volatility == ClaimVolatility.STABLE:
            reasons.append("STRONG: Stable factual basis")
            return EvidenceQuality.STRONG, reasons

        # Low volatility + archive OK = good evidence likely
        if volatility == ClaimVolatility.LOW and temporal_mode == TemporalMode.ARCHIVE_OK:
            reasons.append("STRONG: Low volatility, archive sources acceptable")
            return EvidenceQuality.STRONG, reasons

        # === MEDIUM evidence (default) ===
        # High volatility but not territorial = medium confidence
        if volatility == ClaimVolatility.HIGH:
            reasons.append("MEDIUM: High volatility but not territorial")
            return EvidenceQuality.MEDIUM, reasons

        # Foreign influence = some IO patterns documented
        if ClaimType.FOREIGN_INFLUENCE in claim_types:
            reasons.append("MEDIUM: Foreign influence - some patterns documented")
            return EvidenceQuality.MEDIUM, reasons

        # Delegitimization = context-dependent
        if ClaimType.DELEGITIMIZATION_FRAME in claim_types:
            reasons.append("MEDIUM: Delegitimization frame - context-dependent")
            return EvidenceQuality.MEDIUM, reasons

        # Default: MEDIUM
        reasons.append("MEDIUM: Standard claim, moderate evidence expected")
        return EvidenceQuality.MEDIUM, reasons

    def determine_response_mode(
        self,
        io_score: float,
        is_io: bool,
        is_territorial: bool,
        volatility: ClaimVolatility,
        temporal_mode: TemporalMode,
        evidence_quality: EvidenceQuality,
    ) -> ResponseModeResult:
        """
        Determine how Guardian should frame the response.

        PROPER ROUTING MATRIX (user's specification):
        1. Gate 1: TEMPORAL (highest priority)
           - If LIVE_REQUIRED: proceed to evidence gate
        2. Gate 2: EVIDENCE QUALITY
           - If evidence WEAK → CAUTIOUS (can't make strong claims)
           - If evidence MEDIUM/STRONG → proceed to IO gate
        3. Gate 3: IO OVERLAY (not replacement!)
           - IO is SECONDARY mode, not primary for frontline claims
           - LIVE_SITUATION + IO_CONTEXT = combined response

        Priority: CAUTIOUS > LIVE_SITUATION > IO_CONTEXT > DEBUNK
        """
        reasons = []

        # =================================================================
        # GATE 1: TEMPORAL MODE (highest priority)
        # =================================================================
        if temporal_mode == TemporalMode.LIVE_REQUIRED or volatility == ClaimVolatility.VERY_HIGH:
            reasons.append("Gate1: LIVE_REQUIRED or VERY_HIGH volatility")

            # =================================================================
            # GATE 2: EVIDENCE QUALITY (for live situations)
            # =================================================================
            if evidence_quality == EvidenceQuality.WEAK:
                # Weak evidence + live = CAUTIOUS (can't make claims)
                reasons.append("Gate2: WEAK evidence → CAUTIOUS")
                logger.info("❓ Response mode: CAUTIOUS (live + weak evidence)")
                return ResponseModeResult(
                    primary=ResponseMode.CAUTIOUS,
                    secondary=ResponseMode.IO_CONTEXT if is_io else None,
                    io_score=io_score,
                    evidence_quality=evidence_quality,
                    mode_reason=" | ".join(reasons),
                )

            # MEDIUM/STRONG evidence + live = LIVE_SITUATION
            reasons.append(f"Gate2: {evidence_quality.value} evidence → LIVE_SITUATION")

            # =================================================================
            # GATE 3: IO OVERLAY (secondary, not replacement!)
            # =================================================================
            if is_io:
                # LIVE_SITUATION + IO_CONTEXT combined
                reasons.append(f"Gate3: IO overlay (score={io_score:.2f})")
                logger.info(f"⚡📢 Response mode: LIVE_SITUATION + IO_CONTEXT (score={io_score:.2f})")
                return ResponseModeResult(
                    primary=ResponseMode.LIVE_SITUATION,
                    secondary=ResponseMode.IO_CONTEXT,
                    io_score=io_score,
                    evidence_quality=evidence_quality,
                    mode_reason=" | ".join(reasons),
                )

            # Just LIVE_SITUATION, no IO
            logger.info("⚡ Response mode: LIVE_SITUATION")
            return ResponseModeResult(
                primary=ResponseMode.LIVE_SITUATION,
                secondary=None,
                io_score=io_score,
                evidence_quality=evidence_quality,
                mode_reason=" | ".join(reasons),
            )

        # =================================================================
        # NON-LIVE PATH: Check ambiguous first
        # =================================================================
        if temporal_mode == TemporalMode.AMBIGUOUS:
            reasons.append("Gate1: AMBIGUOUS temporal → CAUTIOUS")
            logger.info("❓ Response mode: CAUTIOUS (ambiguous temporal)")
            return ResponseModeResult(
                primary=ResponseMode.CAUTIOUS,
                secondary=ResponseMode.IO_CONTEXT if is_io else None,
                io_score=io_score,
                evidence_quality=evidence_quality,
                mode_reason=" | ".join(reasons),
            )

        # =================================================================
        # ARCHIVE_OK PATH: Standard fact-checking
        # =================================================================
        reasons.append("Gate1: ARCHIVE_OK → standard path")

        # If IO detected in non-live context, IO_CONTEXT is primary
        if is_io:
            reasons.append(f"IO pattern detected (score={io_score:.2f}) → IO_CONTEXT primary")
            logger.info(f"📢 Response mode: IO_CONTEXT (score={io_score:.2f})")
            return ResponseModeResult(
                primary=ResponseMode.IO_CONTEXT,
                secondary=None,
                io_score=io_score,
                evidence_quality=evidence_quality,
                mode_reason=" | ".join(reasons),
            )

        # Default: DEBUNK
        reasons.append("Default → DEBUNK")
        logger.info("✅ Response mode: DEBUNK")
        return ResponseModeResult(
            primary=ResponseMode.DEBUNK,
            secondary=None,
            io_score=io_score,
            evidence_quality=evidence_quality,
            mode_reason=" | ".join(reasons),
        )

    def analyze_claim(self, claim_text: str, claim_id: Optional[str] = None) -> ClaimAnalysis:
        """
        Full claim analysis pipeline with TikTok temporal awareness.

        Returns:
            ClaimAnalysis with type classification, risk level, keywords,
            volatility, and temporal mode for proper TikTok response handling.

        Routing Matrix:
            1. Gate 1: TEMPORAL (LIVE_REQUIRED / ARCHIVE_OK / AMBIGUOUS)
            2. Gate 2: EVIDENCE QUALITY (STRONG / MEDIUM / WEAK)
            3. Gate 3: IO OVERLAY (secondary mode, not replacement)
        """
        import uuid

        claim_id = claim_id or str(uuid.uuid4())
        language = self.detect_language(claim_text)

        # Normalize claim
        normalized = claim_text.strip()
        if len(normalized) > 1000:
            normalized = normalized[:1000] + "..."

        # Classify
        claim_types = self.classify_claim(claim_text)
        risk_level = self.assess_risk_level(claim_types)
        requires_guardian = self.should_guardian_respond(risk_level, claim_types)

        # Extract entities and keywords
        entities = self.extract_entities(claim_text)
        keywords = self.extract_keywords(claim_text)

        # === TEMPORAL AWARENESS (TikTok-specific) ===
        is_territorial = self.detect_territorial_claim(claim_text)
        temporal_signals = self.detect_temporal_signals(claim_text, language)
        volatility = self.determine_volatility(claim_text, claim_types)
        temporal_mode = self.determine_temporal_mode(claim_text, volatility, temporal_signals)

        # Volatility reason for auditability
        volatility_reason = ""
        if is_territorial:
            volatility_reason = "Territorial control claim"
        elif volatility == ClaimVolatility.VERY_HIGH:
            volatility_reason = "Very high volatility (hourly changes)"
        elif volatility == ClaimVolatility.HIGH:
            volatility_reason = "High volatility (daily changes)"
        elif volatility == ClaimVolatility.STABLE:
            volatility_reason = "Stable factual basis"

        # === IO (Information Operation) DETECTION - WEIGHTED ===
        io_score, io_indicators, is_io_pattern = self.detect_io_patterns(claim_text)

        # === EVIDENCE QUALITY ASSESSMENT ===
        evidence_quality, evidence_reasons = self.assess_evidence_quality(
            claim_types, volatility, is_territorial, temporal_mode
        )

        # === RESPONSE MODE (with proper routing matrix) ===
        response_mode_result = self.determine_response_mode(
            io_score=io_score,
            is_io=is_io_pattern,
            is_territorial=is_territorial,
            volatility=volatility,
            temporal_mode=temporal_mode,
            evidence_quality=evidence_quality,
        )
        # Populate evidence reasons in result
        response_mode_result.evidence_reasons = evidence_reasons

        # Legacy field for backwards compatibility
        response_mode = response_mode_result.primary

        # Calculate confidence based on pattern matches
        confidence = min(0.95, 0.5 + len(claim_types) * 0.15)

        # Generate brief reasoning (include temporal + IO + evidence info)
        if claim_types:
            type_names = [ct.value.replace("_", " ") for ct in claim_types]
            reasoning = f"Detected: {', '.join(type_names)}. Risk: {risk_level.value}."
            if is_io_pattern:
                reasoning += f" 📢 IO pattern (score={io_score:.2f})."
            if response_mode_result.secondary:
                reasoning += f" Mode: {response_mode_result.primary.value}+{response_mode_result.secondary.value}."
            elif temporal_mode == TemporalMode.LIVE_REQUIRED:
                reasoning += " ⚡ LIVE check required."
            if evidence_quality == EvidenceQuality.WEAK:
                reasoning += " ⚠️ Weak evidence - hedge language required."
            if is_territorial:
                reasoning += " 🎯 Territorial claim."
        else:
            reasoning = "No specific harmful patterns detected. Standard fact-check recommended."

        logger.info(
            "Analyzed claim %s: types=%s, risk=%s, volatility=%s, "
            "response_mode=%s (secondary=%s), io_score=%.2f, evidence=%s",
            claim_id[:8], claim_types, risk_level, volatility,
            response_mode_result.primary, response_mode_result.secondary,
            io_score, evidence_quality
        )

        return ClaimAnalysis(
            claim_id=claim_id,
            normalized_claim=normalized,
            language=language,
            claim_types=claim_types,
            risk_level=risk_level,
            confidence=confidence,
            reasoning_brief=reasoning,
            entities=entities,
            keywords=keywords,
            requires_guardian=requires_guardian,
            # TikTok temporal fields
            volatility=volatility,
            volatility_reason=volatility_reason,
            temporal_mode=temporal_mode,
            temporal_signals=temporal_signals,
            is_territorial=is_territorial,
            # IO awareness - WEIGHTED scoring
            io_score=io_score,
            io_indicators=io_indicators,
            is_io_pattern=is_io_pattern,
            # Response mode (primary + secondary)
            response_mode_result=response_mode_result,
            response_mode=response_mode,  # Legacy backwards compatibility
        )


# Extended claim types for policy/geopolitical claims
class PolicyClaimRouter(ClaimRouter):
    """Extended router for policy and geopolitical claims."""

    def __init__(self):
        super().__init__()

        # Add policy-specific patterns
        self.patterns[ClaimType.POLICY_AID_OVERSIGHT] = {
            "de": [
                r"\b(hilfe|unterstützung|geld)\b.*\b(verschwendet|gestohlen|korrupt)\b",
                r"\b(kontrolle|aufsicht|transparenz)\b.*\b(fehlt|mangelt|keine)\b",
                r"\b(milliarden?|millionen?)\b.*\b(verschwunden|weg|unklar)\b",
            ],
            "en": [
                r"\b(aid|support|money)\b.*\b(wasted|stolen|corrupt)\b",
                r"\b(oversight|control|transparency)\b.*\b(lacking|missing|none)\b",
                r"\b(billion|million)\b.*\b(disappeared|gone|unclear)\b",
            ]
        }

        self.patterns[ClaimType.FOREIGN_INFLUENCE] = {
            "de": [
                r"\b(russland|china|iran)\b.*\b(kontrolliert|steuert|beeinflusst)\b",
                r"\b(propaganda|desinformation|fake\s*news)\b.*\b(kampagne|operation)\b",
                r"\b(trollfabrik|bot|koordiniert)\b",
            ],
            "en": [
                r"\b(russia|china|iran)\b.*\b(controls|runs|influences)\b",
                r"\b(propaganda|disinformation|fake\s*news)\b.*\b(campaign|operation)\b",
                r"\b(troll\s*farm|bot|coordinated)\b",
            ]
        }
