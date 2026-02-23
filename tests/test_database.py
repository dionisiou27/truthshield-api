"""Database model tests using synchronous in-memory SQLite."""

import json
import uuid
from datetime import datetime, timezone

import pytest

sa = pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed")
create_engine = sa.create_engine
inspect = sa.inspect

from sqlalchemy.orm import Session  # noqa: E402

from src.models.monitoring import Base, MonitoredContent, MonitoringKeyword  # noqa: E402
from src.models.claims import ClaimAnalysisRecord, BanditDecisionRecord, AuditLogEntry  # noqa: E402


@pytest.fixture
def db():
    """In-memory SQLite with all tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def engine():
    """Bare engine for schema introspection."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


# ── Schema tests ──────────────────────────────────────────────


class TestSchemaCreation:
    def test_all_tables_created(self, engine):
        table_names = inspect(engine).get_table_names()
        expected = {
            "monitored_content",
            "monitoring_keywords",
            "claim_analyses",
            "bandit_decisions",
            "audit_log",
        }
        assert expected == set(table_names)

    def test_claim_analyses_columns(self, engine):
        cols = {c["name"] for c in inspect(engine).get_columns("claim_analyses")}
        assert "claim_text" in cols
        assert "claim_hash" in cols
        assert "risk_level" in cols
        assert "io_score" in cols
        assert "created_at" in cols

    def test_bandit_decisions_columns(self, engine):
        cols = {c["name"] for c in inspect(engine).get_columns("bandit_decisions")}
        assert "decision_id" in cols
        assert "tone_variant" in cols
        assert "source_mix" in cols
        assert "reward" in cols
        assert "feedback_at" in cols

    def test_audit_log_columns(self, engine):
        cols = {c["name"] for c in inspect(engine).get_columns("audit_log")}
        assert "event_type" in cols
        assert "claim_hash" in cols
        assert "decision_id" in cols
        assert "details" in cols


# ── CRUD tests ────────────────────────────────────────────────


class TestClaimAnalysisCRUD:
    def test_insert_and_read(self, db):
        record = ClaimAnalysisRecord(
            claim_text="5G causes cancer",
            claim_hash="abc123",
            language="en",
            claim_types=json.dumps(["health_misinformation"]),
            risk_level="HIGH",
            volatility="STABLE",
            temporal_mode="ARCHIVE_OK",
            is_territorial=False,
            io_score=0.0,
            response_mode="DEBUNK",
            requires_guardian=True,
        )
        db.add(record)
        db.commit()

        result = db.query(ClaimAnalysisRecord).filter_by(claim_hash="abc123").first()
        assert result is not None
        assert result.claim_text == "5G causes cancer"
        assert result.risk_level == "HIGH"
        assert json.loads(result.claim_types) == ["health_misinformation"]

    def test_claim_hash_unique(self, db):
        for i in range(2):
            db.add(ClaimAnalysisRecord(
                claim_text=f"claim {i}",
                claim_hash="duplicate",
                language="en",
                requires_guardian=True,
            ))
        with pytest.raises(Exception):  # IntegrityError
            db.commit()

    def test_dedup_lookup(self, db):
        db.add(ClaimAnalysisRecord(
            claim_text="Earth is flat",
            claim_hash="flat123",
            language="en",
            requires_guardian=True,
        ))
        db.commit()
        assert db.query(ClaimAnalysisRecord).filter_by(claim_hash="flat123").first() is not None
        assert db.query(ClaimAnalysisRecord).filter_by(claim_hash="nonexistent").first() is None


class TestBanditDecisionCRUD:
    def test_insert_and_read(self, db):
        did = str(uuid.uuid4())
        record = BanditDecisionRecord(
            decision_id=did,
            claim_type="health_misinformation",
            risk_level="HIGH",
            platform="tiktok",
            tone_variant="FIRM",
            source_mix="institution_heavy",
        )
        db.add(record)
        db.commit()

        result = db.query(BanditDecisionRecord).filter_by(decision_id=did).first()
        assert result is not None
        assert result.tone_variant == "FIRM"
        assert result.reward is None  # no feedback yet

    def test_reward_update(self, db):
        did = str(uuid.uuid4())
        db.add(BanditDecisionRecord(
            decision_id=did,
            claim_type="conspiracy_theory",
            risk_level="MEDIUM",
            platform="tiktok",
            tone_variant="WITTY",
            source_mix="balanced",
        ))
        db.commit()

        record = db.query(BanditDecisionRecord).filter_by(decision_id=did).first()
        record.reward = 0.75
        record.feedback_at = datetime.now(timezone.utc)
        db.commit()

        updated = db.query(BanditDecisionRecord).filter_by(decision_id=did).first()
        assert updated.reward == 0.75
        assert updated.feedback_at is not None


class TestAuditLogCRUD:
    def test_insert_and_read(self, db):
        entry = AuditLogEntry(
            event_type="claim_analyzed",
            claim_hash="hash456",
            details=json.dumps({"risk": "HIGH", "types": ["health_misinformation"]}),
        )
        db.add(entry)
        db.commit()

        result = db.query(AuditLogEntry).filter_by(claim_hash="hash456").first()
        assert result is not None
        assert result.event_type == "claim_analyzed"
        assert json.loads(result.details)["risk"] == "HIGH"

    def test_multiple_events_per_claim(self, db):
        for event in ["claim_analyzed", "response_generated", "decision_made"]:
            db.add(AuditLogEntry(
                event_type=event,
                claim_hash="same_claim",
            ))
        db.commit()

        entries = db.query(AuditLogEntry).filter_by(claim_hash="same_claim").all()
        assert len(entries) == 3
        assert {e.event_type for e in entries} == {
            "claim_analyzed", "response_generated", "decision_made"
        }


# ── Existing model tests ─────────────────────────────────────


class TestMonitoringModels:
    def test_monitored_content_insert(self, db):
        content = MonitoredContent(
            platform="twitter",
            content_id="tweet_123",
            content_text="Test content",
            company_target="BMW",
        )
        db.add(content)
        db.commit()

        result = db.query(MonitoredContent).filter_by(content_id="tweet_123").first()
        assert result is not None
        assert result.platform == "twitter"

    def test_monitoring_keyword_insert(self, db):
        kw = MonitoringKeyword(
            company_name="Vodafone",
            keyword="5G conspiracy",
            language="en",
        )
        db.add(kw)
        db.commit()

        result = db.query(MonitoringKeyword).filter_by(company_name="Vodafone").first()
        assert result is not None
        assert result.keyword == "5G conspiracy"
        assert result.active is True
