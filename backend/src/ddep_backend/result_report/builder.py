from datetime import UTC, datetime

from ddep_backend.diagnosis_engine.models import DiagnosisResult
from ddep_backend.domains import DiagnosisDomain
from ddep_backend.result_report.models import (
    DomainReadiness,
    DomainReportProfile,
    DomainScoreDelta,
    ReportComparison,
    ReportSnapshot,
    ResultReport,
    RetestTarget,
    RoadmapItem,
    StrengthWeaknessSummary,
)


def build_result_report(
    result: DiagnosisResult,
    *,
    previous_result: DiagnosisResult | None = None,
    generated_at: datetime | None = None,
) -> ResultReport:
    weak_tags_by_domain = _weak_tags_by_domain(result)
    domain_profiles = [
        DomainReportProfile(
            domain=score.domain,
            score=score.score,
            confidence=score.confidence,
            evidence_weight=score.evidence_weight,
            attempted_questions=score.attempted_questions,
            readiness=_readiness(score.score, score.confidence),
            uncertainty=_uncertainty(score.confidence, score.attempted_questions),
            weak_concept_count=len(weak_tags_by_domain.get(score.domain, [])),
            weak_concept_tags=weak_tags_by_domain.get(score.domain, []),
        )
        for score in result.domain_scores
    ]

    report = ResultReport(
        snapshot=_snapshot(result, generated_at=generated_at),
        domain_profiles=domain_profiles,
        strength_weakness=_summary(result, domain_profiles),
        roadmap=_roadmap(result),
        retest_targets=_retest_targets(result, domain_profiles),
        comparison=_comparison(result, previous_result) if previous_result is not None else None,
    )
    return report


def _snapshot(result: DiagnosisResult, *, generated_at: datetime | None) -> ReportSnapshot:
    attempted_scores = [score for score in result.domain_scores if score.attempted_questions > 0]
    scored_domains = attempted_scores or result.domain_scores
    weakest = min(scored_domains, key=lambda item: (item.score, -item.confidence), default=None)
    strongest = max(scored_domains, key=lambda item: (item.score, item.confidence), default=None)
    average = round(sum(score.score for score in result.domain_scores) / len(result.domain_scores))
    return ReportSnapshot(
        generated_at=generated_at or datetime.now(UTC),
        algorithm_version=result.algorithm_version,
        status=result.status,
        answered_question_count=result.answered_question_count,
        average_domain_score=average,
        weakest_domain=weakest.domain if weakest else None,
        strongest_domain=strongest.domain if strongest else None,
    )


def _summary(
    result: DiagnosisResult,
    domain_profiles: list[DomainReportProfile],
) -> StrengthWeaknessSummary:
    strength_domains = [
        profile.domain
        for profile in domain_profiles
        if profile.readiness == "strong" and profile.confidence >= 0.5
    ]
    weakness_domains = [
        profile.domain
        for profile in domain_profiles
        if profile.readiness == "weak" or profile.weak_concept_count > 0
    ]
    confidence_notes = [
        f"{profile.domain.value}: {profile.uncertainty}"
        for profile in domain_profiles
        if profile.confidence < 0.67
    ]
    return StrengthWeaknessSummary(
        strength_domains=strength_domains,
        weakness_domains=weakness_domains,
        weak_concept_tags=[weak.concept_slug for weak in result.weak_concepts],
        confidence_notes=confidence_notes,
    )


def _roadmap(result: DiagnosisResult) -> list[RoadmapItem]:
    items: list[RoadmapItem] = []
    seen: set[str] = set()
    for weak in sorted(
        result.weak_concepts,
        key=lambda item: (item.score, -item.evidence_weight, item.concept_slug),
    ):
        for prerequisite in weak.prerequisite_chain:
            if prerequisite not in seen:
                seen.add(prerequisite)
                items.append(
                    RoadmapItem(
                        order=len(items) + 1,
                        concept_slug=prerequisite,
                        reason=f"{weak.concept_slug} 학습 전 선행 개념",
                        priority_score=max(1, 100 - weak.score + 10),
                    )
                )
        if weak.concept_slug not in seen:
            seen.add(weak.concept_slug)
            items.append(
                RoadmapItem(
                    order=len(items) + 1,
                    concept_slug=weak.concept_slug,
                    domain=weak.domain,
                    prerequisite_chain=weak.prerequisite_chain,
                    reason="진단에서 취약 개념으로 확인됨",
                    priority_score=max(1, 100 - weak.score),
                )
            )
    return items


def _retest_targets(
    result: DiagnosisResult,
    domain_profiles: list[DomainReportProfile],
) -> list[RetestTarget]:
    targets: list[RetestTarget] = []
    for weak in result.weak_concepts[:5]:
        domain = weak.domain or _domain_for_weak(result, weak.concept_slug)
        if domain is None:
            continue
        targets.append(
            RetestTarget(
                domain=domain,
                concept_slug=weak.concept_slug,
                reason="취약 개념 보강 후 재진단",
                priority=len(targets) + 1,
            )
        )
    if targets:
        return targets

    low_confidence_domains = [
        profile
        for profile in domain_profiles
        if profile.confidence < 0.5 or profile.attempted_questions == 0
    ]
    return [
        RetestTarget(
            domain=profile.domain,
            reason="근거 문항이 부족해 신뢰도 보강 필요",
            priority=index + 1,
        )
        for index, profile in enumerate(low_confidence_domains[:3])
    ]


def _comparison(
    current: DiagnosisResult,
    previous: DiagnosisResult,
) -> ReportComparison:
    previous_scores = {score.domain: score for score in previous.domain_scores}
    domain_deltas = [
        DomainScoreDelta(
            domain=score.domain,
            previous_score=previous_scores[score.domain].score,
            current_score=score.score,
            delta=score.score - previous_scores[score.domain].score,
            previous_confidence=previous_scores[score.domain].confidence,
            current_confidence=score.confidence,
        )
        for score in current.domain_scores
        if score.domain in previous_scores
    ]
    previous_weak = {weak.concept_slug for weak in previous.weak_concepts}
    current_weak = {weak.concept_slug for weak in current.weak_concepts}
    return ReportComparison(
        domain_deltas=domain_deltas,
        resolved_weak_concepts=sorted(previous_weak - current_weak),
        new_weak_concepts=sorted(current_weak - previous_weak),
    )


def _weak_tags_by_domain(result: DiagnosisResult) -> dict[DiagnosisDomain, list[str]]:
    grouped: dict[DiagnosisDomain, list[str]] = {}
    for weak in result.weak_concepts:
        if weak.domain is not None:
            grouped.setdefault(weak.domain, []).append(weak.concept_slug)
    return grouped


def _domain_for_weak(result: DiagnosisResult, concept_slug: str) -> DiagnosisDomain | None:
    for weak in result.weak_concepts:
        if weak.concept_slug == concept_slug:
            return weak.domain
    return None


def _readiness(score: int, confidence: float) -> DomainReadiness:
    if confidence == 0:
        return "unmeasured"
    if score >= 75:
        return "strong"
    if score >= 60:
        return "developing"
    return "weak"


def _uncertainty(confidence: float, attempted_questions: int) -> str:
    if attempted_questions == 0:
        return "아직 진단 근거가 없습니다"
    if confidence < 0.5:
        return "근거 문항이 적어 불확실성이 높습니다"
    if confidence < 0.85:
        return "추가 문항으로 신뢰도를 높일 수 있습니다"
    return "현재 근거 기준 신뢰도가 높습니다"
