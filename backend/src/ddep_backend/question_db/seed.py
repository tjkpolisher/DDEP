from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ddep_backend.domains import DiagnosisDomain
from ddep_backend.question_db.enums import AnswerType, Difficulty, ReviewStatus, SourceType
from ddep_backend.question_db.grading import normalize_short_answer

TAG_SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class SeedValidationError(ValueError):
    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("\n".join(messages))


class ConceptTagSeed(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    slug: str
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    domain: DiagnosisDomain | None = None
    prerequisites: list[str] = Field(default_factory=list)

    @field_validator("slug")
    @classmethod
    def slug_must_be_lower_snake_ascii(cls, value: str) -> str:
        if not TAG_SLUG_RE.fullmatch(value):
            raise ValueError("must be lower snake_case ASCII")
        return value


class QuestionChoiceSeed(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    key: str = Field(min_length=1)
    text: str = Field(min_length=1)
    is_correct: bool


class QuestionSeed(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    external_id: str = Field(min_length=1)
    domain: DiagnosisDomain
    subdomain: str = Field(min_length=1)
    difficulty: Difficulty
    answer_type: AnswerType
    review_status: ReviewStatus
    source_type: SourceType
    source_title: str = Field(min_length=1)
    source_url: str | None = None
    source_reference: str = Field(min_length=1)
    concept_tags: list[str] = Field(min_length=1)
    prerequisites: list[str] = Field(default_factory=list)
    prompt: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    choices: list[QuestionChoiceSeed] = Field(default_factory=list)
    accepted_answers: list[str] = Field(default_factory=list)
    short_answer_case_sensitive: bool = False

    @field_validator("concept_tags", "prerequisites")
    @classmethod
    def tag_references_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("contains duplicate tag references")
        return value

    @model_validator(mode="after")
    def answer_shape_must_match_type(self) -> Self:
        correct_count = sum(1 for choice in self.choices if choice.is_correct)
        choice_keys = [choice.key for choice in self.choices]
        if len(choice_keys) != len(set(choice_keys)):
            raise ValueError(f"{self.external_id}: duplicate choice keys")

        if self.answer_type is AnswerType.SINGLE_CHOICE:
            if len(self.choices) < 2:
                raise ValueError(f"{self.external_id}: single_choice requires at least 2 choices")
            if correct_count != 1:
                raise ValueError(
                    f"{self.external_id}: single_choice requires exactly 1 correct choice"
                )
            if self.accepted_answers:
                raise ValueError(
                    f"{self.external_id}: single_choice must not define accepted_answers"
                )
        elif self.answer_type is AnswerType.MULTI_SELECT:
            if len(self.choices) < 3:
                raise ValueError(f"{self.external_id}: multi_select requires at least 3 choices")
            if correct_count < 2:
                raise ValueError(
                    f"{self.external_id}: multi_select requires at least 2 correct choices"
                )
            if self.accepted_answers:
                raise ValueError(
                    f"{self.external_id}: multi_select must not define accepted_answers"
                )
        elif self.answer_type is AnswerType.SHORT_ANSWER:
            if self.choices:
                raise ValueError(f"{self.external_id}: short_answer must not define choices")
            if not self.accepted_answers:
                raise ValueError(f"{self.external_id}: short_answer requires accepted_answers")
            normalized = [
                normalize_short_answer(
                    answer,
                    case_sensitive=self.short_answer_case_sensitive,
                )
                for answer in self.accepted_answers
            ]
            if any(not answer for answer in normalized):
                raise ValueError(
                    f"{self.external_id}: short_answer accepted_answers cannot be blank"
                )
            if len(normalized) != len(set(normalized)):
                raise ValueError(f"{self.external_id}: duplicate normalized accepted_answers")
        return self


class QuestionSeedManifest(BaseModel):
    concept_tags: list[ConceptTagSeed]
    questions: list[QuestionSeed]

    @classmethod
    def from_path(cls, path: Path) -> QuestionSeedManifest:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    def approved_questions(self) -> list[QuestionSeed]:
        return [
            question
            for question in self.questions
            if question.review_status is ReviewStatus.APPROVED
        ]


def load_seed_manifest(path: Path) -> QuestionSeedManifest:
    try:
        return QuestionSeedManifest.from_path(path)
    except json.JSONDecodeError as exc:
        raise SeedValidationError(
            [f"{path}: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"]
        ) from exc
    except ValidationError as exc:
        messages = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        raise SeedValidationError(messages) from exc


def validate_seed_manifest(
    manifest: QuestionSeedManifest,
    *,
    include_drafts: bool = False,
    enforce_distribution: bool = True,
) -> None:
    errors: list[str] = []
    tag_by_slug = {tag.slug: tag for tag in manifest.concept_tags}
    if len(tag_by_slug) != len(manifest.concept_tags):
        errors.append("concept_tags: duplicate tag slug")

    question_ids = [question.external_id for question in manifest.questions]
    duplicated_question_ids = sorted(_duplicates(question_ids))
    if duplicated_question_ids:
        errors.append(
            f"questions: duplicate external_id values: {', '.join(duplicated_question_ids)}"
        )

    for tag in manifest.concept_tags:
        for prerequisite in tag.prerequisites:
            if prerequisite not in tag_by_slug:
                errors.append(f"concept_tags.{tag.slug}: unknown prerequisite tag '{prerequisite}'")

    errors.extend(_detect_prerequisite_cycles(manifest.concept_tags))

    for question in manifest.questions:
        for slug in question.concept_tags:
            if slug not in tag_by_slug:
                errors.append(f"questions.{question.external_id}: unknown concept tag '{slug}'")
        for slug in question.prerequisites:
            if slug not in tag_by_slug:
                errors.append(
                    f"questions.{question.external_id}: unknown prerequisite tag '{slug}'"
                )
        if question.review_status is ReviewStatus.APPROVED and not question.prerequisites:
            errors.append(
                f"questions.{question.external_id}: approved questions require prerequisites"
            )
        if (
            not include_drafts
            and question.review_status is not ReviewStatus.APPROVED
            and not question.prerequisites
        ):
            errors.append(
                f"questions.{question.external_id}: "
                "empty draft prerequisites require --include-drafts",
            )

    if enforce_distribution:
        errors.extend(_validate_distribution(manifest.approved_questions()))

    if errors:
        raise SeedValidationError(errors)


def load_and_validate_seed(
    path: Path,
    *,
    include_drafts: bool = False,
    enforce_distribution: bool = True,
) -> QuestionSeedManifest:
    manifest = load_seed_manifest(path)
    validate_seed_manifest(
        manifest,
        include_drafts=include_drafts,
        enforce_distribution=enforce_distribution,
    )
    return manifest


def _duplicates(values: list[str]) -> set[str]:
    counts = Counter(values)
    return {value for value, count in counts.items() if count > 1}


def _detect_prerequisite_cycles(tags: list[ConceptTagSeed]) -> list[str]:
    graph = {tag.slug: tag.prerequisites for tag in tags}
    visited: set[str] = set()
    visiting: set[str] = set()
    errors: list[str] = []

    def visit(slug: str, path: list[str]) -> None:
        if slug in visiting:
            cycle_start = path.index(slug)
            cycle = " -> ".join([*path[cycle_start:], slug])
            errors.append(f"concept_tags: cyclic prerequisites detected: {cycle}")
            return
        if slug in visited:
            return
        visiting.add(slug)
        for prerequisite in graph.get(slug, []):
            if prerequisite in graph:
                visit(prerequisite, [*path, prerequisite])
        visiting.remove(slug)
        visited.add(slug)

    for tag in tags:
        visit(tag.slug, [tag.slug])

    return errors


def _validate_distribution(approved_questions: list[QuestionSeed]) -> list[str]:
    errors: list[str] = []
    domain_values = [domain.value for domain in DiagnosisDomain]
    counts_by_domain: dict[str, int] = {domain: 0 for domain in domain_values}
    by_domain: dict[str, list[QuestionSeed]] = defaultdict(list)
    for question in approved_questions:
        counts_by_domain[question.domain.value] += 1
        by_domain[question.domain.value].append(question)

    total = len(approved_questions)
    if total == 30:
        for domain, count in counts_by_domain.items():
            if count != 5:
                errors.append(
                    f"questions: expected 5 approved questions for {domain}, found {count}"
                )
    elif total > 0:
        spread = max(counts_by_domain.values()) - min(counts_by_domain.values())
        if spread > 1:
            errors.append(
                f"questions: approved domain distribution spread must be <= 1, found {spread}"
            )

    for domain in domain_values:
        questions = by_domain[domain]
        if not questions:
            errors.append(f"questions: missing approved questions for domain {domain}")
            continue
        answer_counts = Counter(question.answer_type for question in questions)
        difficulty_counts = Counter(question.difficulty for question in questions)
        objective_count = (
            answer_counts[AnswerType.SINGLE_CHOICE] + answer_counts[AnswerType.MULTI_SELECT]
        )
        if objective_count < 3:
            errors.append(f"questions.{domain}: expected at least 3 objective questions")
        if answer_counts[AnswerType.SHORT_ANSWER] < 1:
            errors.append(f"questions.{domain}: expected at least 1 short_answer question")
        if difficulty_counts[Difficulty.EASY] < 1:
            errors.append(f"questions.{domain}: expected at least 1 easy question")
        if difficulty_counts[Difficulty.MEDIUM] < 2:
            errors.append(f"questions.{domain}: expected at least 2 medium questions")
        if difficulty_counts[Difficulty.HARD] < 1:
            errors.append(f"questions.{domain}: expected at least 1 hard question")
    return errors
