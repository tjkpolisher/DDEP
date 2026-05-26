from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ddep_backend.core.config import get_settings
from ddep_backend.db.session import get_db
from ddep_backend.diagnosis_engine import (
    DiagnosisResult,
    DiagnosisSessionState,
    QuestionOutcome,
    SubmittedAnswer,
    apply_outcome,
    calculate_result,
    complete_session,
    grade_submitted_answer,
)
from ddep_backend.diagnosis_engine.repository import (
    load_approved_engine_questions,
    load_concept_prerequisite_graph,
)
from ddep_backend.question_db.enums import AnswerType, Difficulty
from ddep_backend.question_db.models import Question, QuestionConceptTag, QuestionPrerequisiteTag
from ddep_backend.result_report import build_result_report
from ddep_backend.result_report.models import ResultReport
from ddep_backend.search_agent import (
    RecommendationRequest,
    RecommendationRun,
    recommend_learning_resources,
)
from ddep_backend.service_mvp.models import (
    AccessSession,
    DiagnosisAnswer,
    DiagnosisOutcomeRecord,
    DiagnosisSessionRecord,
    InternalUser,
    InviteCode,
    OpsEvent,
    RecommendationItemRecord,
    RecommendationRunRecord,
    ResultSnapshotRecord,
)
from ddep_backend.service_mvp.schemas import (
    AccessVerifyRequest,
    AccessVerifyResponse,
    ComparisonResponse,
    CompleteDiagnosisResponse,
    DiagnosisQuestionChoice,
    DiagnosisQuestionPublic,
    DiagnosisSessionResponse,
    OpsEventResponse,
    SaveAnswerRequest,
    SaveAnswerResponse,
    UserSummary,
)
from ddep_backend.service_mvp.security import hash_secret, new_bearer_token, session_expiry

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
AuthHeader = Annotated[str | None, Header()]
PreviousDiagnosisId = Annotated[str, Query()]


def get_current_user(
    session: DbSession,
    authorization: AuthHeader = None,
) -> InternalUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    token_hash = hash_secret(token, get_settings())
    access_session = session.scalar(
        select(AccessSession)
        .where(AccessSession.token_hash == token_hash)
        .options(selectinload(AccessSession.user))
    )
    if access_session is None or access_session.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid bearer token")
    if _is_expired(access_session.expires_at):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Expired bearer token")
    return access_session.user


CurrentUser = Annotated[InternalUser, Depends(get_current_user)]


@router.post("/access/verify")
def verify_access(
    request: AccessVerifyRequest,
    session: DbSession,
) -> AccessVerifyResponse:
    settings = get_settings()
    invite = session.scalar(
        select(InviteCode).where(InviteCode.code_hash == hash_secret(request.invite_code, settings))
    )
    if invite is None or not invite.is_active or _is_expired(invite.expires_at):
        _log_event(session, "access.denied", {"reason": "invalid_invite"})
        session.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid invite code")
    if invite.max_uses is not None and invite.use_count >= invite.max_uses:
        _log_event(session, "access.denied", {"reason": "invite_exhausted"})
        session.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invite code exhausted")

    user = _resolve_user(session, request)
    if invite.grants_operator:
        user.is_operator = True
    token = new_bearer_token()
    expires_at = session_expiry(settings)
    access_session = AccessSession(
        user=user,
        token_hash=hash_secret(token, settings),
        expires_at=expires_at,
    )
    invite.use_count += 1
    session.add(access_session)
    _log_event(session, "access.verified", {"invite_label": invite.label}, user=user)
    session.commit()
    session.refresh(user)
    return AccessVerifyResponse(
        token=token,
        expires_at=expires_at,
        user=_user_summary(user),
    )


@router.post("/diagnoses")
def create_diagnosis(
    user: CurrentUser,
    session: DbSession,
) -> DiagnosisSessionResponse:
    questions = _load_public_questions(session)
    if not questions:
        raise HTTPException(status.HTTP_409_CONFLICT, "No approved questions available")
    diagnosis = DiagnosisSessionRecord(
        public_id=str(uuid4()),
        user_id=user.id,
        status="active",
        question_external_ids=[question.external_id for question in questions],
    )
    session.add(diagnosis)
    session.flush()
    _log_event(
        session,
        "diagnosis.started",
        {"question_count": len(questions)},
        user=user,
        diagnosis=diagnosis,
    )
    session.commit()
    session.refresh(diagnosis)
    return _diagnosis_response(diagnosis, questions)


@router.get("/diagnoses/{diagnosis_id}")
def get_diagnosis(
    diagnosis_id: str,
    user: CurrentUser,
    session: DbSession,
) -> DiagnosisSessionResponse:
    diagnosis = _require_diagnosis(session, diagnosis_id, user)
    return _diagnosis_response(diagnosis, _load_public_questions(session, diagnosis))


