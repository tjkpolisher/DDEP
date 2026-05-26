from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from ddep_backend.core.config import get_settings
from ddep_backend.db.base import Base
from ddep_backend.db.session import get_db
from ddep_backend.domains import DiagnosisDomain
from ddep_backend.main import create_app
from ddep_backend.question_db.enums import AnswerType, Difficulty, ReviewStatus, SourceType
from ddep_backend.question_db.models import (
    ConceptTag,
    ConceptTagPrerequisite,
    Question,
    QuestionChoice,
    QuestionConceptTag,
)
from ddep_backend.service_mvp.models import InviteCode
from ddep_backend.service_mvp.security import hash_secret


def test_authenticated_diagnosis_lifecycle_persists_results_and_recommendations() -> None:
    client = _client()
    token = _verify(client, "Ada", "ada@example.com", invite_code="operator")

    diagnosis = client.post("/diagnoses", headers=_auth(token)).json()
    answer_url = f"/diagnoses/{diagnosis['id']}/answers"

    incomplete = client.post(f"/diagnoses/{diagnosis['id']}/complete", headers=_auth(token))
    first_question_id = diagnosis["questions"][0]["external_id"]
    first = client.post(
        answer_url,
        headers=_auth(token),
        json={"question_external_id": first_question_id, "choice_keys": ["B"]},
    )
    second = client.post(
        answer_url,
        headers=_auth(token),
        json={"question_external_id": first_question_id, "choice_keys": ["A"]},
    )
    _answer_remaining(client, token, diagnosis, answered_question_ids={first_question_id})
    completed = client.post(f"/diagnoses/{diagnosis['id']}/complete", headers=_auth(token))
    results = client.get(f"/diagnoses/{diagnosis['id']}/results", headers=_auth(token))
    recommendations = client.get(
        f"/diagnoses/{diagnosis['id']}/recommendations",
        headers=_auth(token),
    )
    events = client.get("/ops/events", headers=_auth(token))

    assert first.status_code == 200
    assert incomplete.status_code == 409
    assert second.json()["answered_question_count"] == 1
    assert completed.status_code == 200
    assert completed.json()["report"]["snapshot"]["answered_question_count"] == 6
    assert len(completed.json()["recommendations"]["recommendations"]) >= 3
    assert results.json()["snapshot"]["status"] == "completed"
    assert recommendations.json()["recommendations"]
    assert {event["event_type"] for event in events.json()} >= {
        "access.verified",
        "diagnosis.started",
        "diagnosis.answer_saved",
        "diagnosis.completed",
    }


def test_same_user_comparison_and_cross_user_rejection() -> None:
    client = _client()
    first_token = _verify(client, "Ada", "ada@example.com")
    second_token = _verify(client, "Grace", "grace@example.com")

    previous_id = _complete_all_questions(client, first_token, ["B"])
    current_id = _complete_all_questions(client, first_token, ["A"])

    comparison = client.get(
        f"/diagnoses/{current_id}/comparison",
        headers=_auth(first_token),
        params={"previous_id": previous_id},
    )
    forbidden = client.get(f"/diagnoses/{current_id}", headers=_auth(second_token))
    unauthorized = client.get(f"/diagnoses/{current_id}")

    assert comparison.status_code == 200
    assert comparison.json()["comparison"]["domain_deltas"]
    assert forbidden.status_code == 403
    assert unauthorized.status_code == 401


def test_ops_events_require_operator_access() -> None:
    client = _client()
    user_token = _verify(client, "Ada", "ada@example.com")

    response = client.get("/ops/events", headers=_auth(user_token))

    assert response.status_code == 403


