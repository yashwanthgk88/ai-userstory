import uuid

from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class ComplianceMapping(Base):
    __tablename__ = "compliance_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("security_analyses.id", ondelete="CASCADE"))
    requirement_id: Mapped[str] = mapped_column(String(50))
    standard_name: Mapped[str] = mapped_column(String(100), nullable=False)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False)
    control_title: Mapped[str | None] = mapped_column(String(500))
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    analysis = relationship("SecurityAnalysis", back_populates="compliance_mappings")
