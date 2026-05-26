"""Create Phase 01 question database tables.

Revision ID: 20260526_0326
Revises:
Create Date: 2026-05-26 03:26:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260526_0326"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DOMAIN_VALUES = (
    "airframe_aerodynamics",
    "electronics_hardware",
    "control",
    "software",
    "autonomous_ai",
    "fabrication_operations",
)
DIFFICULTY_VALUES = ("easy", "medium", "hard")
ANSWER_TYPE_VALUES = ("single_choice", "multi_select", "short_answer")
REVIEW_STATUS_VALUES = ("draft", "in_review", "approved", "deprecated")
SOURCE_TYPE_VALUES = (
    "official_docs",
    "technical_manual",
    "course_material",
    "paper",
    "internal_note",
    "expert_review",
)


def upgrade() -> None:
    op.create_table(
        "concept_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            _in_or_null("domain", DOMAIN_VALUES),
            name="ck_concept_tags_domain",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_concept_tags_domain"), "concept_tags", ["domain"], unique=False)
    op.create_index(op.f("ix_concept_tags_slug"), "concept_tags", ["slug"], unique=True)

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("subdomain", sa.String(length=120), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("answer_type", sa.String(length=32), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_title", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("accepted_answers", sa.JSON(), nullable=True),
        sa.Column("short_answer_case_sensitive", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(_in("domain", DOMAIN_VALUES), name="ck_questions_domain"),
        sa.CheckConstraint(_in("difficulty", DIFFICULTY_VALUES), name="ck_questions_difficulty"),
        sa.CheckConstraint(_in("answer_type", ANSWER_TYPE_VALUES), name="ck_questions_answer_type"),
        sa.CheckConstraint(
            _in("review_status", REVIEW_STATUS_VALUES), name="ck_questions_review_status"
        ),
        sa.CheckConstraint(_in("source_type", SOURCE_TYPE_VALUES), name="ck_questions_source_type"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index(op.f("ix_questions_domain"), "questions", ["domain"], unique=False)
    op.create_index(op.f("ix_questions_external_id"), "questions", ["external_id"], unique=True)
    op.create_index(
        op.f("ix_questions_review_status"), "questions", ["review_status"], unique=False
    )

    op.create_table(
        "concept_tag_prerequisites",
        sa.Column("concept_tag_id", sa.Integer(), nullable=False),
        sa.Column("prerequisite_tag_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "concept_tag_id <> prerequisite_tag_id",
            name="ck_concept_tag_prerequisites_not_self",
        ),
        sa.ForeignKeyConstraint(["concept_tag_id"], ["concept_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prerequisite_tag_id"], ["concept_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("concept_tag_id", "prerequisite_tag_id"),
        sa.UniqueConstraint(
            "concept_tag_id",
            "prerequisite_tag_id",
            name="uq_concept_tag_prerequisites_pair",
        ),
    )
    op.create_table(
        "question_choices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("choice_key", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "choice_key", name="uq_question_choices_question_key"),
        sa.UniqueConstraint("question_id", "sort_order", name="uq_question_choices_question_order"),
    )
    op.create_index(
        op.f("ix_question_choices_question_id"), "question_choices", ["question_id"], unique=False
    )
    op.create_table(
        "question_concept_tags",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("concept_tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["concept_tag_id"], ["concept_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id", "concept_tag_id"),
        sa.UniqueConstraint("question_id", "concept_tag_id", name="uq_question_concept_tags_pair"),
    )
    op.create_table(
        "question_prerequisite_tags",
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("concept_tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["concept_tag_id"], ["concept_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("question_id", "concept_tag_id"),
        sa.UniqueConstraint(
            "question_id", "concept_tag_id", name="uq_question_prerequisite_tags_pair"
        ),
    )


def downgrade() -> None:
    op.drop_table("question_prerequisite_tags")
    op.drop_table("question_concept_tags")
    op.drop_index(op.f("ix_question_choices_question_id"), table_name="question_choices")
    op.drop_table("question_choices")
    op.drop_table("concept_tag_prerequisites")
    op.drop_index(op.f("ix_questions_review_status"), table_name="questions")
    op.drop_index(op.f("ix_questions_external_id"), table_name="questions")
    op.drop_index(op.f("ix_questions_domain"), table_name="questions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_concept_tags_slug"), table_name="concept_tags")
    op.drop_index(op.f("ix_concept_tags_domain"), table_name="concept_tags")
    op.drop_table("concept_tags")


def _in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


def _in_or_null(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IS NULL OR {_in(column, values)}"
