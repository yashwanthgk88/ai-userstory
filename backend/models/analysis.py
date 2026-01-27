import uuid
from datetime import datetime

from sqlalchemy import Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class SecurityAnalysis(Base):
    __tablename__ = "security_analyses"
    __table_args__ = (UniqueConstraint("user_story_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_story_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_stories.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    abuse_cases: Mapped[dict] = mapped_column(JSONB, nullable=False)
    stride_threats: Mapped[dict] = mapped_column(JSONB, nullable=False)
    security_requirements: Mapped[dict] = mapped_column(JSONB, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    ai_model_used: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user_story = relationship("UserStory", back_populates="analyses")
    compliance_mappings = relationship("ComplianceMapping", back_populates="analysis", cascade="all, delete-orphan")
