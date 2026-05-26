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
    token = _verify(client, "Ada", "ada@example.com")

    diagnosis = client.post("/diagnoses", headers=_auth(token)).json()
    question_id = diagnosis["questions"][0]["external_id"]
    answer_url = f"/diagnoses/{diagnosis['id']}/answers"

    first = client.post(
        answer_url,
        headers=_auth(token),
        json={"question_external_id": question_id, "choice_keys": ["B"]},
    )
    second = client.post(
        answer_url,
        headers=_auth(token),
        json={"question_external_id": question_id, "choice_keys": ["A"]},
    )
    completed = client.post(f"/diagnoses/{diagnosis['id']}/complete", headers=_auth(token))
    results = client.get(f"/diagnoses/{diagnosis['id']}/results", headers=_auth(token))
    recommendations = client.get(
        f"/diagnoses/{diagnosis['id']}/recommendations",
        headers=_auth(token),
    )
    events = client.get("/ops/events", headers=_auth(token))

    assert first.status_code == 200
    assert second.json()["answered_question_count"] == 1
    assert completed.status_code == 200
    assert completed.json()["report"]["snapshot"]["answered_question_count"] == 1
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

    previous_id = _complete_one_question(client, first_token, ["B"])
    current_id = _complete_one_question(client, first_token, ["A"])

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
    session.add(InviteCode(code_hash=hash_secret("beta", settings), label="Beta", is_active=True))
    imu = ConceptTag(slug="imu", label="IMU", description="IMU")
    sensor_fusion = ConceptTag(
        slug="sensor_fusion",
        label="Sensor fusion",
        description="Fusion",
        domain=DiagnosisDomain.AUTONOMOUS_AI.value,
    )
    attitude = ConceptTag(
        slug="attitude_control",
        label="Attitude",
        description="Attitude",
        domain=DiagnosisDomain.CONTROL.value,
    )
    session.add_all([imu, sensor_fusion, attitude])
    session.flush()
    session.add_all(
        [
            ConceptTagPrerequisite(
                concept_tag_id=sensor_fusion.id,
                prerequisite_tag_id=imu.id,
            ),
            ConceptTagPrerequisite(
                concept_tag_id=attitude.id,
                prerequisite_tag_id=sensor_fusion.id,
            ),
        ]
    )
    question = Question(
        external_id="control-1",
        domain=DiagnosisDomain.CONTROL.value,
        subdomain="Control",
        difficulty=Difficulty.MEDIUM.value,
        answer_type=AnswerType.SINGLE_CHOICE.value,
        review_status=ReviewStatus.APPROVED.value,
        source_type=SourceType.INTERNAL_NOTE.value,
        source_title="Fixture",
        source_reference="Fixture",
        prompt="Which option is correct?",
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
            QuestionConceptTag(question_id=question.id, concept_tag_id=attitude.id),
        ]
    )


def _verify(client: TestClient, display_name: str, email: str) -> str:
    response = client.post(
        "/access/verify",
        json={"invite_code": "beta", "display_name": display_name, "email": email},
    )
    assert response.status_code == 200
    return str(response.json()["token"])


def _complete_one_question(client: TestClient, token: str, choice_keys: list[str]) -> str:
    diagnosis = client.post("/diagnoses", headers=_auth(token)).json()
    question_id = diagnosis["questions"][0]["external_id"]
    client.post(
        f"/diagnoses/{diagnosis['id']}/answers",
        headers=_auth(token),
        json={"question_external_id": question_id, "choice_keys": choice_keys},
    )
    completed = client.post(f"/diagnoses/{diagnosis['id']}/complete", headers=_auth(token))
    assert completed.status_code == 200
    return str(diagnosis["id"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
