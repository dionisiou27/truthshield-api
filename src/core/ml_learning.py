"""
TruthShield ML Learning System
Kontinuierliches Lernen aus jeder Interaktion

Components:
1. InteractionLogger - Logs every fact-check, response, engagement
2. FeatureStore - Extracts and stores ML features
3. FeedbackLoop - Processes engagement metrics and corrections
4. OnlineLearner - Updates models based on new data
5. ModelRegistry - Manages different ML models
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
from collections import defaultdict

logger = logging.getLogger(__name__)


class LearningSignal(Enum):
    """Types of learning signals"""
    POSITIVE = "positive"  # Good response (high engagement, no corrections)
    NEGATIVE = "negative"  # Bad response (low engagement, corrections needed)
    NEUTRAL = "neutral"    # No signal yet
    EXPERT_VERIFIED = "expert_verified"  # Expert confirmed correct
    EXPERT_CORRECTED = "expert_corrected"  # Expert provided correction


@dataclass
class InteractionRecord:
    """Record of a single fact-check interaction"""
    interaction_id: str
    timestamp: str

    # Input
    claim_text: str
    claim_hash: str
    claim_language: str
    claim_category: str  # politics, health, science, viral, etc.

    # Detection
    avatar_used: str
    platform: str
    is_fake_detected: bool
    confidence: float
    astroturfing_score: float

    # Sources used
    sources_used: List[str] = field(default_factory=list)
    source_count: int = 0
    academic_sources_count: int = 0

    # Response
    response_text: str = ""
    response_length: int = 0

    # Features (for ML)
    features: Dict[str, float] = field(default_factory=dict)

    # Feedback (filled later)
    engagement_score: float = 0.0
    likes: int = 0
    replies: int = 0
    shares: int = 0
    top_comment_achieved: bool = False

    # Learning signal
    learning_signal: str = LearningSignal.NEUTRAL.value
    expert_correction: Optional[str] = None
    user_feedback: Optional[str] = None


@dataclass
class ClaimPattern:
    """Learned pattern for claim detection"""
    pattern_id: str
    pattern_type: str  # "misinformation", "astroturfing", "satire", "true"
    keywords: List[str]
    context_signals: List[str]
    confidence: float
    occurrence_count: int
    last_seen: str
    avg_detection_confidence: float


class FeatureExtractor:
    """Extract ML features from claims and responses"""

    @staticmethod
    def extract_claim_features(claim: str, language: str = "en") -> Dict[str, float]:
        """Extract features from a claim for ML"""
        text_lower = claim.lower()

        features = {
            # Text features
            "char_count": len(claim),
            "word_count": len(claim.split()),
            "avg_word_length": sum(len(w) for w in claim.split()) / max(len(claim.split()), 1),
            "exclamation_count": claim.count("!"),
            "question_count": claim.count("?"),
            "caps_ratio": sum(1 for c in claim if c.isupper()) / max(len(claim), 1),
            "number_count": sum(1 for c in claim if c.isdigit()),

            # Misinformation signals
            "has_absolute_terms": float(any(t in text_lower for t in ["always", "never", "everyone", "nobody", "immer", "nie"])),
            "has_urgency": float(any(t in text_lower for t in ["breaking", "urgent", "shocking", "eilmeldung", "schockierend"])),
            "has_conspiracy_terms": float(any(t in text_lower for t in ["they don't want", "hidden truth", "secret", "geheim", "verschwiegen"])),
            "has_emotional_language": float(any(t in text_lower for t in ["outrage", "scandal", "disgusting", "skandal", "widerlich"])),

            # Astroturfing signals
            "has_political_target": float(any(t in text_lower for t in ["merkel", "biden", "trump", "macron", "scholz", "von der leyen"])),
            "has_corruption_accusation": float(any(t in text_lower for t in ["corrupt", "crooked", "dirty", "korrupt", "kriminell"])),
            "has_call_to_action": float(any(t in text_lower for t in ["share this", "spread the word", "wake up", "teilt das", "aufwachen"])),

            # Scientific claim signals
            "has_science_terms": float(any(t in text_lower for t in ["study", "research", "scientists", "studie", "forschung", "wissenschaftler"])),
            "has_health_terms": float(any(t in text_lower for t in ["vaccine", "covid", "treatment", "impfung", "behandlung"])),
            "has_citation": float(any(t in text_lower for t in ["according to", "study shows", "research found", "laut", "zeigt"])),

            # Language
            "is_german": float(language == "de"),
            "is_english": float(language == "en"),
        }

        return features

    @staticmethod
    def extract_response_features(response: str, platform: str) -> Dict[str, float]:
        """Extract features from generated response"""
        features = {
            "response_length": len(response),
            "word_count": len(response.split()),
            "emoji_count": sum(1 for c in response if ord(c) > 127000),  # Rough emoji detection
            "has_source_citation": float("quellen:" in response.lower() or "sources:" in response.lower()),
            "has_hook": float(response.strip().endswith("?") or response.strip().startswith(("Did", "Wusstet", "Fun fact", "Plot twist"))),
            "question_count": response.count("?"),

            # Platform optimization
            "is_tiktok_optimized": float(platform == "tiktok" and 300 <= len(response) <= 500),
            "is_twitter_optimized": float(platform == "twitter" and len(response) <= 280),
        }
        return features


class InteractionLogger:
    """Logs all interactions for ML learning"""

    def __init__(self, db_path: str = "truthshield_ml.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for interaction logging"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id TEXT PRIMARY KEY,
                timestamp TEXT,
                claim_text TEXT,
                claim_hash TEXT,
                claim_language TEXT,
                claim_category TEXT,
                avatar_used TEXT,
                platform TEXT,
                is_fake_detected INTEGER,
                confidence REAL,
                astroturfing_score REAL,
                sources_used TEXT,
                source_count INTEGER,
                academic_sources_count INTEGER,
                response_text TEXT,
                response_length INTEGER,
                features TEXT,
                engagement_score REAL DEFAULT 0,
                likes INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                top_comment_achieved INTEGER DEFAULT 0,
                learning_signal TEXT DEFAULT 'neutral',
                expert_correction TEXT,
                user_feedback TEXT
            )
        """)

        # Claim patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claim_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                keywords TEXT,
                context_signals TEXT,
                confidence REAL,
                occurrence_count INTEGER,
                last_seen TEXT,
                avg_detection_confidence REAL
            )
        """)

        # Model performance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                model_name TEXT,
                accuracy REAL,
                precision_score REAL,
                recall_score REAL,
                f1_score REAL,
                sample_count INTEGER
            )
        """)

        # Engagement metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engagement_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id TEXT,
                timestamp TEXT,
                platform TEXT,
                likes INTEGER,
                replies INTEGER,
                shares INTEGER,
                top_comment INTEGER,
                engagement_rate REAL,
                FOREIGN KEY (interaction_id) REFERENCES interactions(interaction_id)
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"✅ ML database initialized at {self.db_path}")

    def log_interaction(self, record: InteractionRecord) -> str:
        """Log a new interaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO interactions
            (interaction_id, timestamp, claim_text, claim_hash, claim_language, claim_category,
             avatar_used, platform, is_fake_detected, confidence, astroturfing_score,
             sources_used, source_count, academic_sources_count, response_text, response_length,
             features, learning_signal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.interaction_id,
            record.timestamp,
            record.claim_text,
            record.claim_hash,
            record.claim_language,
            record.claim_category,
            record.avatar_used,
            record.platform,
            int(record.is_fake_detected),
            record.confidence,
            record.astroturfing_score,
            json.dumps(record.sources_used),
            record.source_count,
            record.academic_sources_count,
            record.response_text,
            record.response_length,
            json.dumps(record.features),
            record.learning_signal
        ))

        conn.commit()
        conn.close()

        logger.info(f"📝 Logged interaction {record.interaction_id}")
        return record.interaction_id

    def update_engagement(self, interaction_id: str, likes: int, replies: int,
                          shares: int, top_comment: bool) -> None:
        """Update engagement metrics for an interaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate engagement score (weighted)
        engagement_score = (likes * 1.0 + replies * 2.0 + shares * 3.0 +
                            (10.0 if top_comment else 0)) / 16.0  # Normalized to ~0-1

        # Update interaction
        cursor.execute("""
            UPDATE interactions
            SET likes = ?, replies = ?, shares = ?, top_comment_achieved = ?,
                engagement_score = ?
            WHERE interaction_id = ?
        """, (likes, replies, shares, int(top_comment), engagement_score, interaction_id))

        # Log to engagement metrics
        cursor.execute("""
            INSERT INTO engagement_metrics
            (interaction_id, timestamp, platform, likes, replies, shares, top_comment, engagement_rate)
            SELECT interaction_id, ?, platform, ?, ?, ?, ?, ?
            FROM interactions WHERE interaction_id = ?
        """, (datetime.utcnow().isoformat(), likes, replies, shares, int(top_comment),
              engagement_score, interaction_id))

        # Update learning signal based on engagement
        if engagement_score > 0.7:
            learning_signal = LearningSignal.POSITIVE.value
        elif engagement_score < 0.2 and (likes + replies + shares) > 0:
            learning_signal = LearningSignal.NEGATIVE.value
        else:
            learning_signal = LearningSignal.NEUTRAL.value

        cursor.execute("""
            UPDATE interactions SET learning_signal = ? WHERE interaction_id = ?
        """, (learning_signal, interaction_id))

        conn.commit()
        conn.close()

        logger.info(
            f"📊 Updated engagement for {interaction_id}: score={engagement_score:.2f}, signal={learning_signal}")

    def add_expert_feedback(self, interaction_id: str, is_correct: bool,
                            correction: Optional[str] = None) -> None:
        """Add expert verification/correction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if is_correct:
            learning_signal = LearningSignal.EXPERT_VERIFIED.value
        else:
            learning_signal = LearningSignal.EXPERT_CORRECTED.value

        cursor.execute("""
            UPDATE interactions
            SET learning_signal = ?, expert_correction = ?
            WHERE interaction_id = ?
        """, (learning_signal, correction, interaction_id))

        conn.commit()
        conn.close()

        logger.info(f"👨‍🔬 Expert feedback added for {interaction_id}: {'correct' if is_correct else 'corrected'}")

    def get_training_data(self, signal_filter: Optional[str] = None,
                          limit: int = 1000) -> List[Dict]:
        """Get labeled training data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if signal_filter:
            cursor.execute("""
                SELECT * FROM interactions
                WHERE learning_signal = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (signal_filter, limit))
        else:
            cursor.execute("""
                SELECT * FROM interactions
                WHERE learning_signal != 'neutral'
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))

        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        return [dict(zip(columns, row)) for row in rows]


