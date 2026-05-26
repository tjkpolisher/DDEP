from collections.abc import Iterable

from ddep_backend.search_agent.models import (
    FallbackReason,
    LearningRecommendation,
    LearningResourceCandidate,
    RecommendationRequest,
    RecommendationRun,
    ResourceDifficulty,
    ScoreBreakdown,
)
from ddep_backend.search_agent.providers import CuratedResourceProvider, LearningResourceProvider

WEIGHTS = {
    "trust": 0.35,
    "level_fit": 0.25,
    "freshness": 0.15,
    "practice": 0.15,
    "dedupe": 0.10,
}

MIN_TRUST_SCORE = 0.7
MIN_RECOMMENDATION_COUNT = 3


def recommend_learning_resources(
    request: RecommendationRequest,
    *,
    provider: LearningResourceProvider | None = None,
) -> RecommendationRun:
    resource_provider = provider or CuratedResourceProvider()
    query_terms = generate_query_terms(request)
    candidates = resource_provider.collect(request, query_terms)
    verified = [
        candidate
        for candidate in candidates
        if candidate.is_verified and candidate.trust_score >= MIN_TRUST_SCORE
    ]
    fallback_reasons: list[FallbackReason] = []
    if len(verified) < len(candidates):
        fallback_reasons.append("low_trust_results_filtered")
    if not _has_direct_match(verified, request):
        fallback_reasons.append("no_direct_concept_match")
        verified = _fallback_candidates(resource_provider, request, query_terms, verified)
    if len(verified) < max(request.min_results, MIN_RECOMMENDATION_COUNT):
        fallback_reasons.append("insufficient_verified_results")
        verified = _fallback_candidates(resource_provider, request, query_terms, verified)

    recommendations = _rank(verified, request)[: request.max_results]
    return RecommendationRun(
        query_terms=query_terms,
        recommendations=recommendations,
        fallback_reasons=_unique_in_order(fallback_reasons),
        candidate_count=len(candidates),
        verified_candidate_count=len(verified),
    )


def generate_query_terms(request: RecommendationRequest) -> list[str]:
    terms = [
        *_normalize_tags(request.prerequisite_tags),
        *_normalize_tags(request.weak_concept_tags),
        *(domain.value for domain in request.target_domains),
    ]
    return _unique_in_order(terms)


def _rank(
    candidates: Iterable[LearningResourceCandidate],
    request: RecommendationRequest,
) -> list[LearningRecommendation]:
    seen_urls: set[str] = set()
    ranked: list[LearningRecommendation] = []
    for candidate in candidates:
        url = str(candidate.url)
        dedupe = 0.0 if url in seen_urls else 1.0
        seen_urls.add(url)
        score = ScoreBreakdown(
            trust=round(candidate.trust_score * WEIGHTS["trust"], 4),
            level_fit=round(
                _level_fit(candidate.difficulty, request.learner_level) * WEIGHTS["level_fit"],
                4,
            ),
            freshness=round(candidate.freshness_score * WEIGHTS["freshness"], 4),
            practice=round(candidate.practice_score * WEIGHTS["practice"], 4),
            dedupe=round(dedupe * WEIGHTS["dedupe"], 4),
            total=0,
        )
        total = round(
            score.trust + score.level_fit + score.freshness + score.practice + score.dedupe,
            4,
        )
        ranked.append(
            LearningRecommendation(
                title=candidate.title,
                url=candidate.url,
                source_name=candidate.source_name,
                source_type=candidate.source_type,
                difficulty=candidate.difficulty,
                trust_score=candidate.trust_score,
                recommendation_reason=_reason(candidate, request),
                prerequisite_tags=candidate.prerequisite_tags,
                concept_tags=candidate.concept_tags,
                score=score.model_copy(update={"total": total}),
            )
        )
    ranked.sort(key=lambda item: (-item.score.total, item.source_name, item.title))
    return ranked


def _fallback_candidates(
    provider: LearningResourceProvider,
    request: RecommendationRequest,
    query_terms: list[str],
    existing: list[LearningResourceCandidate],
) -> list[LearningResourceCandidate]:
    existing_urls = {str(candidate.url) for candidate in existing}
    broad_request = request.model_copy(update={"weak_concept_tags": [], "prerequisite_tags": []})
    fallback = [
        candidate
        for candidate in provider.collect(broad_request, query_terms)
        if candidate.is_verified
        and candidate.trust_score >= MIN_TRUST_SCORE
        and str(candidate.url) not in existing_urls
    ]
    return [*existing, *fallback]


def _has_direct_match(
    candidates: list[LearningResourceCandidate],
    request: RecommendationRequest,
) -> bool:
    requested = set(request.weak_concept_tags) | set(request.prerequisite_tags)
    if not requested:
        return bool(candidates)
    return any(
        requested & (set(candidate.concept_tags) | set(candidate.prerequisite_tags))
        for candidate in candidates
    )


def _reason(candidate: LearningResourceCandidate, request: RecommendationRequest) -> str:
    requested = set(request.weak_concept_tags) | set(request.prerequisite_tags)
    matched = sorted(requested & (set(candidate.concept_tags) | set(candidate.prerequisite_tags)))
    if matched:
        return f"{', '.join(matched)} 보강에 직접 연결되는 검증 자료"
    return "취약 개념과 인접한 공식/공개 학습 자료"


def _level_fit(candidate: ResourceDifficulty, target: ResourceDifficulty) -> float:
    order = {"intro": 0, "intermediate": 1, "advanced": 2}
    distance = abs(order[candidate] - order[target])
    if distance == 0:
        return 1.0
    if distance == 1:
        return 0.7
    return 0.4


def _normalize_tags(tags: list[str]) -> list[str]:
    return [tag.strip().lower().replace(" ", "_") for tag in tags if tag.strip()]


def _unique_in_order[T](values: Iterable[T]) -> list[T]:
    seen: set[T] = set()
    unique: list[T] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
