from datetime import UTC, datetime

from fastapi.testclient import TestClient

from ddep_backend.diagnosis_engine.models import (
    ConceptMastery,
    DiagnosisResult,
    DomainScore,
    WeakConcept,
)
from ddep_backend.domains import DiagnosisDomain
from ddep_backend.main import create_app
from ddep_backend.result_report import build_result_report


def test_builds_domain_profiles_summary_roadmap_and_retest_targets() -> None:
    result = _result()

    report = build_result_report(
        result,
        generated_at=datetime(2026, 5, 26, tzinfo=UTC),
    )

    assert report.snapshot.average_domain_score == 62
    assert report.snapshot.weakest_domain is DiagnosisDomain.CONTROL
    assert [profile.domain for profile in report.domain_profiles] == list(DiagnosisDomain)
    control = next(
        profile for profile in report.domain_profiles if profile.domain is DiagnosisDomain.CONTROL
    )
    assert control.readiness == "weak"
    assert control.weak_concept_tags == ["attitude_control"]
    assert report.strength_weakness.strength_domains == [DiagnosisDomain.SOFTWARE]
    assert report.strength_weakness.weakness_domains == [DiagnosisDomain.CONTROL]
    assert [item.concept_slug for item in report.roadmap] == [
        "pid",
        "imu",
        "sensor_fusion",
        "attitude_control",
    ]
    assert report.retest_targets[0].concept_slug == "attitude_control"


def test_compares_domain_deltas_and_weak_concept_changes() -> None:
    previous = _result(
        control_score=42,
        software_score=74,
        weak_slug="pid",
        weak_prerequisites=["basic_control"],
    )
    current = _result(control_score=68, software_score=82)

    comparison = build_result_report(current, previous_result=previous).comparison

    assert comparison is not None
    control_delta = next(
        item for item in comparison.domain_deltas if item.domain is DiagnosisDomain.CONTROL
    )
    assert control_delta.delta == 26
    assert comparison.resolved_weak_concepts == ["pid"]
    assert comparison.new_weak_concepts == ["attitude_control"]


def test_preview_endpoint_returns_report_without_persisting() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/result-report/preview",
        json={"result": _result().model_dump(mode="json")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["snapshot"]["answered_question_count"] == 6
    assert payload["roadmap"][0]["concept_slug"] == "pid"


def _result(
    *,
    control_score: int = 45,
    software_score: int = 78,
    weak_slug: str = "attitude_control",
    weak_prerequisites: list[str] | None = None,
) -> DiagnosisResult:
    domain_scores = [
        DomainScore(
            domain=domain,
            score=software_score if domain is DiagnosisDomain.SOFTWARE else 62,
            confidence=0.8,
            evidence_weight=3.0,
            weighted_correct=2.0,
            weighted_attempts=3.0,
            attempted_questions=3,
        )
        for domain in DiagnosisDomain
    ]
    domain_scores[2] = domain_scores[2].model_copy(
        update={"score": control_score, "confidence": 0.7}
    )
    return DiagnosisResult(
        algorithm_version="bayes-lite-v1",
        status="completed",
        answered_question_count=6,
        domain_scores=domain_scores,
        concept_mastery=[
            ConceptMastery(
                concept_slug=weak_slug,
                score=control_score,
                confidence=0.7,
                evidence_weight=2.0,
                weighted_correct=0.4,
                weighted_attempts=2.0,
                attempted_questions=2,
            )
        ],
        weak_concepts=[
            WeakConcept(
                concept_slug=weak_slug,
                score=control_score,
                confidence=0.7,
                evidence_weight=2.0,
                prerequisite_chain=weak_prerequisites
                or ["pid", "imu", "sensor_fusion"],
                domain=DiagnosisDomain.CONTROL,
            )
        ],
    )
