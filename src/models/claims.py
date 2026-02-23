from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text
from sqlalchemy.sql import func
from src.models.monitoring import Base


class ClaimAnalysisRecord(Base):
    """Persisted claim analysis results."""
    __tablename__ = "claim_analyses"

    id = Column(Integer, primary_key=True, index=True)
    claim_text = Column(Text, nullable=False)
    claim_hash = Column(String(64), unique=True, index=True)  # SHA256 dedup
    language = Column(String(5))
    claim_types = Column(Text)  # JSON-serialized List[ClaimType]
    risk_level = Column(String(20))
    volatility = Column(String(20))
    temporal_mode = Column(String(20))
    is_territorial = Column(Boolean, default=False)
    io_score = Column(Float, default=0.0)
    response_mode = Column(String(20))
    requires_guardian = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BanditDecisionRecord(Base):
    """Bandit decisions for audit and analysis."""
    __tablename__ = "bandit_decisions"

    id = Column(Integer, primary_key=True, index=True)
    decision_id = Column(String(36), unique=True, index=True)  # UUID
    claim_type = Column(String(50))
    risk_level = Column(String(20))
    platform = Column(String(20))
    tone_variant = Column(String(20))
    source_mix = Column(String(30))
    reward = Column(Float, nullable=True)  # NULL until feedback arrives
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    feedback_at = Column(DateTime(timezone=True), nullable=True)


class AuditLogEntry(Base):
    """Audit trail for EU compliance (AI Act Art. 14)."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # claim_analyzed, response_generated, decision_made
    claim_hash = Column(String(64), nullable=True, index=True)
    decision_id = Column(String(36), nullable=True)
    details = Column(Text)  # JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
