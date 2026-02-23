"""
Response generation for Guardian Avatar and brand personas.
Extracted from ai_engine.py (P3.7).
"""
import asyncio
import logging
from typing import Dict, List, Optional

from pydantic import BaseModel

from src.ml.guardian.claim_router import (
    ClaimRouter, ClaimAnalysis, ClaimType, RiskLevel,
    ClaimVolatility, TemporalMode, ResponseMode,
    ResponseModeResult, EvidenceQuality,
)
from src.ml.learning.bandit import (
    GuardianBandit, BanditContext, ToneVariant, SourceMixStrategy,
)
from src.core.prompt_builder import (
    get_tone_instructions, get_opening_style,
    get_temporal_instructions, get_response_mode_instructions,
)
from src.core.source_aggregation import Source

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AVATAR_COMPANIES = {
    "GuardianAvatar", "PolicyAvatar", "MemeAvatar",
    "EuroShieldAvatar", "ScienceAvatar",
}

# Global TikTok Output Rules - applies to ALL avatars
TIKTOK_OUTPUT_RULES = {
    "platform": "TikTok",
    "output_length": {
        "sentences": "4-5",
        "max_chars": 450,
    },
    "sources": {
        "required": 3,
        "format": "Quellen: A | B | C",  # or "Sources: A | B | C" for EN
    },
    "learning_mode": "dynamic",
    "optimization_targets": [
        "top_comment_probability",
        "reply_quality",
        "like_reply_ratio",
        "share_proxy",
    ],
    "tone_adaptation": "ML-driven (reinforcement from performance metrics)",
    "no_static_templates": True,
}

# Domain-to-label mapping for authoritative source names
DOMAIN_TO_LABEL: Dict[str, str] = {
    # Primary Health Authorities
    "who.int": "WHO",
    "ema.europa.eu": "EMA",
    "rki.de": "RKI",
    "cdc.gov": "CDC",
    "fda.gov": "FDA",
    "nih.gov": "NIH",
    "pubmed.ncbi.nlm.nih.gov": "PubMed",
    "ncbi.nlm.nih.gov": "PubMed",
    # EU / UN Institutions
    "ec.europa.eu": "EU-Kommission",
    "europa.eu": "EU",
    "fra.europa.eu": "EU Grundrechteagentur",
    "ohchr.org": "UN Menschenrechte",
    "un.org": "UN",
    "eeas.europa.eu": "EU Außendienst",
    # Science & Climate
    "ipcc.ch": "IPCC",
    "nasa.gov": "NASA",
    "nature.com": "Nature",
    "science.org": "Science",
    # Fact-Checkers
    "correctiv.org": "Correctiv",
    "faktenfinder.tagesschau.de": "ARD Faktenfinder",
    "afp.com": "AFP",
    "factcheck.afp.com": "AFP Faktenfinder",
    "dpa.com": "dpa",
    "reuters.com": "Reuters",
    "snopes.com": "Snopes",
    "politifact.com": "PolitiFact",
    "fullfact.org": "Full Fact",
    # Media
    "bpb.de": "bpb",
    "tagesschau.de": "Tagesschau",
    "dw.com": "Deutsche Welle",
    "zeit.de": "Zeit",
    "spiegel.de": "Spiegel",
    "sueddeutsche.de": "SZ",
    # NGOs
    "amnesty.org": "Amnesty",
    "hrw.org": "Human Rights Watch",
    "transparency.org": "Transparency Int.",
    "reporter-ohne-grenzen.de": "Reporter ohne Grenzen",
}

PRIMARY_AUTHORITIES_BY_TYPE: Dict[str, List[str]] = {
    "health_misinformation": ["WHO", "EMA", "RKI", "CDC", "FDA", "PubMed", "NIH"],
    "science_denial": ["IPCC", "Nature", "NASA", "PubMed", "Science"],
    "conspiracy_theory": ["EU", "Reuters", "AFP", "Correctiv", "bpb"],
    "hate_or_dehumanization": [
        "EU Grundrechteagentur", "UN Menschenrechte", "Amnesty", "bpb",
    ],
    "foreign_influence": ["EU Außendienst", "EU", "Reuters", "AFP"],
    "delegitimization_frame": ["EU-Kommission", "Transparency Int.", "Reuters"],
    "economic_misinformation": ["EU-Kommission", "Reuters", "Zeit"],
}

