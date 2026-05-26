"""Create Phase 05 service MVP tables.

Revision ID: 20260526_1050
Revises: 20260526_0326
Create Date: 2026-05-26 10:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260526_1050"
down_revision: str | None = "20260526_0326"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "internal_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_internal_users_email"), "internal_users", ["email"], unique=True)

    op.create_table(
        "invite_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invite_codes_code_hash"), "invite_codes", ["code_hash"], unique=True)

    op.create_table(
        "access_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["internal_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_access_sessions_token_hash"), "access_sessions", ["token_hash"], unique=True
    )
    op.create_index(
        op.f("ix_access_sessions_user_id"), "access_sessions", ["user_id"], unique=False
    )

    op.create_table(
        "diagnosis_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("question_external_ids", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'completed')", name="ck_diagnosis_sessions_status"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["internal_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index(
        op.f("ix_diagnosis_sessions_public_id"), "diagnosis_sessions", ["public_id"], unique=True
    )
    op.create_index(
        op.f("ix_diagnosis_sessions_user_id"), "diagnosis_sessions", ["user_id"], unique=False
    )

    op.create_table(
        "diagnosis_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), nullable=False),
        sa.Column("question_external_id", sa.String(length=120), nullable=False),
        sa.Column("choice_keys", sa.JSON(), nullable=False),
        sa.Column("short_answer", sa.Text(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnosis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "diagnosis_id",
            "question_external_id",
            name="uq_diagnosis_answers_diagnosis_question",
        ),
    )
    op.create_index(
        op.f("ix_diagnosis_answers_diagnosis_id"),
        "diagnosis_answers",
        ["diagnosis_id"],
        unique=False,
    )

    op.create_table(
        "diagnosis_outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), nullable=False),
        sa.Column("question_external_id", sa.String(length=120), nullable=False),
        sa.Column("outcome_json", sa.JSON(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnosis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "diagnosis_id",
            "question_external_id",
            name="uq_diagnosis_outcomes_diagnosis_question",
        ),
    )
    op.create_index(
        op.f("ix_diagnosis_outcomes_diagnosis_id"),
        "diagnosis_outcomes",
        ["diagnosis_id"],
        unique=False,
    )

    op.create_table(
        "result_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnosis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_result_snapshots_diagnosis_id"), "result_snapshots", ["diagnosis_id"], unique=True
    )

    op.create_table(
        "recommendation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("diagnosis_id", sa.Integer(), nullable=False),
        sa.Column("request_json", sa.JSON(), nullable=False),
        sa.Column("run_json", sa.JSON(), nullable=False),
        sa.Column("fallback_reasons", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnosis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_recommendation_runs_diagnosis_id"),
        "recommendation_runs",
        ["diagnosis_id"],
        unique=True,
    )

    op.create_table(
        "ops_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("diagnosis_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("detail_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["diagnosis_id"], ["diagnosis_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["internal_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ops_events_diagnosis_id"), "ops_events", ["diagnosis_id"], unique=False
    )
    op.create_index(op.f("ix_ops_events_event_type"), "ops_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_ops_events_user_id"), "ops_events", ["user_id"], unique=False)

    op.create_table(
        "recommendation_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("trust_score", sa.Float(), nullable=False),
        sa.Column("recommendation_reason", sa.Text(), nullable=False),
        sa.Column("score_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["recommendation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sort_order", name="uq_recommendation_items_run_order"),
    )
    op.create_index(
        op.f("ix_recommendation_items_run_id"), "recommendation_items", ["run_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_recommendation_items_run_id"), table_name="recommendation_items")
    op.drop_table("recommendation_items")
    op.drop_index(op.f("ix_ops_events_user_id"), table_name="ops_events")
    op.drop_index(op.f("ix_ops_events_event_type"), table_name="ops_events")
    op.drop_index(op.f("ix_ops_events_diagnosis_id"), table_name="ops_events")
    op.drop_table("ops_events")
    op.drop_index(op.f("ix_recommendation_runs_diagnosis_id"), table_name="recommendation_runs")
    op.drop_table("recommendation_runs")
    op.drop_index(op.f("ix_result_snapshots_diagnosis_id"), table_name="result_snapshots")
    op.drop_table("result_snapshots")
    op.drop_index(op.f("ix_diagnosis_outcomes_diagnosis_id"), table_name="diagnosis_outcomes")
    op.drop_table("diagnosis_outcomes")
    op.drop_index(op.f("ix_diagnosis_answers_diagnosis_id"), table_name="diagnosis_answers")
    op.drop_table("diagnosis_answers")
    op.drop_index(op.f("ix_diagnosis_sessions_user_id"), table_name="diagnosis_sessions")
    op.drop_index(op.f("ix_diagnosis_sessions_public_id"), table_name="diagnosis_sessions")
    op.drop_table("diagnosis_sessions")
    op.drop_index(op.f("ix_access_sessions_user_id"), table_name="access_sessions")
    op.drop_index(op.f("ix_access_sessions_token_hash"), table_name="access_sessions")
    op.drop_table("access_sessions")
    op.drop_index(op.f("ix_invite_codes_code_hash"), table_name="invite_codes")
    op.drop_table("invite_codes")
    op.drop_index(op.f("ix_internal_users_email"), table_name="internal_users")
    op.drop_table("internal_users")