@router.post("/diagnoses/{diagnosis_id}/answers")
def save_answer(
    diagnosis_id: str,
    request: SaveAnswerRequest,
    user: CurrentUser,
    session: DbSession,
) -> SaveAnswerResponse:
    diagnosis = _require_diagnosis(session, diagnosis_id, user)
    if diagnosis.status == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Diagnosis already completed")
    engine_questions = {
        question.external_id: question for question in load_approved_engine_questions(session)
    }
    question = engine_questions.get(request.question_external_id)
    if question is None or request.question_external_id not in diagnosis.question_external_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found in diagnosis")

    outcome = grade_submitted_answer(question, request)
    _upsert_answer(session, diagnosis, request)
    _upsert_outcome(session, diagnosis, outcome)
    _log_event(
        session,
        "diagnosis.answer_saved",
        {"question_external_id": request.question_external_id, "is_correct": outcome.is_correct},
        user=user,
        diagnosis=diagnosis,
    )
    session.commit()
    answered_count = _answered_count(session, diagnosis)
    return SaveAnswerResponse(
        diagnosis_id=diagnosis.public_id,
        question_external_id=request.question_external_id,
        is_correct=outcome.is_correct,
        answered_question_count=answered_count,
    )


@router.post("/diagnoses/{diagnosis_id}/complete")
def complete_diagnosis(
    diagnosis_id: str,
    user: CurrentUser,
    session: DbSession,
) -> CompleteDiagnosisResponse:
    diagnosis = _require_diagnosis(session, diagnosis_id, user)
    if (
        diagnosis.status == "completed"
        and diagnosis.result_snapshot
        and diagnosis.recommendation_run
    ):
        return CompleteDiagnosisResponse(
            diagnosis=_diagnosis_response(diagnosis, _load_public_questions(session, diagnosis)),
            report=ResultReport.model_validate(diagnosis.result_snapshot.report_json),
            recommendations=RecommendationRun.model_validate(diagnosis.recommendation_run.run_json),
        )

    state = _state_from_outcomes(session, diagnosis)
    missing_question_ids = sorted(
        set(diagnosis.question_external_ids) - set(state.answered_question_ids)
    )
    if missing_question_ids:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "All diagnosis questions must be answered before completion: "
            f"{len(missing_question_ids)} missing",
        )
    state = complete_session(state)
    questions = load_approved_engine_questions(session)
    graph = load_concept_prerequisite_graph(session)
    result = calculate_result(questions, state, graph)
    report = build_result_report(result)
    recommendation_request = _recommendation_request(report)
    recommendation_run = recommend_learning_resources(recommendation_request)

    diagnosis.status = "completed"
    diagnosis.completed_at = datetime.now(UTC)
    _replace_result_snapshot(
        session,
        diagnosis,
        result,
        report,
    )
    _replace_recommendations(
        session,
        diagnosis,
        recommendation_request,
        recommendation_run,
    )
    _log_event(
        session,
        "diagnosis.completed",
        {
            "answered_question_count": result.answered_question_count,
            "recommendation_count": len(recommendation_run.recommendations),
            "fallback_reasons": recommendation_run.fallback_reasons,
        },
        user=user,
        diagnosis=diagnosis,
    )
    session.commit()
    session.refresh(diagnosis)
    return CompleteDiagnosisResponse(
        diagnosis=_diagnosis_response(diagnosis, _load_public_questions(session, diagnosis)),
        report=report,
        recommendations=recommendation_run,
    )


@router.get("/diagnoses/{diagnosis_id}/results")
def get_results(
    diagnosis_id: str,
    user: CurrentUser,
    session: DbSession,
) -> dict[str, object]:
    diagnosis = _require_diagnosis(session, diagnosis_id, user)
    if diagnosis.result_snapshot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Result snapshot not available")
    return diagnosis.result_snapshot.report_json


@router.get("/diagnoses/{diagnosis_id}/recommendations")
def get_recommendations(
    diagnosis_id: str,
    user: CurrentUser,
    session: DbSession,
) -> dict[str, object]:
    diagnosis = _require_diagnosis(session, diagnosis_id, user)
    if diagnosis.recommendation_run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recommendation run not available")
    return diagnosis.recommendation_run.run_json


