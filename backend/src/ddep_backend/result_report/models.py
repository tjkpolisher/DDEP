from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ddep_backend.domains import DiagnosisDomain

DomainReadiness = Literal["strong", "developing", "weak", "unmeasured"]


class ReportSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    algorithm_version: str
    status: Literal["active", "completed"]
    answered_question_count: int
    average_domain_score: int
    weakest_domain: DiagnosisDomain | None = None
    strongest_domain: DiagnosisDomain | None = None


class DomainReportProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: DiagnosisDomain
    score: int
    confidence: float
    evidence_weight: float
    attempted_questions: int
    readiness: DomainReadiness
    uncertainty: str
    weak_concept_count: int
    weak_concept_tags: list[str] = Field(default_factory=list)


class StrengthWeaknessSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    strength_domains: list[DiagnosisDomain] = Field(default_factory=list)
    weakness_domains: list[DiagnosisDomain] = Field(default_factory=list)
    weak_concept_tags: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)


class RoadmapItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    order: int
    concept_slug: str
    domain: DiagnosisDomain | None = None
    prerequisite_chain: list[str] = Field(default_factory=list)
    reason: str
    priority_score: int


class RetestTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: DiagnosisDomain
    concept_slug: str | None = None
    reason: str
    priority: int


class DomainScoreDelta(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: DiagnosisDomain
    previous_score: int
    current_score: int
    delta: int
    previous_confidence: float
    current_confidence: float


class ReportComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain_deltas: list[DomainScoreDelta]
    resolved_weak_concepts: list[str] = Field(default_factory=list)
    new_weak_concepts: list[str] = Field(default_factory=list)


class ResultReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot: ReportSnapshot
    domain_profiles: list[DomainReportProfile]
    strength_weakness: StrengthWeaknessSummary
    roadmap: list[RoadmapItem]
    retest_targets: list[RetestTarget]
    comparison: ReportComparison | None = None
