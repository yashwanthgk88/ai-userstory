from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class AbuseCase(BaseModel):
    id: str
    threat: str
    actor: str
    description: str
    impact: str
    likelihood: str
    attack_vector: str
    stride_category: str


class StrideThreat(BaseModel):
    category: str
    threat: str
    description: str
    risk_level: str


class SecurityRequirement(BaseModel):
    id: str
    text: str
    priority: str
    category: str
    details: str


class AnalysisResponse(BaseModel):
    id: UUID
    user_story_id: UUID
    version: int
    abuse_cases: list[AbuseCase]
    stride_threats: list[StrideThreat]
    security_requirements: list[SecurityRequirement]
    risk_score: int
    ai_model_used: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisSummary(BaseModel):
    id: UUID
    version: int
    risk_score: int
    abuse_case_count: int
    requirement_count: int
    ai_model_used: str | None
    created_at: datetime
