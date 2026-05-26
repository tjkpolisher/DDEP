from ddep_backend.search_agent.engine import recommend_learning_resources
from ddep_backend.search_agent.models import RecommendationRequest, RecommendationRun


def preview_recommendations(request: RecommendationRequest) -> RecommendationRun:
    return recommend_learning_resources(request)
