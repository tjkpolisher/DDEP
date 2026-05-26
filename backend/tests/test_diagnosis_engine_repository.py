import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from ddep_backend.core.config import get_settings
from ddep_backend.db.base import Base
from ddep_backend.diagnosis_engine import (
    DiagnosisSessionState,
    SubmittedAnswer,
    apply_outcome,
    calculate_result,
    grade_submitted_answer,
)
from ddep_backend.diagnosis_engine.repository import (
    load_approved_engine_questions,
    load_concept_prerequisite_graph,
)
from ddep_backend.domains import DiagnosisDomain
from ddep_backend.question_db.enums import AnswerType, Difficulty, ReviewStatus, SourceType
from ddep_backend.question_db.importer import import_seed_manifest
from ddep_backend.question_db.models import (
    ConceptTag,
    ConceptTagPrerequisite,
    Question,
    QuestionChoice,
    QuestionConceptTag,
    QuestionPrerequisiteTag,
)
from ddep_backend.question_db.seed import QuestionSeedManifest, load_and_validate_seed

SEED_PATH = Path("seeds/phase01_questions.json")


def test_repository_maps_approved_question_rows_to_engine_dtos() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            with session.begin():
                _insert_repository_fixture(session)

            questions = load_approved_engine_questions(session)
            graph = load_concept_prerequisite_graph(session)
    finally:
        engine.dispose()

    assert [question.external_id for question in questions] == ["approved-choice", "approved-short"]
    choice_question = questions[0]
    assert choice_question.domain is DiagnosisDomain.AIRFRAME_AERODYNAMICS
    assert choice_question.difficulty is Difficulty.MEDIUM
    assert choice_question.answer_type is AnswerType.SINGLE_CHOICE
    assert [choice.key for choice in choice_question.choices] == ["A", "B"]
    assert choice_question.correct_choice_keys == ["A"]
    assert choice_question.concept_tags == ["lift", "shared"]
    assert choice_question.prerequisite_tags == ["base"]
    assert questions[1].accepted_answers == ["mavlink"]
    assert graph["lift"] == ["base"]
    assert graph["shared"] == ["base"]


