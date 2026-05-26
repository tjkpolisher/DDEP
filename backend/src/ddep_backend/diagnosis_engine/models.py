from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ddep_backend.domains import DiagnosisDomain
from ddep_backend.question_db.enums import AnswerType, Difficulty, ReviewStatus


class DiagnosisScoringConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    algorithm_version: str = "bayes-lite-v1"
    alpha: float = 1.0
    beta: float = 1.0
    difficulty_weights: dict[Difficulty, float] = Field(
        default_factory=lambda: {
            Difficulty.EASY: 0.8,
            Difficulty.MEDIUM: 1.0,
            Difficulty.HARD: 1.2,
        }
    )
    weak_threshold: int = 60
    min_weak_evidence_weight: float = 1.0
    full_confidence_evidence_weight: float = 3.0


class EngineChoice(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    key: str
    text: str
    is_correct: bool = False


class EngineQuestion(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    external_id: str
    domain: DiagnosisDomain
    difficulty: Difficulty
    answer_type: AnswerType
    review_status: ReviewStatus = ReviewStatus.APPROVED
    concept_tags: list[str] = Field(min_length=1)
    prerequisite_tags: list[str] = Field(default_factory=list)
    choices: list[EngineChoice] = Field(default_factory=list)
    accepted_answers: list[str] = Field(default_factory=list)
    short_answer_case_sensitive: bool = False

    @property
    def correct_choice_keys(self) -> list[str]:
        return [choice.key for choice in self.choices if choice.is_correct]


class SubmittedAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    question_external_id: str
    choice_keys: list[str] = Field(default_factory=list)
    short_answer: str | None = None


class QuestionOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_external_id: str
    domain: DiagnosisDomain
    difficulty: Difficulty
    concept_tags: list[str]
    prerequisite_tags: list[str]
    is_correct: bool
    evidence_weight: float
    submitted_choice_keys: list[str] = Field(default_factory=list)
    submitted_short_answer: str | None = None
    correct_choice_keys: list[str] = Field(default_factory=list)


class DiagnosisSessionState(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["active", "completed"] = "active"
    answered_question_ids: list[str] = Field(default_factory=list)
    outcomes: dict[str, QuestionOutcome] = Field(default_factory=dict)
    last_outcome: QuestionOutcome | None = None
    consecutive_correct_by_domain: dict[str, int] = Field(default_factory=dict)
    consecutive_correct_by_concept: dict[str, int] = Field(default_factory=dict)


class DomainScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    domain: DiagnosisDomain
    score: int
    confidence: float
    evidence_weight: float
    weighted_correct: float
    weighted_attempts: float
    attempted_questions: int


class ConceptMastery(BaseModel):
    model_config = ConfigDict(frozen=True)

    concept_slug: str
    score: int
    confidence: float
    evidence_weight: float
    weighted_correct: float
    weighted_attempts: float
    attempted_questions: int


class WeakConcept(BaseModel):
    model_config = ConfigDict(frozen=True)

    concept_slug: str
    score: int
    confidence: float
    evidence_weight: float
    prerequisite_chain: list[str]
    domain: DiagnosisDomain | None = None


class DiagnosisResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    algorithm_version: str
    status: Literal["active", "completed"]
    answered_question_count: int
    domain_scores: list[DomainScore]
    concept_mastery: list[ConceptMastery]
    weak_concepts: list[WeakConcept]
