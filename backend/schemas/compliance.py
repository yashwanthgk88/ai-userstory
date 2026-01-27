from uuid import UUID
from pydantic import BaseModel


class ComplianceMappingResponse(BaseModel):
    id: UUID
    analysis_id: UUID
    requirement_id: str
    standard_name: str
    control_id: str
    control_title: str | None
    relevance_score: float

    model_config = {"from_attributes": True}


class ComplianceSummary(BaseModel):
    standard_name: str
    total_controls: int
    mapped_controls: int
    coverage_percent: float