DEFAULTS_BY_TYPE: Dict[str, List[str]] = {
    "health_misinformation": ["WHO", "EMA", "RKI"],
    "science_denial": ["IPCC", "NASA", "Nature"],
    "hate_or_dehumanization": [
        "EU Grundrechteagentur", "UN Menschenrechte", "bpb",
    ],
    "conspiracy_theory": ["Correctiv", "AFP Faktenfinder", "Reuters"],
}


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

class AIInfluencerResponse(BaseModel):
    """AI-generated brand influencer response."""

    response_text: str
    tone: str
    engagement_score: float
    hashtags: List[str]
    company_voice: str
    bot_name: Optional[str] = None
    bot_type: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper: resolve source labels for the Guardian footer
# ---------------------------------------------------------------------------

def _resolve_source_labels(
    sources: List[Source],
    claim_type_str: str,
) -> List[str]:
    """Build deduplicated, authority-prioritised source labels (max 3)."""

    preferred_authorities = PRIMARY_AUTHORITIES_BY_TYPE.get(claim_type_str, [])
    source_labels: List[str] = []
    seen_labels: set = set()

    # First pass: find preferred authorities
    for src in sources:
        if len(source_labels) >= 3:
            break
        url = src.url.lower()
        domain = None
        for d in DOMAIN_TO_LABEL:
            if d in url:
                domain = d
                break
        if domain:
            label = DOMAIN_TO_LABEL[domain]
            if label in preferred_authorities and label not in seen_labels:
                source_labels.insert(0, label)
                seen_labels.add(label)

    # Second pass: fill remaining slots
    for src in sources:
        if len(source_labels) >= 3:
            break
        url = src.url.lower()
        domain = None
        for d in DOMAIN_TO_LABEL:
            if d in url:
                domain = d
                break
        if domain:
            label = DOMAIN_TO_LABEL[domain]
            if label not in seen_labels:
                source_labels.append(label)
                seen_labels.add(label)
        else:
            name = src.title.split(" - ")[0].split(" | ")[0][:20]
            if name and name not in seen_labels:
                source_labels.append(name)
                seen_labels.add(name)

    # Default fallbacks based on claim type
    defaults = DEFAULTS_BY_TYPE.get(
        claim_type_str, ["EU", "Reuters", "bpb"]
    )
    for default in defaults:
        if len(source_labels) >= 3:
            break
        if default not in seen_labels:
            source_labels.append(default)
            seen_labels.add(default)

    return source_labels[:3]


# ---------------------------------------------------------------------------
# Helper: build sources context snippet for the LLM prompt
# ---------------------------------------------------------------------------

def _build_sources_text(sources: List[Source]) -> str:
    """Return a formatted sources block for inclusion in the LLM prompt."""

    if not sources:
        return ""

    top_sources = sources[:3]
    lines = []
    for i, src in enumerate(top_sources, 1):
        snippet = (
            src.snippet[:150] + "..." if len(src.snippet) > 150 else src.snippet
        )
        lines.append(
            f"{i}. {src.title}\n   URL: {src.url}\n   Info: {snippet}"
        )

    return (
        "\n\nVERIFIED SOURCES (use these facts in your response):\n"
        + "\n".join(lines)
        + "\n"
    )


# ---------------------------------------------------------------------------
# ResponseBuilder
# ---------------------------------------------------------------------------