@pytest.mark.skipif(
    "DDEP_TEST_DATABASE_URL" not in os.environ,
    reason="DDEP_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)
def test_seed_import_adapter_and_engine_run_against_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_url = os.environ["DDEP_TEST_DATABASE_URL"]
    database_name = make_url(database_url).database
    if database_name == "ddep":
        pytest.fail("DDEP_TEST_DATABASE_URL must not point at the normal ddep database")

    monkeypatch.setenv("DDEP_DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        _upgrade_database()
        manifest = load_and_validate_seed(SEED_PATH)
        engine = create_engine(database_url, pool_pre_ping=True)
        try:
            first_external_ids = _import_load_and_score(engine, manifest)
            second_external_ids = _import_load_and_score(engine, manifest)
        finally:
            engine.dispose()
    finally:
        get_settings.cache_clear()

    assert first_external_ids == second_external_ids
    assert len(first_external_ids) == 30


def _insert_repository_fixture(session: Session) -> None:
    base = ConceptTag(slug="base", label="Base", description="Base")
    lift = ConceptTag(
        slug="lift",
        label="Lift",
        description="Lift",
        domain=DiagnosisDomain.AIRFRAME_AERODYNAMICS.value,
    )
    shared = ConceptTag(slug="shared", label="Shared", description="Shared")
    session.add_all([base, lift, shared])
    session.flush()
    session.add_all(
        [
            ConceptTagPrerequisite(concept_tag_id=lift.id, prerequisite_tag_id=base.id),
            ConceptTagPrerequisite(concept_tag_id=shared.id, prerequisite_tag_id=base.id),
        ]
    )

    approved_choice = _question_row(
        "approved-choice",
        DiagnosisDomain.AIRFRAME_AERODYNAMICS,
        Difficulty.MEDIUM,
        AnswerType.SINGLE_CHOICE,
        ReviewStatus.APPROVED,
    )
    approved_short = _question_row(
        "approved-short",
        DiagnosisDomain.SOFTWARE,
        Difficulty.EASY,
        AnswerType.SHORT_ANSWER,
        ReviewStatus.APPROVED,
        accepted_answers=["mavlink"],
    )
    draft = _question_row(
        "draft",
        DiagnosisDomain.SOFTWARE,
        Difficulty.EASY,
        AnswerType.SINGLE_CHOICE,
        ReviewStatus.DRAFT,
    )
    session.add_all([approved_choice, approved_short, draft])
    session.flush()

    session.add_all(
        [
            QuestionChoice(
                question_id=approved_choice.id,
                choice_key="A",
                text="Correct",
                is_correct=True,
                sort_order=0,
            ),
            QuestionChoice(
                question_id=approved_choice.id,
                choice_key="B",
                text="Wrong",
                is_correct=False,
                sort_order=1,
            ),
            QuestionConceptTag(question_id=approved_choice.id, concept_tag_id=shared.id),
            QuestionConceptTag(question_id=approved_choice.id, concept_tag_id=lift.id),
            QuestionPrerequisiteTag(question_id=approved_choice.id, concept_tag_id=base.id),
            QuestionConceptTag(question_id=approved_short.id, concept_tag_id=shared.id),
            QuestionPrerequisiteTag(question_id=approved_short.id, concept_tag_id=base.id),
            QuestionConceptTag(question_id=draft.id, concept_tag_id=shared.id),
        ]
    )


def _question_row(
    external_id: str,
    domain: DiagnosisDomain,
    difficulty: Difficulty,
    answer_type: AnswerType,
    review_status: ReviewStatus,
    *,
    accepted_answers: list[str] | None = None,
) -> Question:
    return Question(
        external_id=external_id,
        domain=domain.value,
        subdomain="Fixture",
        difficulty=difficulty.value,
        answer_type=answer_type.value,
        review_status=review_status.value,
        source_type=SourceType.INTERNAL_NOTE.value,
        source_title="Fixture",
        source_reference="Fixture",
        prompt="Prompt",
        explanation="Explanation",
        accepted_answers=accepted_answers,
        short_answer_case_sensitive=False,
    )


def _upgrade_database() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")


def _import_load_and_score(engine: Engine, manifest: QuestionSeedManifest) -> list[str]:
    with Session(engine) as session:
        with session.begin():
            import_seed_manifest(session, manifest)

        questions = load_approved_engine_questions(session)
        graph = load_concept_prerequisite_graph(session)

        assert len(questions) == 30
        assert {question.domain for question in questions} == set(DiagnosisDomain)
        assert any(len(question.concept_tags) > 1 for question in questions)
        assert any(question.answer_type is AnswerType.SHORT_ANSWER for question in questions)
        assert any(question.choices for question in questions)
        assert any(graph.values())

        state = DiagnosisSessionState()
        for domain in DiagnosisDomain:
            question = next(item for item in questions if item.domain is domain)
            answer = _correct_answer_for(question.external_id, session)
            state = apply_outcome(state, grade_submitted_answer(question, answer))

        result = calculate_result(questions, state, graph)
        assert result.answered_question_count == 6
        assert {score.domain for score in result.domain_scores} == set(DiagnosisDomain)
        return [question.external_id for question in questions]


def _correct_answer_for(question_external_id: str, session: Session) -> SubmittedAnswer:
    question = session.scalar(select(Question).where(Question.external_id == question_external_id))
    assert question is not None
    if question.answer_type == AnswerType.SHORT_ANSWER.value:
        assert question.accepted_answers
        return SubmittedAnswer(
            question_external_id=question_external_id,
            short_answer=question.accepted_answers[0],
        )
    choice_keys = [
        choice.choice_key
        for choice in sorted(question.choices, key=lambda item: item.sort_order)
        if choice.is_correct
    ]
    return SubmittedAnswer(question_external_id=question_external_id, choice_keys=choice_keys)
