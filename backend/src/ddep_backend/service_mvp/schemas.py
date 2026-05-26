from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ddep_backend.diagnosis_engine.models import SubmittedAnswer
from ddep_backend.question_db.enums import AnswerType, Difficulty
from ddep_backend.result_report.models import ReportComparison, ResultReport
from ddep_backend.search_agent.models import RecommendationRun


class UserSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    display_name: str
    email: str | None = None


class AccessVerifyRequest(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    invite_code: str
    display_name: str = Field(min_length=1, max_length=120)
    email: str | None = None


class AccessVerifyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserSummary


class DiagnosisQuestionChoice(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    text: str


class DiagnosisQuestionPublic(BaseModel):
    model_config = ConfigDict(frozen=True)

    external_id: str
    domain: str
    difficulty: Difficulty
    answer_type: AnswerType
    prompt: str
    choices: list[DiagnosisQuestionChoice] = Field(default_factory=list)
    concept_tags: list[str] = Field(default_factory=list)
    prerequisite_tags: list[str] = Field(default_factory=list)


class DiagnosisSessionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    status: Literal["active", "completed"]
    answered_question_count: int
    question_count: int
    questions: list[DiagnosisQuestionPublic] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None


class SaveAnswerRequest(SubmittedAnswer):
    pass


class SaveAnswerResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    diagnosis_id: str
    question_external_id: str
    is_correct: bool
    answered_question_count: int


class CompleteDiagnosisResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    diagnosis: DiagnosisSessionResponse
    report: ResultReport
    recommendations: RecommendationRun


class OpsEventResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    event_type: str
    user_id: int | None
    diagnosis_id: int | None
    detail: dict[str, object]
    created_at: datetime


class ComparisonResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_diagnosis_id: str
    previous_diagnosis_id: str
    comparison: ReportComparison