class PatternLearner:
    """Learns patterns from claims for better detection"""

    def __init__(self, db_path: str = "truthshield_ml.db"):
        self.db_path = db_path
        self.patterns: Dict[str, ClaimPattern] = {}
        self._load_patterns()

    def _load_patterns(self):
        """Load existing patterns from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM claim_patterns")
        for row in cursor.fetchall():
            pattern = ClaimPattern(
                pattern_id=row[0],
                pattern_type=row[1],
                keywords=json.loads(row[2]),
                context_signals=json.loads(row[3]),
                confidence=row[4],
                occurrence_count=row[5],
                last_seen=row[6],
                avg_detection_confidence=row[7]
            )
            self.patterns[pattern.pattern_id] = pattern

        conn.close()
        logger.info(f"📚 Loaded {len(self.patterns)} claim patterns")

    def learn_pattern(self, claim: str, claim_type: str, confidence: float) -> str:
        """Learn a new pattern or update existing one"""
        # Extract key phrases
        words = claim.lower().split()
        # Simple n-gram extraction (2-3 word phrases)
        keywords = []
        for i in range(len(words) - 1):
            keywords.append(" ".join(words[i:i + 2]))
        for i in range(len(words) - 2):
            keywords.append(" ".join(words[i:i + 3]))

        # Create pattern ID from keywords hash
        pattern_hash = hashlib.md5(" ".join(sorted(keywords[:5])).encode()).hexdigest()[:12]
        pattern_id = f"pattern_{claim_type}_{pattern_hash}"

        if pattern_id in self.patterns:
            # Update existing pattern
            pattern = self.patterns[pattern_id]
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.utcnow().isoformat()
            pattern.avg_detection_confidence = (
                (pattern.avg_detection_confidence * (pattern.occurrence_count - 1) + confidence)
                / pattern.occurrence_count
            )
        else:
            # Create new pattern
            pattern = ClaimPattern(
                pattern_id=pattern_id,
                pattern_type=claim_type,
                keywords=keywords[:10],
                context_signals=[],
                confidence=confidence,
                occurrence_count=1,
                last_seen=datetime.utcnow().isoformat(),
                avg_detection_confidence=confidence
            )
            self.patterns[pattern_id] = pattern

        # Save to database
        self._save_pattern(pattern)

        return pattern_id

    def _save_pattern(self, pattern: ClaimPattern):
        """Save pattern to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO claim_patterns
            (pattern_id, pattern_type, keywords, context_signals, confidence,
             occurrence_count, last_seen, avg_detection_confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern.pattern_id,
            pattern.pattern_type,
            json.dumps(pattern.keywords),
            json.dumps(pattern.context_signals),
            pattern.confidence,
            pattern.occurrence_count,
            pattern.last_seen,
            pattern.avg_detection_confidence
        ))

        conn.commit()
        conn.close()

    def find_similar_patterns(self, claim: str, threshold: float = 0.3) -> List[ClaimPattern]:
        """Find patterns similar to a claim"""
        claim_lower = claim.lower()
        similar = []

        for pattern in self.patterns.values():
            # Calculate keyword overlap
            matches = sum(1 for kw in pattern.keywords if kw in claim_lower)
            similarity = matches / max(len(pattern.keywords), 1)

            if similarity >= threshold:
                similar.append(pattern)

        # Sort by confidence and occurrence
        similar.sort(key=lambda p: (p.confidence * p.occurrence_count), reverse=True)
        return similar[:5]