@router.get("/diagnoses/{diagnosis_id}/comparison")
def compare_diagnoses(
    diagnosis_id: str,
    previous_id: PreviousDiagnosisId,
    user: CurrentUser,
    session: DbSession,
) -> ComparisonResponse:
    current = _require_diagnosis(session, diagnosis_id, user)
    previous = _require_diagnosis(session, previous_id, user)
    if current.result_snapshot is None or previous.result_snapshot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Both diagnoses need result snapshots")
    comparison = build_result_report(
        result=_diagnosis_result_from_snapshot(current),
        previous_result=_diagnosis_result_from_snapshot(previous),
    ).comparison
    if comparison is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Comparison unavailable")
    return ComparisonResponse(
        current_diagnosis_id=current.public_id,
        previous_diagnosis_id=previous.public_id,
        comparison=comparison,
    )


@router.get("/ops/events")
def list_ops_events(
    user: CurrentUser,
    session: DbSession,
) -> list[OpsEventResponse]:
    if not user.is_operator:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Operator access required")
    events = session.scalars(select(OpsEvent).order_by(OpsEvent.id.desc()).limit(100)).all()
    return [
        OpsEventResponse(
            id=event.id,
            event_type=event.event_type,
            user_id=event.user_id,
            diagnosis_id=event.diagnosis_id,
            detail=event.detail_json,
            created_at=event.created_at,
        )
        for event in events
    ]


def _resolve_user(session: Session, request: AccessVerifyRequest) -> InternalUser:
    user = None
    if request.email:
        user = session.scalar(select(InternalUser).where(InternalUser.email == request.email))
    if user is None:
        user = InternalUser(display_name=request.display_name, email=request.email)
        session.add(user)
        session.flush()
    else:
        user.display_name = request.display_name
    return user


def _require_diagnosis(
    session: Session,
    public_id: str,
    user: InternalUser,
) -> DiagnosisSessionRecord:
    diagnosis = session.scalar(
        select(DiagnosisSessionRecord)
        .where(DiagnosisSessionRecord.public_id == public_id)
        .options(
            selectinload(DiagnosisSessionRecord.answers),
            selectinload(DiagnosisSessionRecord.outcomes),
            selectinload(DiagnosisSessionRecord.result_snapshot),
            selectinload(DiagnosisSessionRecord.recommendation_run).selectinload(
                RecommendationRunRecord.items
            ),
        )
    )
    if diagnosis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Diagnosis not found")
    if diagnosis.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Diagnosis belongs to another user")
    return diagnosis


def _load_public_questions(
    session: Session,
    diagnosis: DiagnosisSessionRecord | None = None,
) -> list[DiagnosisQuestionPublic]:
    statement = (
        select(Question)
        .where(Question.review_status == "approved")
        .options(
            selectinload(Question.choices),
            selectinload(Question.concept_tags).selectinload(QuestionConceptTag.tag),
            selectinload(Question.prerequisite_tags).selectinload(QuestionPrerequisiteTag.tag),
        )
        .order_by(Question.external_id)
    )
    questions = session.scalars(statement).all()
    if diagnosis is not None:
        allowed = set(diagnosis.question_external_ids)
        questions = [question for question in questions if question.external_id in allowed]
    return [
        DiagnosisQuestionPublic(
            external_id=question.external_id,
            domain=question.domain,
            difficulty=Difficulty(question.difficulty),
            answer_type=AnswerType(question.answer_type),
            prompt=question.prompt,
            choices=[
                DiagnosisQuestionChoice(key=choice.choice_key, text=choice.text)
                for choice in sorted(question.choices, key=lambda item: item.sort_order)
            ],
            concept_tags=sorted(link.tag.slug for link in question.concept_tags),
            prerequisite_tags=sorted(link.tag.slug for link in question.prerequisite_tags),
        )
        for question in questions
    ]


def _diagnosis_response(
    diagnosis: DiagnosisSessionRecord,
    questions: list[DiagnosisQuestionPublic],
) -> DiagnosisSessionResponse:
    status_value: Literal["active", "completed"] = (
        "completed" if diagnosis.status == "completed" else "active"
    )
    return DiagnosisSessionResponse(
        id=diagnosis.public_id,
        status=status_value,
        answered_question_count=len({answer.question_external_id for answer in diagnosis.answers}),
        question_count=len(diagnosis.question_external_ids),
        questions=questions,
        created_at=diagnosis.created_at,
        completed_at=diagnosis.completed_at,
    )


def _upsert_answer(
    session: Session,
    diagnosis: DiagnosisSessionRecord,
    submitted: SubmittedAnswer,
) -> None:
    answer = session.scalar(
        select(DiagnosisAnswer).where(
            DiagnosisAnswer.diagnosis_id == diagnosis.id,
            DiagnosisAnswer.question_external_id == submitted.question_external_id,
        )
    )
    if answer is None:
        answer = DiagnosisAnswer(
            diagnosis_id=diagnosis.id,
            question_external_id=submitted.question_external_id,
            choice_keys=submitted.choice_keys,
            short_answer=submitted.short_answer,
        )
        session.add(answer)
    else:
        answer.choice_keys = submitted.choice_keys
        answer.short_answer = submitted.short_answer


