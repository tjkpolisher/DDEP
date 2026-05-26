from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ddep_backend.domains import DiagnosisDomain

ResourceSourceType = Literal[
    "official_docs",
    "open_course",
    "paper",
    "technical_blog",
    "community_reference",
]
ResourceDifficulty = Literal["intro", "intermediate", "advanced"]
FallbackReason = Literal[
    "insufficient_verified_results",
    "low_trust_results_filtered",
    "no_direct_concept_match",
]


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    weak_concept_tags: list[str] = Field(default_factory=list)
    prerequisite_tags: list[str] = Field(default_factory=list)
    target_domains: list[DiagnosisDomain] = Field(default_factory=list)
    learner_level: ResourceDifficulty = "intermediate"
    min_results: int = Field(default=3, ge=1, le=7)
    max_results: int = Field(default=7, ge=3, le=7)


class LearningResourceCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    title: str
    url: str
    source_name: str
    source_type: ResourceSourceType
    difficulty: ResourceDifficulty
    concept_tags: list[str] = Field(default_factory=list)
    prerequisite_tags: list[str] = Field(default_factory=list)
    summary: str
    trust_score: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    practice_score: float = Field(ge=0, le=1)
    published_on: date | None = None
    is_verified: bool = False


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    trust: float
    level_fit: float
    freshness: float
    practice: float
    dedupe: float
    total: float


class LearningRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    url: str
    source_name: str
    source_type: ResourceSourceType
    difficulty: ResourceDifficulty
    trust_score: float
    recommendation_reason: str
    prerequisite_tags: list[str] = Field(default_factory=list)
    concept_tags: list[str] = Field(default_factory=list)
    score: ScoreBreakdown


class RecommendationRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_terms: list[str]
    recommendations: list[LearningRecommendation]
    fallback_reasons: list[FallbackReason] = Field(default_factory=list)
    candidate_count: int
    verified_candidate_count: int