class ResponseOptimizer:
    """Optimizes responses based on learned engagement patterns"""

    def __init__(self, db_path: str = "truthshield_ml.db"):
        self.db_path = db_path
        self.engagement_weights = self._load_engagement_weights()

    def _load_engagement_weights(self) -> Dict[str, Dict[str, float]]:
        """Load learned engagement weights per platform/avatar"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        weights = defaultdict(lambda: defaultdict(float))

        try:
            # Get average engagement by platform and avatar
            cursor.execute("""
                SELECT platform, avatar_used,
                       AVG(engagement_score) as avg_engagement,
                       AVG(response_length) as avg_length,
                       COUNT(*) as count
                FROM interactions
                WHERE learning_signal IN ('positive', 'expert_verified')
                GROUP BY platform, avatar_used
            """)

            for row in cursor.fetchall():
                platform, avatar, avg_eng, avg_len, count = row
                if count >= 5:  # Only use if enough samples
                    weights[platform][f"{avatar}_engagement"] = avg_eng
                    weights[platform][f"{avatar}_optimal_length"] = avg_len

        except sqlite3.OperationalError:
            pass  # Table might not exist yet

        conn.close()
        return dict(weights)

    def get_optimal_response_params(self, platform: str, avatar: str) -> Dict[str, Any]:
        """Get optimal response parameters based on learned patterns"""
        platform_weights = self.engagement_weights.get(platform, {})

        # Default params
        params = {
            "target_length": 400,
            "emoji_density": "medium",
            "hook_style": "question",
            "confidence_threshold": 0.7
        }

        # Override with learned values
        if f"{avatar}_optimal_length" in platform_weights:
            params["target_length"] = int(platform_weights[f"{avatar}_optimal_length"])

        return params

    def score_response_quality(self, response: str, platform: str, avatar: str) -> float:
        """Score a response based on learned quality patterns"""
        features = FeatureExtractor.extract_response_features(response, platform)

        # Base score
        score = 0.5

        # Length optimization
        optimal_length = self.engagement_weights.get(platform, {}).get(f"{avatar}_optimal_length", 400)
        length_diff = abs(len(response) - optimal_length) / optimal_length
        score += max(0, 0.2 - length_diff * 0.2)  # Up to +0.2 for optimal length

        # Hook bonus
        if features.get("has_hook", 0) > 0:
            score += 0.1

        # Source citation bonus
        if features.get("has_source_citation", 0) > 0:
            score += 0.1

        # Platform optimization bonus
        if features.get(f"is_{platform}_optimized", 0) > 0:
            score += 0.1

        return min(score, 1.0)


class TruthShieldMLSystem:
    """Main ML system orchestrating all learning components"""

    def __init__(self, db_path: str = "truthshield_ml.db"):
        self.db_path = db_path
        self.logger = InteractionLogger(db_path)
        self.pattern_learner = PatternLearner(db_path)
        self.response_optimizer = ResponseOptimizer(db_path)
        self.feature_extractor = FeatureExtractor()

    async def record_fact_check(self,
                                claim: str,
                                language: str,
                                avatar: str,
                                platform: str,
                                is_fake: bool,
                                confidence: float,
                                astroturfing_score: float,
                                sources: List[str],
                                response: str,
                                category: str = "unknown") -> str:
        """Record a fact-check interaction for learning"""

        # Generate interaction ID
        interaction_id = f"fc_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{hashlib.md5(claim.encode()).hexdigest()[:8]}"

        # Extract features
        claim_features = self.feature_extractor.extract_claim_features(claim, language)
        response_features = self.feature_extractor.extract_response_features(response, platform)
        all_features = {**claim_features, **response_features}

        # Count academic sources
        academic_sources = sum(1 for s in sources if any(
            domain in s.lower() for domain in ["pubmed", "arxiv", "nature.com", "science.org", "who.int", "semantic"]
        ))

        # Create record
        record = InteractionRecord(
            interaction_id=interaction_id,
            timestamp=datetime.utcnow().isoformat(),
            claim_text=claim,
            claim_hash=hashlib.md5(claim.encode()).hexdigest(),
            claim_language=language,
            claim_category=category,
            avatar_used=avatar,
            platform=platform,
            is_fake_detected=is_fake,
            confidence=confidence,
            astroturfing_score=astroturfing_score,
            sources_used=sources,
            source_count=len(sources),
            academic_sources_count=academic_sources,
            response_text=response,
            response_length=len(response),
            features=all_features
        )

        # Log interaction
        self.logger.log_interaction(record)

        # Learn pattern
        claim_type = "misinformation" if is_fake else "true"
        self.pattern_learner.learn_pattern(claim, claim_type, confidence)

        logger.info(f"🧠 ML recorded fact-check {interaction_id}")
        return interaction_id

    async def update_with_engagement(self, interaction_id: str,
                                     likes: int, replies: int,
                                     shares: int, top_comment: bool) -> None:
        """Update learning with engagement metrics"""
        self.logger.update_engagement(interaction_id, likes, replies, shares, top_comment)

        # Refresh optimizer weights
        self.response_optimizer.engagement_weights = self.response_optimizer._load_engagement_weights()

    async def get_pattern_boost(self, claim: str) -> Tuple[float, str]:
        """Get confidence boost from known patterns"""
        similar_patterns = self.pattern_learner.find_similar_patterns(claim)

        if not similar_patterns:
            return 0.0, "no_pattern_match"

        # Use the most confident matching pattern
        best_pattern = similar_patterns[0]

        # Calculate boost based on pattern confidence and occurrence
        boost = min(0.2, best_pattern.avg_detection_confidence * 0.1 * min(best_pattern.occurrence_count, 10))

        return boost, best_pattern.pattern_type

    def get_response_optimization(self, platform: str, avatar: str) -> Dict[str, Any]:
        """Get learned response optimization parameters"""
        return self.response_optimizer.get_optimal_response_params(platform, avatar)

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about ML learning"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        try:
            # Total interactions
            cursor.execute("SELECT COUNT(*) FROM interactions")
            stats["total_interactions"] = cursor.fetchone()[0]

            # By learning signal
            cursor.execute("""
                SELECT learning_signal, COUNT(*)
                FROM interactions
                GROUP BY learning_signal
            """)
            stats["by_signal"] = dict(cursor.fetchall())

            # By platform
            cursor.execute("""
                SELECT platform, COUNT(*), AVG(engagement_score)
                FROM interactions
                GROUP BY platform
            """)
            stats["by_platform"] = {row[0]: {"count": row[1], "avg_engagement": row[2]}
                                    for row in cursor.fetchall()}

            # Total patterns learned
            cursor.execute("SELECT COUNT(*) FROM claim_patterns")
            stats["patterns_learned"] = cursor.fetchone()[0]

            # Average engagement by avatar
            cursor.execute("""
                SELECT avatar_used, AVG(engagement_score), COUNT(*)
                FROM interactions
                WHERE engagement_score > 0
                GROUP BY avatar_used
            """)
            stats["avatar_performance"] = {row[0]: {"avg_engagement": row[1], "count": row[2]}
                                           for row in cursor.fetchall()}

        except sqlite3.OperationalError as e:
            stats["error"] = str(e)

        conn.close()
        return stats


# Global ML system instance
ml_system = TruthShieldMLSystem()


async def record_interaction(claim: str, language: str, avatar: str, platform: str,
                             is_fake: bool, confidence: float, astroturfing_score: float,
                             sources: List[str], response: str) -> str:
    """Convenience function to record an interaction"""
    return await ml_system.record_fact_check(
        claim=claim,
        language=language,
        avatar=avatar,
        platform=platform,
        is_fake=is_fake,
        confidence=confidence,
        astroturfing_score=astroturfing_score,
        sources=sources,
        response=response
    )


async def update_engagement(interaction_id: str, likes: int, replies: int,
                            shares: int, top_comment: bool) -> None:
    """Convenience function to update engagement"""
    await ml_system.update_with_engagement(interaction_id, likes, replies, shares, top_comment)


def get_pattern_boost(claim: str) -> Tuple[float, str]:
    """Synchronous wrapper for pattern boost"""
    return asyncio.get_event_loop().run_until_complete(ml_system.get_pattern_boost(claim))
