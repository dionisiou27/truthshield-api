"""
Guardian Claim Router v1
Multi-label classification for claim typing and risk assessment.
"""
from enum import Enum
from typing import List, Dict, Optional, Set
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
        r"\b(impf|vakzin|mrna)\b.*\b(gift|tödlich|unfruchtbar|chip)\b",
        r"\b(corona|covid)\b.*\b(lüge|fake|erfunden|plandemie)\b",
        r"\b(5g)\b.*\b(krank|krebs|corona|strahlung)\b",
        r"\b(heilung|heilt|kur)\b.*\b(krebs|diabetes|aids)\b",
    ],
    "en": [
        r"\b(vaccine|vax|mrna)\b.*\b(poison|deadly|infertile|chip|magnetic)\b",
        r"\b(corona|covid)\b.*\b(hoax|fake|invented|plandemic)\b",
        r"\b(5g)\b.*\b(sick|cancer|corona|radiation)\b",
        r"\b(cure|cures|heals)\b.*\b(cancer|diabetes|aids)\b",
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


class ClaimRouter:
    """
    Guardian Claim Router
    Classifies claims into types and assesses risk level.
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
        logger.info("ClaimRouter initialized with %d pattern types", len(self.patterns))

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

    def analyze_claim(self, claim_text: str, claim_id: Optional[str] = None) -> ClaimAnalysis:
        """
        Full claim analysis pipeline.

        Returns:
            ClaimAnalysis with type classification, risk level, and keywords
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

        # Calculate confidence based on pattern matches
        confidence = min(0.95, 0.5 + len(claim_types) * 0.15)

        # Generate brief reasoning
        if claim_types:
            type_names = [ct.value.replace("_", " ") for ct in claim_types]
            reasoning = f"Detected: {', '.join(type_names)}. Risk: {risk_level.value}."
        else:
            reasoning = "No specific harmful patterns detected. Standard fact-check recommended."

        logger.info(
            "Analyzed claim %s: types=%s, risk=%s, guardian=%s",
            claim_id[:8], claim_types, risk_level, requires_guardian
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
            requires_guardian=requires_guardian
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