def _upsert_outcome(
    session: Session,
    diagnosis: DiagnosisSessionRecord,
    outcome: QuestionOutcome,
) -> None:
    record = session.scalar(
        select(DiagnosisOutcomeRecord).where(
            DiagnosisOutcomeRecord.diagnosis_id == diagnosis.id,
            DiagnosisOutcomeRecord.question_external_id == outcome.question_external_id,
        )
    )
    payload = outcome.model_dump(mode="json")
    if record is None:
        session.add(
            DiagnosisOutcomeRecord(
                diagnosis_id=diagnosis.id,
                question_external_id=outcome.question_external_id,
                outcome_json=payload,
            )
        )
    else:
        record.outcome_json = payload


def _state_from_outcomes(
    session: Session,
    diagnosis: DiagnosisSessionRecord,
) -> DiagnosisSessionState:
    outcomes = session.scalars(
        select(DiagnosisOutcomeRecord)
        .where(DiagnosisOutcomeRecord.diagnosis_id == diagnosis.id)
        .order_by(DiagnosisOutcomeRecord.id)
    ).all()
    state = DiagnosisSessionState()
    for record in outcomes:
        state = apply_outcome(state, QuestionOutcome.model_validate(record.outcome_json))
    return state


def _answered_count(session: Session, diagnosis: DiagnosisSessionRecord) -> int:
    return len(
        session.scalars(
            select(DiagnosisAnswer.question_external_id).where(
                DiagnosisAnswer.diagnosis_id == diagnosis.id
            )
        ).all()
    )


def _replace_result_snapshot(
    session: Session,
    diagnosis: DiagnosisSessionRecord,
    result: DiagnosisResult,
    report: ResultReport,
) -> None:
    if diagnosis.result_snapshot is not None:
        session.delete(diagnosis.result_snapshot)
        session.flush()
    session.add(
        ResultSnapshotRecord(
            diagnosis_id=diagnosis.id,
            result_json=result.model_dump(mode="json"),
            report_json=report.model_dump(mode="json"),
        )
    )


def _replace_recommendations(
    session: Session,
    diagnosis: DiagnosisSessionRecord,
    request: RecommendationRequest,
    run_result: RecommendationRun,
) -> None:
    if diagnosis.recommendation_run is not None:
        session.delete(diagnosis.recommendation_run)
        session.flush()
    run = RecommendationRunRecord(
        diagnosis_id=diagnosis.id,
        request_json=request.model_dump(mode="json"),
        run_json=run_result.model_dump(mode="json"),
        fallback_reasons=run_result.fallback_reasons,
    )
    session.add(run)
    session.flush()
    for index, item in enumerate(run_result.recommendations, start=1):
        session.add(
            RecommendationItemRecord(
                run_id=run.id,
                sort_order=index,
                title=item.title,
                url=item.url,
                source_type=item.source_type,
                difficulty=item.difficulty,
                trust_score=item.trust_score,
                recommendation_reason=item.recommendation_reason,
                score_json=item.score.model_dump(mode="json"),
            )
        )


def _recommendation_request(report: ResultReport) -> RecommendationRequest:
    weak_tags = list(report.strength_weakness.weak_concept_tags)
    prerequisites = [
        prerequisite for item in report.roadmap for prerequisite in item.prerequisite_chain
    ]
    return RecommendationRequest(
        weak_concept_tags=weak_tags,
        prerequisite_tags=prerequisites,
        target_domains=list(report.strength_weakness.weakness_domains),
    )


def _diagnosis_result_from_snapshot(diagnosis: DiagnosisSessionRecord) -> DiagnosisResult:
    if diagnosis.result_snapshot is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Result snapshot not available")
    return DiagnosisResult.model_validate(diagnosis.result_snapshot.result_json)


def _log_event(
    session: Session,
    event_type: str,
    detail: dict[str, object],
    *,
    user: InternalUser | None = None,
    diagnosis: DiagnosisSessionRecord | None = None,
) -> None:
    session.add(
        OpsEvent(
            event_type=event_type,
            user_id=user.id if user else None,
            diagnosis_id=diagnosis.id if diagnosis else None,
            detail_json=detail,
        )
    )


def _user_summary(user: InternalUser) -> UserSummary:
    return UserSummary(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        is_operator=user.is_operator,
    )


def _is_expired(value: datetime | None) -> bool:
    if value is None:
        return False
    comparable = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return comparable <= datetime.now(UTC)
