from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ddep_backend.db.base import Base


class InternalUser(Base):
    __tablename__ = "internal_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    is_operator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sessions: Mapped[list["AccessSession"]] = relationship(back_populates="user")
    diagnoses: Mapped[list["DiagnosisSessionRecord"]] = relationship(back_populates="user")


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    grants_operator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class AccessSession(Base):
    __tablename__ = "access_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("internal_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[InternalUser] = relationship(back_populates="sessions")


class DiagnosisSessionRecord(Base):
    __tablename__ = "diagnosis_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed')", name="ck_diagnosis_sessions_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("internal_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    question_external_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[InternalUser] = relationship(back_populates="diagnoses")
    answers: Mapped[list["DiagnosisAnswer"]] = relationship(
        back_populates="diagnosis",
        cascade="all, delete-orphan",
    )
    outcomes: Mapped[list["DiagnosisOutcomeRecord"]] = relationship(
        back_populates="diagnosis",
        cascade="all, delete-orphan",
    )
    result_snapshot: Mapped["ResultSnapshotRecord | None"] = relationship(
        back_populates="diagnosis",
        cascade="all, delete-orphan",
    )
    recommendation_run: Mapped["RecommendationRunRecord | None"] = relationship(
        back_populates="diagnosis",
        cascade="all, delete-orphan",
    )


class DiagnosisAnswer(Base):
    __tablename__ = "diagnosis_answers"
    __table_args__ = (
        UniqueConstraint(
            "diagnosis_id",
            "question_external_id",
            name="uq_diagnosis_answers_diagnosis_question",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(
        ForeignKey("diagnosis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    choice_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    short_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    diagnosis: Mapped[DiagnosisSessionRecord] = relationship(back_populates="answers")


class DiagnosisOutcomeRecord(Base):
    __tablename__ = "diagnosis_outcomes"
    __table_args__ = (
        UniqueConstraint(
            "diagnosis_id",
            "question_external_id",
            name="uq_diagnosis_outcomes_diagnosis_question",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(
        ForeignKey("diagnosis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    outcome_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    diagnosis: Mapped[DiagnosisSessionRecord] = relationship(back_populates="outcomes")


class ResultSnapshotRecord(Base):
    __tablename__ = "result_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(
        ForeignKey("diagnosis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    result_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    report_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    diagnosis: Mapped[DiagnosisSessionRecord] = relationship(back_populates="result_snapshot")


class RecommendationRunRecord(Base):
    __tablename__ = "recommendation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagnosis_id: Mapped[int] = mapped_column(
        ForeignKey("diagnosis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    request_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    run_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    fallback_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    diagnosis: Mapped[DiagnosisSessionRecord] = relationship(back_populates="recommendation_run")
    items: Mapped[list["RecommendationItemRecord"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RecommendationItemRecord.sort_order",
    )


class RecommendationItemRecord(Base):
    __tablename__ = "recommendation_items"
    __table_args__ = (
        UniqueConstraint("run_id", "sort_order", name="uq_recommendation_items_run_order"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    score_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)

    run: Mapped[RecommendationRunRecord] = relationship(back_populates="items")


class OpsEvent(Base):
    __tablename__ = "ops_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("internal_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    diagnosis_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagnosis_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    detail_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
