from fastapi.testclient import TestClient

from ddep_backend.main import create_app
from ddep_backend.search_agent import RecommendationRequest, recommend_learning_resources
from ddep_backend.search_agent.models import LearningResourceCandidate


def test_generates_ranked_verified_recommendations_with_expected_bounds() -> None:
    run = recommend_learning_resources(
        RecommendationRequest(
            weak_concept_tags=["attitude_control", "pid"],
            prerequisite_tags=["imu"],
            learner_level="intermediate",
        )
    )

    assert 3 <= len(run.recommendations) <= 7
    assert "attitude_control" in run.query_terms
    assert all(recommendation.trust_score >= 0.7 for recommendation in run.recommendations)
    assert all(
        "example.com" not in str(recommendation.url) for recommendation in run.recommendations
    )
    totals = [recommendation.score.total for recommendation in run.recommendations]
    assert totals == sorted(totals, reverse=True)


def test_filters_low_trust_candidates_and_reports_fallback_reason() -> None:
    run = recommend_learning_resources(
        RecommendationRequest(weak_concept_tags=["unknown_concept"]),
        provider=_OnlyUnverifiedProvider(),
    )

    assert run.recommendations == []
    assert run.fallback_reasons == [
        "low_trust_results_filtered",
        "no_direct_concept_match",
        "insufficient_verified_results",
    ]


def test_preview_endpoint_does_not_expose_raw_candidates() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/recommendations/preview",
        json={
            "weak_concept_tags": ["sensor_fusion"],
            "prerequisite_tags": ["imu"],
            "learner_level": "intermediate",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert 3 <= len(payload["recommendations"]) <= 7
    assert "candidates" not in payload
    assert payload["recommendations"][0]["recommendation_reason"]


class _OnlyUnverifiedProvider:
    def collect(
        self,
        request: RecommendationRequest,
        query_terms: list[str],
    ) -> list[LearningResourceCandidate]:
        return [
            LearningResourceCandidate(
                title="Unverified",
                url="https://example.com/unverified",
                source_name="Community",
                source_type="community_reference",
                difficulty="intro",
                concept_tags=request.weak_concept_tags,
                prerequisite_tags=[],
                summary="Unverified",
                trust_score=0.2,
                freshness_score=0.5,
                practice_score=0.5,
                is_verified=False,
            )
        ]