def _client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed(session)
        session.commit()

    app = create_app()

    def override_db() -> Generator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _seed(session: Session) -> None:
    settings = get_settings()
    session.add_all(
        [
            InviteCode(code_hash=hash_secret("beta", settings), label="Beta", is_active=True),
            InviteCode(
                code_hash=hash_secret("operator", settings),
                label="Operator",
                is_active=True,
                grants_operator=True,
            ),
        ]
    )
    concepts = [
        ConceptTag(slug="basic_physics", label="Physics", description="Physics"),
        ConceptTag(slug="power_distribution", label="Power", description="Power"),
        ConceptTag(
            slug="pid_control",
            label="PID",
            description="PID",
            domain=DiagnosisDomain.CONTROL.value,
        ),
        ConceptTag(
            slug="mavlink_protocol",
            label="MAVLink",
            description="MAVLink",
            domain=DiagnosisDomain.SOFTWARE.value,
        ),
        ConceptTag(
            slug="path_planning",
            label="Path planning",
            description="Path",
            domain=DiagnosisDomain.AUTONOMOUS_AI.value,
        ),
        ConceptTag(
            slug="preflight_inspection",
            label="Preflight",
            description="Preflight",
            domain=DiagnosisDomain.FABRICATION_OPERATIONS.value,
        ),
    ]
    session.add_all(concepts)
    session.flush()
    concept_by_slug = {concept.slug: concept for concept in concepts}
    session.add_all(
        [
            ConceptTagPrerequisite(
                concept_tag_id=concept_by_slug["pid_control"].id,
                prerequisite_tag_id=concept_by_slug["basic_physics"].id,
            ),
        ]
    )
    for index, (domain, concept_slug) in enumerate(
        [
            (DiagnosisDomain.AIRFRAME_AERODYNAMICS, "basic_physics"),
            (DiagnosisDomain.ELECTRONICS_HARDWARE, "power_distribution"),
            (DiagnosisDomain.CONTROL, "pid_control"),
            (DiagnosisDomain.SOFTWARE, "mavlink_protocol"),
            (DiagnosisDomain.AUTONOMOUS_AI, "path_planning"),
            (DiagnosisDomain.FABRICATION_OPERATIONS, "preflight_inspection"),
        ],
        start=1,
    ):
        _add_question(session, index, domain, concept_by_slug[concept_slug])


def _add_question(
    session: Session,
    index: int,
    domain: DiagnosisDomain,
    concept: ConceptTag,
) -> None:
    question = Question(
        external_id=f"q-{index}",
        domain=domain.value,
        subdomain="Fixture",
        difficulty=Difficulty.MEDIUM.value,
        answer_type=AnswerType.SINGLE_CHOICE.value,
        review_status=ReviewStatus.APPROVED.value,
        source_type=SourceType.INTERNAL_NOTE.value,
        source_title="Fixture",
        source_reference="Fixture",
        prompt=f"Question {index}",
        explanation="A is correct",
        short_answer_case_sensitive=False,
    )
    session.add(question)
    session.flush()
    session.add_all(
        [
            QuestionChoice(
                question_id=question.id,
                choice_key="A",
                text="Correct",
                is_correct=True,
                sort_order=0,
            ),
            QuestionChoice(
                question_id=question.id,
                choice_key="B",
                text="Wrong",
                is_correct=False,
                sort_order=1,
            ),
            QuestionConceptTag(question_id=question.id, concept_tag_id=concept.id),
        ]
    )


def _verify(client: TestClient, display_name: str, email: str, *, invite_code: str = "beta") -> str:
    response = client.post(
        "/access/verify",
        json={"invite_code": invite_code, "display_name": display_name, "email": email},
    )
    assert response.status_code == 200
    return str(response.json()["token"])


def _complete_all_questions(client: TestClient, token: str, choice_keys: list[str]) -> str:
    diagnosis = client.post("/diagnoses", headers=_auth(token)).json()
    for question in diagnosis["questions"]:
        client.post(
            f"/diagnoses/{diagnosis['id']}/answers",
            headers=_auth(token),
            json={"question_external_id": question["external_id"], "choice_keys": choice_keys},
        )
    completed = client.post(f"/diagnoses/{diagnosis['id']}/complete", headers=_auth(token))
    assert completed.status_code == 200
    return str(diagnosis["id"])


def _answer_remaining(
    client: TestClient,
    token: str,
    diagnosis: dict[str, object],
    *,
    answered_question_ids: set[str],
) -> None:
    questions = diagnosis["questions"]
    assert isinstance(questions, list)
    diagnosis_id = str(diagnosis["id"])
    for question in questions:
        assert isinstance(question, dict)
        question_id = str(question["external_id"])
        if question_id in answered_question_ids:
            continue
        choice_keys = ["B"] if question_id == "q-3" else ["A"]
        client.post(
            f"/diagnoses/{diagnosis_id}/answers",
            headers=_auth(token),
            json={"question_external_id": question_id, "choice_keys": choice_keys},
        )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