class ResponseBuilder:
    """Builds LLM-powered responses for Guardian Avatar and brand personas.

    Extracted from ``TruthShieldAI._generate_single_response`` so that
    response generation can be tested and evolved independently of the main
    fact-checking pipeline.
    """

    def __init__(
        self,
        openai_client,
        claim_router: ClaimRouter,
        bandit: GuardianBandit,
        company_personas: Dict,
    ):
        self.openai_client = openai_client
        self.claim_router = claim_router
        self.bandit = bandit
        self.company_personas = company_personas
        self.last_claim_analysis: Optional[ClaimAnalysis] = None
        self.last_tone_variant: Optional[ToneVariant] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_brand_response(
        self,
        claim: str,
        fact_check,
        company: str = "BMW",
        language: str = "en",
    ) -> Dict[str, "AIInfluencerResponse"]:
        """Generate company-branded response in both languages."""

        responses = {}

        # Generate English response
        responses['en'] = await self.generate_single_response(claim, fact_check, company, "en")

        # Generate German response
        responses['de'] = await self.generate_single_response(claim, fact_check, company, "de")

        # Add Guardian Avatar metadata if applicable
        if company == "GuardianAvatar":
            for lang in responses:
                responses[lang].bot_name = "Guardian Avatar 🛡️"
                responses[lang].bot_type = "universal_avatar"

        return responses

    async def generate_single_response(
        self,
        claim: str,
        fact_check,
        company: str,
        language: str,
    ) -> AIInfluencerResponse:
        """Generate a single-language response for *company*.

        Parameters
        ----------
        claim:
            The raw claim text being fact-checked.
        fact_check:
            A ``FactCheckResult`` (or compatible object) with ``is_fake``,
            ``confidence``, ``category``, ``explanation``, and ``sources``.
        company:
            Company / avatar identifier (e.g. ``"GuardianAvatar"``).
        language:
            ``"en"`` or ``"de"``.
        """

        if not self.openai_client:
            return self._fallback_response(company, language)

        try:
            persona = self.company_personas.get(
                company, self.company_personas.get("BMW", {})
            )

            if company in AVATAR_COMPANIES:
                prompt = self._build_avatar_prompt(
                    claim, fact_check, company, language, persona,
                )
            else:
                prompt = self._build_brand_prompt(
                    claim, fact_check, company, language, persona,
                )

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
            )

            response_text = response.choices[0].message.content

            hashtags = (
                ["#TruthShield", "#FactCheck", f"#{company}"]
                if company in AVATAR_COMPANIES
                else [f"#{company}Facts", "#TruthShield"]
            )

            return AIInfluencerResponse(
                response_text=response_text,
                tone=persona.get("tone", "professional"),
                engagement_score=0.85,
                hashtags=hashtags,
                company_voice=company,
            )

        except Exception as e:
            logger.error(f"Brand response generation failed: {e}")
            return self._error_fallback(company, language)

    # ------------------------------------------------------------------
    # Prompt builders (private)
    # ------------------------------------------------------------------

    def _build_avatar_prompt(
        self,
        claim: str,
        fact_check,
        company: str,
        language: str,
        persona: Dict,
    ) -> str:
        """Build prompt for any avatar persona (Guardian, Meme, Policy, ...)."""

        # --- TikTok rules block ---
        sources_format = (
            "Sources: A | B | C" if language == "en" else "Quellen: A | B | C"
        )
        tiktok_rules = (
            f"\nGLOBAL TIKTOK PLATFORM RULES (MUST FOLLOW):\n"
            f"- Output length: 4-5 sentences, MAX "
            f"{TIKTOK_OUTPUT_RULES['output_length']['max_chars']} characters\n"
            f'- Sources: Include exactly 3 sources at the end in format: '
            f'"{sources_format}"\n'
            f"- NO static templates - generate dynamic, unique responses\n"
            f"- Optimize for: engagement, reply quality, shareability\n"
            f"- Tone: Adapt dynamically based on claim severity\n"
        )

        # --- Humor / style per avatar type ---
        if company == "MemeAvatar":
            lang_instructions = {
                "en": "Create a maximum humor Reddit-style response that",
                "de": "Erstelle eine maximale Humor Reddit-Style Antwort, die",
            }
            humor_level = "MAXIMUM HUMOR - Reddit-style, sarcastic, meme-savvy"
        elif company == "GuardianAvatar":
            lang_instructions = {
                "en": (
                    "Create an authoritative boundary-setting response "
                    "with exactly 5 sentences that"
                ),
                "de": (
                    "Erstelle eine autoritative Grenzziehungs-Antwort "
                    "mit genau 5 Sätzen, die"
                ),
            }
            humor_level = (
                "NO HUMOR - Authoritative, de-escalation, boundary enforcement"
            )
        elif company in {"PolicyAvatar", "EuroShieldAvatar", "ScienceAvatar"}:
            lang_instructions = {
                "en": "Create a serious, evidence-based response that",
                "de": "Erstelle eine ernste, evidenzbasierte Antwort, die",
            }
            humor_level = "SERIOUS - Evidence-based, authoritative, professional"
        else:
            lang_instructions = {
                "en": "Create a factual response that",
                "de": "Erstelle eine faktische Antwort, die",
            }
            humor_level = "PROFESSIONAL - Factual and clear"

        language_directive = (
            "Antwort ausschließlich auf Deutsch."
            if language == "de"
            else "Respond only in English."
        )

        sources_text = _build_sources_text(
            fact_check.sources if fact_check.sources else []
        )

        # --- Guardian Avatar: full ML pipeline ---
        if company == "GuardianAvatar":
            return self._build_guardian_prompt(
                claim, fact_check, language, tiktok_rules,
                sources_text, language_directive,
            )

        # --- All other avatars ---
        source_names: List[str] = []
        if fact_check.sources:
            for src in fact_check.sources[:3]:
                name = src.title.split(" - ")[0].split(" | ")[0][:25]
                if name and name not in source_names:
                    source_names.append(name)
        while len(source_names) < 3:
            source_names.append(
                "EU" if len(source_names) == 0
                else "Reuters" if len(source_names) == 1
                else "bpb"
            )
        sources_line = " | ".join(source_names)
        sources_suffix = (
            f"Sources: {sources_line}" if language == "en"
            else f"Quellen: {sources_line}"
        )

        return f"""
You are {company} {persona.get('emoji', '')}, {persona.get('style', '')} for TikTok.
{tiktok_rules}

Voice: {persona.get('voice', '')}
Tone: {persona.get('tone', '')}
Humor Level: {humor_level}

A claim is circulating:
"{claim}"

Fact-check result:
- Is fake: {fact_check.is_fake}
- Confidence: {fact_check.confidence}
- Category: {fact_check.category}
- Explanation: {fact_check.explanation}
{sources_text}

{lang_instructions.get(language, lang_instructions['en'])}:
1. Matches your persona's humor level and style
2. Is engaging and appropriate for your TikTok audience
3. References specific facts from the verified sources above
4. Includes concrete details (not generic statements)
5. Uses 1-2 emojis maximum
6. Is 4-5 sentences, MAX 450 characters total
7. If the claim is false, clearly state what the truth is based on the sources
8. END WITH exactly 3 sources: "{sources_suffix}"

{language_directive}

Examples of {company} style:
{persona.get('examples', {}).get(language, [''])[0]}
"""

    def _build_guardian_prompt(
        self,
        claim: str,
        fact_check,
        language: str,
        tiktok_rules: str,
        sources_text: str,
        language_directive: str,
    ) -> str:
        """Build the full ML-pipeline-driven Guardian Avatar prompt."""

        # Step 1: Analyze claim with ClaimRouter
        claim_analysis = self.claim_router.analyze_claim(claim)
        self.last_claim_analysis = claim_analysis

        # Step 2: Create context for Bandit
        bandit_context = BanditContext(
            claim_type=(
                claim_analysis.claim_types[0].value
                if claim_analysis.claim_types
                else "unknown"
            ),
            risk_level=claim_analysis.risk_level.value,
            language=language,
        )

        # Step 3: Select tone variant via Thompson Sampling
        tone_variant = self.bandit.select_tone(bandit_context)
        self.last_tone_variant = tone_variant
        logger.info(
            f"ML selected tone: {tone_variant.value} "
            f"for risk={claim_analysis.risk_level.value}"
        )

        # Step 4: Dynamic tone instructions
        tone_instructions = get_tone_instructions(tone_variant, language)
        opening_style = get_opening_style(tone_variant, language)

        # Step 5: Authoritative source labels
        claim_type_str = (
            claim_analysis.claim_types[0].value
            if claim_analysis.claim_types
            else "general"
        )
        source_labels = _resolve_source_labels(
            fact_check.sources if fact_check.sources else [],
            claim_type_str,
        )
        sources_line = " | ".join(source_labels)
        sources_suffix = (
            f"Sources: {sources_line}" if language == "en"
            else f"Quellen: {sources_line}"
        )
        logger.info(
            f"Guardian sources for {claim_type_str}: {sources_line}"
        )

        # Step 6: Temporal instructions
        temporal_instructions = get_temporal_instructions(
            claim_analysis.temporal_mode,
            claim_analysis.volatility,
            claim_analysis.is_territorial,
            language,
        )

        # Step 7: Response mode instructions (IO-awareness + Evidence Quality)
        response_mode_instructions = get_response_mode_instructions(
            claim_analysis.response_mode_result,
            claim_analysis.is_io_pattern,
            claim_analysis.io_indicators,
            language,
        )

        # Logging
        if claim_analysis.is_io_pattern:
            logger.info(
                f"IO detected (score={claim_analysis.io_score:.2f}): "
                f"{claim_analysis.io_indicators}"
            )
        if claim_analysis.response_mode_result:
            mode_str = claim_analysis.response_mode_result.primary.value
            if claim_analysis.response_mode_result.secondary:
                mode_str += (
                    f"+{claim_analysis.response_mode_result.secondary.value}"
                )
            logger.info(
                f"Response mode: {mode_str} "
                f"(evidence={claim_analysis.response_mode_result.evidence_quality.value})"
            )
        else:
            logger.info(
                f"Response mode (legacy): {claim_analysis.response_mode.value}"
            )

        return f"""
You are Guardian on TikTok. Fact-checker with personality.
{tiktok_rules}

=== YOUR VIBE ===
- Confident, not aggressive
- Clear, not preachy
- Human, not robotic
- Tone: {tone_variant.value.replace('_', ' ').title()}

=== RESPONSE MODE ===
{response_mode_instructions}

=== TEMPORAL CONTEXT ===
{temporal_instructions}

=== THE CLAIM ===
"{claim}"

=== WHAT YOU KNOW ===
Verdict: {'FALSE' if fact_check.is_fake else 'MISLEADING'}
Key fact: {fact_check.explanation}
{sources_text}

=== OUTPUT (TikTok Format) ===
1. HOOK (max 8 words): "{opening_style}" or your own punchy opener
2. THE CORRECTION: What's actually true. One fact.
3. PROOF: One number/date/stat from sources
4. Sources: "{sources_suffix}"

MAX 450 chars. {language_directive}

=== ONE RULE ===
No moralizing. No "you should know". No lectures.
Just: Hook -> Fact -> Source. Done.
"""

    def _build_brand_prompt(
        self,
        claim: str,
        fact_check,
        company: str,
        language: str,
        persona: Dict,
    ) -> str:
        """Build prompt for non-avatar company brands."""

        language_directive = (
            "Antwort ausschließlich auf Deutsch."
            if language == "de"
            else "Respond only in English."
        )
        lang_instructions = {
            "en": "Create an English response that",
            "de": "Erstelle eine deutsche Antwort, die",
        }

        return f"""
You are the official AI brand influencer for {company}.

Company Voice: {persona.get('voice', '')}
Tone: {persona.get('tone', '')}
Style: {persona.get('style', '')}

A claim about {company} is circulating:
"{claim}"

Fact-check result:
- Is fake: {fact_check.is_fake}
- Confidence: {fact_check.confidence}
- Category: {fact_check.category}
- Explanation: {fact_check.explanation}

{lang_instructions.get(language, lang_instructions['en'])}:
1. Addresses the claim directly
2. Uses {company}'s brand voice
3. Is engaging and shareable
4. Includes relevant emojis
5. Is 1-2 sentences max

{language_directive}
Make it feel authentic to {company}'s communication style.
"""

    # ------------------------------------------------------------------
    # Fallback helpers
    # ------------------------------------------------------------------

    def _fallback_response(
        self, company: str, language: str,
    ) -> AIInfluencerResponse:
        """Return a safe response when OpenAI client is unavailable."""

        if company in AVATAR_COMPANIES:
            persona = self.company_personas.get(
                company,
                self.company_personas.get("GuardianAvatar", {}),
            )
            emoji = persona.get("emoji", "")
            fallback_texts = {
                "en": f"{company} here! {emoji} Let me fact-check this claim...",
                "de": f"{company} hier! {emoji} Lass mich diese Behauptung prüfen...",
            }
        else:
            fallback_texts = {
                "en": (
                    f"As {company}, we take this claim seriously "
                    "and verify all facts."
                ),
                "de": (
                    f"Als {company} nehmen wir diese Behauptung ernst "
                    "und prüfen alle Fakten."
                ),
            }

        hashtags = (
            ["#TruthShield", "#FactCheck", f"#{company}"]
            if company in AVATAR_COMPANIES
            else [f"#{company}Facts", "#TruthShield"]
        )

        return AIInfluencerResponse(
            response_text=fallback_texts.get(language, fallback_texts["en"]),
            tone="professional",
            engagement_score=0.6,
            hashtags=hashtags,
            company_voice=company,
        )

    def _error_fallback(
        self, company: str, language: str,
    ) -> AIInfluencerResponse:
        """Return a safe response when generation fails with an exception."""

        if company in AVATAR_COMPANIES:
            persona = self.company_personas.get(
                company,
                self.company_personas.get("GuardianAvatar", {}),
            )
            emoji = persona.get("emoji", "")
            fallback = {
                "en": (
                    f"{company} says: That's an interesting claim! "
                    f"Let me check the facts... {emoji}"
                ),
                "de": (
                    f"{company} sagt: Das ist eine interessante Behauptung! "
                    f"Lass mich die Fakten prüfen... {emoji}"
                ),
            }
        else:
            fallback = {
                "en": f"We at {company} stand for facts and transparency.",
                "de": f"Wir bei {company} stehen für Fakten und Transparenz.",
            }

        hashtags = (
            ["#TruthShield", "#FactCheck", f"#{company}"]
            if company in AVATAR_COMPANIES
            else [f"#{company}"]
        )

        return AIInfluencerResponse(
            response_text=fallback.get(language, fallback["en"]),
            tone="professional",
            engagement_score=0.5,
            hashtags=hashtags,
            company_voice=company,
        )
