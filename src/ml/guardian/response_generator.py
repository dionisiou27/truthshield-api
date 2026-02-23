"""
Guardian Response Generator
Integrates claim analysis, source ranking, and bandit decisions.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import logging

from .claim_router import ClaimRouter, ClaimAnalysis, ClaimType
from .source_ranker import SourceRanker, SourceCandidate
from ..learning.bandit import BanditContext, BanditDecision, ToneVariant, get_bandit
from ..learning.feedback import ResponseLog, get_collector
from ..learning.logging import get_learning_logger

logger = logging.getLogger(__name__)


class GuardianResponse(BaseModel):
    """Complete Guardian response with ML metadata."""
    response_id: str
    claim_id: str
    timestamp: datetime

    # Analysis
    claim_analysis: ClaimAnalysis

    # Sources
    selected_sources: List[Dict]
    source_ranking_meta: Dict

    # Decision
    decision_id: Optional[str] = None
    tone_variant: str
    source_mix: str

    # Response
    response_text: str
    source_line: str
    constraints: Dict

    # Learning
    learning_enabled: bool = True
    variant_id: str = "guardian_v1"


class GuardianResponseGenerator:
    """
    Guardian Response Generator - ML-enhanced response pipeline.

    Pipeline:
    1. Claim intake & analysis (ClaimRouter)
    2. Source retrieval & ranking (SourceRanker)
    3. Tone/mix selection (GuardianBandit)
    4. Response generation (via existing ai_engine)
    5. Logging for learning
    """

    def __init__(
        self,
        bandit_state_path: Optional[str] = "demo_data/ml/bandit_state.json",
        feedback_dir: str = "demo_data/ml",
        log_dir: str = "demo_data/ml/logs"
    ):
        self.claim_router = ClaimRouter()
        self.source_ranker = SourceRanker()
        self.bandit = get_bandit(bandit_state_path)
        self.feedback_collector = get_collector(feedback_dir)
        self.learning_logger = get_learning_logger(log_dir)

        logger.info("GuardianResponseGenerator initialized")

    def analyze_claim(self, claim_text: str) -> ClaimAnalysis:
        """
        Step 1: Analyze and classify the claim.
        """
        analysis = self.claim_router.analyze_claim(claim_text)

        # Log for learning
        self.learning_logger.log_claim_analysis(
            claim_id=analysis.claim_id,
            claim_text=claim_text,
            claim_types=[ct.value for ct in analysis.claim_types],
            risk_level=analysis.risk_level.value,
            keywords=analysis.keywords,
            requires_guardian=analysis.requires_guardian
        )

        return analysis

    def rank_sources(
        self,
        candidates: List[SourceCandidate],
        claim_analysis: ClaimAnalysis
    ) -> List[SourceCandidate]:
        """
        Step 2: Rank and select sources.
        """
        # Use keywords from claim analysis
        selected = self.source_ranker.rank_sources(
            candidates=candidates,
            claim_keywords=claim_analysis.keywords
        )

        # Get rejection reasons for logging
        rejections = self.source_ranker.get_rejection_reasons(candidates, selected)

        # Log for learning
        self.learning_logger.log_source_ranking(
            claim_id=claim_analysis.claim_id,
            candidates_count=len(candidates),
            selected_sources=[s.model_dump() for s in selected],
            rejected_top=rejections,
            ranking_config=self.source_ranker.config.model_dump()
        )

        return selected

    def make_bandit_decision(self, claim_analysis: ClaimAnalysis) -> BanditDecision:
        """
        Step 3: Select tone variant and source mix using bandit.
        """
        # Build context
        context = BanditContext(
            claim_type=claim_analysis.claim_types[0].value if claim_analysis.claim_types else "unknown",
            risk_level=claim_analysis.risk_level.value,
            topic=self._infer_topic(claim_analysis),
            language=claim_analysis.language,
            time_of_day=datetime.now().hour
        )

        # Make decision
        decision = self.bandit.make_decision(context)

        # Log for learning
        self.learning_logger.log_bandit_decision(
            decision_id=decision.decision_id,
            claim_id=claim_analysis.claim_id,
            context=context.model_dump(),
            tone_variant=decision.tone_variant.value,
            source_mix=decision.source_mix.value,
            arm_stats=self.bandit.get_arm_stats()
        )

        return decision

    def _infer_topic(self, analysis: ClaimAnalysis) -> Optional[str]:
        """Infer topic from claim types."""
        type_to_topic = {
            ClaimType.HEALTH_MISINFORMATION: "health",
            ClaimType.SCIENCE_DENIAL: "science",
            ClaimType.POLICY_AID_OVERSIGHT: "policy",
            ClaimType.FOREIGN_INFLUENCE: "geopolitics",
            ClaimType.CONSPIRACY_THEORY: "conspiracy",
        }

        for ct in analysis.claim_types:
            if ct in type_to_topic:
                return type_to_topic[ct]

        return None

    def build_tone_prompt(self, tone_variant: ToneVariant, language: str) -> str:
        """Build tone-specific prompt modification."""
        tone_prompts = {
            ToneVariant.BOUNDARY_STRICT: {
                "de": "Beginne mit einem klaren 'Stop.' oder 'Halt.' Sei direkt und unmissverständlich.",
                "en": "Start with a clear 'Stop.' Be direct and unambiguous."
            },
            ToneVariant.BOUNDARY_FIRM: {
                "de": "Sei bestimmt aber sachlich. Benenne klar die Falschaussage.",
                "en": "Be firm but factual. Clearly name the false claim."
            },
            ToneVariant.BOUNDARY_EDUCATIONAL: {
                "de": "Erkläre sachlich, warum die Behauptung nicht stimmt. Biete Kontext.",
                "en": "Explain factually why the claim is incorrect. Provide context."
            }
        }

        return tone_prompts.get(tone_variant, {}).get(language, "")

    def format_source_line(self, sources: List[SourceCandidate], language: str) -> str:
        """Format the source line for the response."""
        source_names = []
        for src in sources[:3]:
            # Extract short name from title or publisher
            if src.publisher:
                name = src.publisher[:25]
            else:
                name = src.title.split(' - ')[0].split(' | ')[0][:25]
            source_names.append(name)

        # Pad with defaults if needed
        while len(source_names) < 3:
            defaults = ["EU Fundamental Rights", "UN Hate Speech Guidance", "bpb.de"]
            source_names.append(defaults[len(source_names)])

        sources_line = " | ".join(source_names)

        if language == "de":
            return f"Quellen: {sources_line}"
        return f"Sources: {sources_line}"

    def log_response(
        self,
        response_id: str,
        claim_analysis: ClaimAnalysis,
        decision: BanditDecision,
        response_text: str,
        sources: List[SourceCandidate]
    ):
        """Log the complete response for feedback collection."""
        log = ResponseLog(
            response_id=response_id,
            claim_id=claim_analysis.claim_id,
            timestamp=datetime.now(),
            claim_text=claim_analysis.normalized_claim,
            claim_type=[ct.value for ct in claim_analysis.claim_types],
            risk_level=claim_analysis.risk_level.value,
            language=claim_analysis.language,
            tone_variant=decision.tone_variant.value,
            source_mix=decision.source_mix.value,
            decision_id=decision.decision_id,
            response_text=response_text,
            sources_used=[s.model_dump() for s in sources]
        )

        self.feedback_collector.log_response(log)

        # Log generation event
        self.learning_logger.log_response_generated(
            response_id=response_id,
            claim_id=claim_analysis.claim_id,
            decision_id=decision.decision_id,
            response_length=len(response_text),
            sources_count=len(sources),
            generation_time_ms=0  # Would be filled by actual generation
        )

    def prepare_response(
        self,
        claim_text: str,
        source_candidates: List[SourceCandidate]
    ) -> GuardianResponse:
        """
        Full ML-enhanced response preparation pipeline.

        Note: This prepares all ML decisions but does NOT generate the final text.
        The actual text generation should use the existing ai_engine with the
        tone_variant and selected sources from this response.
        """
        response_id = str(uuid.uuid4())

        # Step 1: Analyze claim
        claim_analysis = self.analyze_claim(claim_text)

        # Step 2: Rank sources
        selected_sources = self.rank_sources(source_candidates, claim_analysis)

        # Step 3: Make bandit decision
        decision = self.make_bandit_decision(claim_analysis)

        # Step 4: Build response metadata
        source_line = self.format_source_line(selected_sources, claim_analysis.language)
        tone_prompt = self.build_tone_prompt(decision.tone_variant, claim_analysis.language)

        return GuardianResponse(
            response_id=response_id,
            claim_id=claim_analysis.claim_id,
            timestamp=datetime.now(),
            claim_analysis=claim_analysis,
            selected_sources=[s.model_dump() for s in selected_sources],
            source_ranking_meta={
                "candidates_count": len(source_candidates),
                "selected_count": len(selected_sources),
                "ranking_config": self.source_ranker.config.model_dump()
            },
            decision_id=decision.decision_id,
            tone_variant=decision.tone_variant.value,
            source_mix=decision.source_mix.value,
            response_text="",  # To be filled by ai_engine
            source_line=source_line,
            constraints={
                "sentences": 5,
                "max_chars": 450,
                "sources_required": 3,
                "tone_prompt": tone_prompt
            },
            learning_enabled=True,
            variant_id=f"guardian_v1_{decision.tone_variant.value}"
        )

    def get_pipeline_stats(self) -> Dict:
        """Get ML pipeline statistics."""
        return {
            "bandit_stats": self.bandit.get_arm_stats(),
            "learning_summary": self.learning_logger.get_learning_summary(),
            "ranker_config": self.source_ranker.config.model_dump()
        }


# Singleton instance
_generator_instance: Optional[GuardianResponseGenerator] = None


def get_generator() -> GuardianResponseGenerator:
    """Get or create the global response generator."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = GuardianResponseGenerator()
    return _generator_instance
