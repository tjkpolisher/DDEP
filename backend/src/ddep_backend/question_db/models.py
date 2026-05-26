from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ddep_backend.db.base import Base
from ddep_backend.domains import DiagnosisDomain
from ddep_backend.question_db.enums import AnswerType, Difficulty, ReviewStatus, SourceType


def _values(
    enum_type: type[Difficulty]
    | type[AnswerType]
    | type[ReviewStatus]
    | type[SourceType]
    | type[DiagnosisDomain],
) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_type)


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(f"domain IN ({_values(DiagnosisDomain)})", name="ck_questions_domain"),
        CheckConstraint(f"difficulty IN ({_values(Difficulty)})", name="ck_questions_difficulty"),
        CheckConstraint(f"answer_type IN ({_values(AnswerType)})", name="ck_questions_answer_type"),
        CheckConstraint(
            f"review_status IN ({_values(ReviewStatus)})",
            name="ck_questions_review_status",
        ),
        CheckConstraint(f"source_type IN ({_values(SourceType)})", name="ck_questions_source_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subdomain: Mapped[str] = mapped_column(String(120), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), nullable=False)
    answer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    accepted_answers: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    short_answer_case_sensitive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    choices: Mapped[list["QuestionChoice"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionChoice.sort_order",
    )
    concept_tags: Mapped[list["QuestionConceptTag"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )
    prerequisite_tags: Mapped[list["QuestionPrerequisiteTag"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class QuestionChoice(Base):
    __tablename__ = "question_choices"
    __table_args__ = (
        UniqueConstraint("question_id", "choice_key", name="uq_question_choices_question_key"),
        UniqueConstraint("question_id", "sort_order", name="uq_question_choices_question_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    choice_key: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)

    question: Mapped[Question] = relationship(back_populates="choices")


class ConceptTag(Base):
    __tablename__ = "concept_tags"
    __table_args__ = (
        CheckConstraint(
            "domain IS NULL OR domain IN (" + _values(DiagnosisDomain) + ")",
            name="ck_concept_tags_domain",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    question_links: Mapped[list["QuestionConceptTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        foreign_keys="QuestionConceptTag.concept_tag_id",
    )
    prerequisite_for_questions: Mapped[list["QuestionPrerequisiteTag"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        foreign_keys="QuestionPrerequisiteTag.concept_tag_id",
    )
    prerequisite_links: Mapped[list["ConceptTagPrerequisite"]] = relationship(
        back_populates="tag",
        cascade="all, delete-orphan",
        foreign_keys="ConceptTagPrerequisite.concept_tag_id",
    )


class QuestionConceptTag(Base):
    __tablename__ = "question_concept_tags"
    __table_args__ = (
        UniqueConstraint("question_id", "concept_tag_id", name="uq_question_concept_tags_pair"),
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    concept_tag_id: Mapped[int] = mapped_column(
        ForeignKey("concept_tags.id", ondelete="CASCADE"), primary_key=True
    )

    question: Mapped[Question] = relationship(back_populates="concept_tags")
    tag: Mapped[ConceptTag] = relationship(back_populates="question_links")


class QuestionPrerequisiteTag(Base):
    __tablename__ = "question_prerequisite_tags"
    __table_args__ = (
        UniqueConstraint(
            "question_id", "concept_tag_id", name="uq_question_prerequisite_tags_pair"
        ),
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    concept_tag_id: Mapped[int] = mapped_column(
        ForeignKey("concept_tags.id", ondelete="CASCADE"), primary_key=True
    )

    question: Mapped[Question] = relationship(back_populates="prerequisite_tags")
    tag: Mapped[ConceptTag] = relationship(back_populates="prerequisite_for_questions")


class ConceptTagPrerequisite(Base):
    __tablename__ = "concept_tag_prerequisites"
    __table_args__ = (
        UniqueConstraint(
            "concept_tag_id", "prerequisite_tag_id", name="uq_concept_tag_prerequisites_pair"
        ),
        CheckConstraint(
            "concept_tag_id <> prerequisite_tag_id", name="ck_concept_tag_prerequisites_not_self"
        ),
    )

    concept_tag_id: Mapped[int] = mapped_column(
        ForeignKey("concept_tags.id", ondelete="CASCADE"), primary_key=True
    )
    prerequisite_tag_id: Mapped[int] = mapped_column(
        ForeignKey("concept_tags.id", ondelete="CASCADE"), primary_key=True
    )

    tag: Mapped[ConceptTag] = relationship(
        back_populates="prerequisite_links",
        foreign_keys=[concept_tag_id],
    )
    prerequisite_tag: Mapped[ConceptTag] = relationship(foreign_keys=[prerequisite_tag_id])
