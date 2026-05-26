from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ddep_backend.diagnosis_engine.models import EngineChoice, EngineQuestion
from ddep_backend.domains import DiagnosisDomain
from ddep_backend.question_db.enums import AnswerType, Difficulty, ReviewStatus
from ddep_backend.question_db.models import (
    ConceptTag,
    ConceptTagPrerequisite,
    Question,
    QuestionConceptTag,
    QuestionPrerequisiteTag,
)


def load_approved_engine_questions(session: Session) -> list[EngineQuestion]:
    questions = session.scalars(
        select(Question)
        .where(Question.review_status == ReviewStatus.APPROVED.value)
        .options(
            selectinload(Question.choices),
            selectinload(Question.concept_tags).selectinload(QuestionConceptTag.tag),
            selectinload(Question.prerequisite_tags).selectinload(QuestionPrerequisiteTag.tag),
        )
        .order_by(Question.external_id)
    ).all()
    return [_to_engine_question(question) for question in questions]


def load_concept_prerequisite_graph(session: Session) -> dict[str, list[str]]:
    tags = session.scalars(
        select(ConceptTag)
        .options(
            selectinload(ConceptTag.prerequisite_links).selectinload(
                ConceptTagPrerequisite.prerequisite_tag
            )
        )
        .order_by(ConceptTag.slug)
    ).all()
    return {
        tag.slug: sorted(link.prerequisite_tag.slug for link in tag.prerequisite_links)
        for tag in tags
    }


def _to_engine_question(question: Question) -> EngineQuestion:
    return EngineQuestion(
        external_id=question.external_id,
        domain=DiagnosisDomain(question.domain),
        difficulty=Difficulty(question.difficulty),
        answer_type=AnswerType(question.answer_type),
        review_status=ReviewStatus(question.review_status),
        concept_tags=sorted(link.tag.slug for link in question.concept_tags),
        prerequisite_tags=sorted(link.tag.slug for link in question.prerequisite_tags),
        choices=[
            EngineChoice(
                key=choice.choice_key,
                text=choice.text,
                is_correct=choice.is_correct,
            )
            for choice in question.choices
        ],
        accepted_answers=question.accepted_answers or [],
        short_answer_case_sensitive=question.short_answer_case_sensitive,
    )
