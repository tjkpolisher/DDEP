from collections import Counter
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ddep_backend.question_db.enums import ReviewStatus
from ddep_backend.question_db.models import (
    ConceptTag,
    ConceptTagPrerequisite,
    Question,
    QuestionChoice,
    QuestionConceptTag,
    QuestionPrerequisiteTag,
)
from ddep_backend.question_db.seed import QuestionSeedManifest


@dataclass(frozen=True)
class ImportSummary:
    questions: int
    choices: int
    concept_tags: int
    question_concept_tags: int
    question_prerequisite_tags: int
    concept_tag_prerequisites: int


def import_seed_manifest(
    session: Session,
    manifest: QuestionSeedManifest,
    *,
    include_drafts: bool = False,
) -> ImportSummary:
    tag_models = _upsert_tags(session, manifest)
    _sync_concept_prerequisites(session, manifest, tag_models)

    questions = [
        question
        for question in manifest.questions
        if include_drafts or question.review_status is ReviewStatus.APPROVED
    ]
    totals: Counter[str] = Counter()
    for question_seed in questions:
        question = _upsert_question(session, question_seed.model_dump(mode="json"))
        session.flush()
        _replace_question_children(session, question.id)

        for index, choice in enumerate(question_seed.choices):
            session.add(
                QuestionChoice(
                    question_id=question.id,
                    choice_key=choice.key,
                    text=choice.text,
                    is_correct=choice.is_correct,
                    sort_order=index,
                )
            )
            totals["choices"] += 1

        for slug in question_seed.concept_tags:
            session.add(
                QuestionConceptTag(question_id=question.id, concept_tag_id=tag_models[slug].id)
            )
            totals["question_concept_tags"] += 1

        for slug in question_seed.prerequisites:
            session.add(
                QuestionPrerequisiteTag(question_id=question.id, concept_tag_id=tag_models[slug].id)
            )
            totals["question_prerequisite_tags"] += 1

    totals["questions"] = len(questions)
    totals["concept_tags"] = len(tag_models)
    totals["concept_tag_prerequisites"] = sum(
        len(tag.prerequisites) for tag in manifest.concept_tags
    )
    return ImportSummary(
        questions=totals["questions"],
        choices=totals["choices"],
        concept_tags=totals["concept_tags"],
        question_concept_tags=totals["question_concept_tags"],
        question_prerequisite_tags=totals["question_prerequisite_tags"],
        concept_tag_prerequisites=totals["concept_tag_prerequisites"],
    )


def _upsert_tags(session: Session, manifest: QuestionSeedManifest) -> dict[str, ConceptTag]:
    tag_models: dict[str, ConceptTag] = {}
    for tag_seed in manifest.concept_tags:
        tag = session.scalar(select(ConceptTag).where(ConceptTag.slug == tag_seed.slug))
        if tag is None:
            tag = ConceptTag(slug=tag_seed.slug)
            session.add(tag)
        tag.label = tag_seed.label
        tag.description = tag_seed.description
        tag.domain = tag_seed.domain.value if tag_seed.domain is not None else None
        tag_models[tag_seed.slug] = tag
    session.flush()
    return tag_models


def _sync_concept_prerequisites(
    session: Session,
    manifest: QuestionSeedManifest,
    tag_models: dict[str, ConceptTag],
) -> None:
    seed_tag_ids = [tag_models[tag.slug].id for tag in manifest.concept_tags]
    session.execute(
        delete(ConceptTagPrerequisite).where(
            ConceptTagPrerequisite.concept_tag_id.in_(seed_tag_ids),
        )
    )
    for tag_seed in manifest.concept_tags:
        tag = tag_models[tag_seed.slug]
        for prerequisite_slug in tag_seed.prerequisites:
            session.add(
                ConceptTagPrerequisite(
                    concept_tag_id=tag.id,
                    prerequisite_tag_id=tag_models[prerequisite_slug].id,
                )
            )


def _upsert_question(session: Session, data: dict[str, object]) -> Question:
    external_id = str(data["external_id"])
    question = session.scalar(select(Question).where(Question.external_id == external_id))
    if question is None:
        question = Question(external_id=external_id)
        session.add(question)

    question.domain = str(data["domain"])
    question.subdomain = str(data["subdomain"])
    question.difficulty = str(data["difficulty"])
    question.answer_type = str(data["answer_type"])
    question.review_status = str(data["review_status"])
    question.source_type = str(data["source_type"])
    question.source_title = str(data["source_title"])
    question.source_url = data["source_url"] if isinstance(data["source_url"], str) else None
    question.source_reference = str(data["source_reference"])
    question.prompt = str(data["prompt"])
    question.explanation = str(data["explanation"])
    question.accepted_answers = (
        list(data["accepted_answers"])
        if isinstance(data["accepted_answers"], list) and data["accepted_answers"]
        else None
    )
    question.short_answer_case_sensitive = bool(data["short_answer_case_sensitive"])
    return question


def _replace_question_children(session: Session, question_id: int) -> None:
    session.execute(delete(QuestionChoice).where(QuestionChoice.question_id == question_id))
    session.execute(delete(QuestionConceptTag).where(QuestionConceptTag.question_id == question_id))
    session.execute(
        delete(QuestionPrerequisiteTag).where(QuestionPrerequisiteTag.question_id == question_id)
    )
