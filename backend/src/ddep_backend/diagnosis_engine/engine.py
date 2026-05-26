from dataclasses import dataclass

from ddep_backend.diagnosis_engine.models import (
    ConceptMastery,
    DiagnosisResult,
    DiagnosisScoringConfig,
    DiagnosisSessionState,
    DomainScore,
    EngineQuestion,
    QuestionOutcome,
    SubmittedAnswer,
    WeakConcept,
)
from ddep_backend.domains import DIAGNOSIS_DOMAINS, DiagnosisDomain
from ddep_backend.question_db.enums import AnswerType, Difficulty, ReviewStatus
from ddep_backend.question_db.grading import is_exact_short_answer_match

DEFAULT_CONFIG = DiagnosisScoringConfig()

_DOMAIN_ORDER = {definition.slug: index for index, definition in enumerate(DIAGNOSIS_DOMAINS)}
_DIFFICULTY_ORDER = {
    Difficulty.EASY: 0,
    Difficulty.MEDIUM: 1,
    Difficulty.HARD: 2,
}


@dataclass
class _Evidence:
    weighted_correct: float = 0.0
    weighted_attempts: float = 0.0
    attempted_questions: int = 0

    def add(self, *, is_correct: bool, weight: float) -> None:
        self.weighted_attempts += weight
        if is_correct:
            self.weighted_correct += weight
        self.attempted_questions += 1


def grade_submitted_answer(
    question: EngineQuestion,
    answer: SubmittedAnswer,
    config: DiagnosisScoringConfig = DEFAULT_CONFIG,
) -> QuestionOutcome:
    if answer.question_external_id != question.external_id:
        raise ValueError(
            "submitted answer question_external_id does not match engine question external_id"
        )

    submitted_choice_keys = _unique_in_order(answer.choice_keys)
    correct_choice_keys = question.correct_choice_keys
    is_correct = False

    if question.answer_type is AnswerType.SINGLE_CHOICE:
        is_correct = (
            len(submitted_choice_keys) == 1 and submitted_choice_keys == correct_choice_keys
        )
    elif question.answer_type is AnswerType.MULTI_SELECT:
        is_correct = set(submitted_choice_keys) == set(correct_choice_keys) and len(
            submitted_choice_keys
        ) == len(correct_choice_keys)
    elif question.answer_type is AnswerType.SHORT_ANSWER:
        is_correct = answer.short_answer is not None and is_exact_short_answer_match(
            answer.short_answer,
            question.accepted_answers,
            case_sensitive=question.short_answer_case_sensitive,
        )

    return QuestionOutcome(
        question_external_id=question.external_id,
        domain=question.domain,
        difficulty=question.difficulty,
        concept_tags=_unique_in_order(question.concept_tags),
        prerequisite_tags=_unique_in_order(question.prerequisite_tags),
        is_correct=is_correct,
        evidence_weight=config.difficulty_weights[question.difficulty],
        submitted_choice_keys=submitted_choice_keys,
        submitted_short_answer=answer.short_answer,
        correct_choice_keys=correct_choice_keys,
    )


def apply_outcome(
    state: DiagnosisSessionState,
    outcome: QuestionOutcome,
) -> DiagnosisSessionState:
    answered_question_ids = [
        question_id
        for question_id in state.answered_question_ids
        if question_id != outcome.question_external_id
    ]
    answered_question_ids.append(outcome.question_external_id)

    outcomes = dict(state.outcomes)
    outcomes[outcome.question_external_id] = outcome

    consecutive_correct_by_domain, consecutive_correct_by_concept = _rebuild_streaks(
        answered_question_ids,
        outcomes,
    )

    return state.model_copy(
        update={
            "answered_question_ids": answered_question_ids,
            "outcomes": outcomes,
            "last_outcome": outcome,
            "consecutive_correct_by_domain": consecutive_correct_by_domain,
            "consecutive_correct_by_concept": consecutive_correct_by_concept,
        }
    )


def complete_session(state: DiagnosisSessionState) -> DiagnosisSessionState:
    return state.model_copy(update={"status": "completed"})


def calculate_result(
    question_pool: list[EngineQuestion],
    state: DiagnosisSessionState,
    prerequisite_graph: dict[str, list[str]],
    config: DiagnosisScoringConfig = DEFAULT_CONFIG,
) -> DiagnosisResult:
    domain_evidence = {definition.slug: _Evidence() for definition in DIAGNOSIS_DOMAINS}
    concept_evidence: dict[str, _Evidence] = {}

    for outcome in _ordered_outcomes(state):
        domain_evidence[outcome.domain].add(
            is_correct=outcome.is_correct,
            weight=outcome.evidence_weight,
        )
        for concept_slug in _unique_in_order(outcome.concept_tags):
            concept_evidence.setdefault(concept_slug, _Evidence()).add(
                is_correct=outcome.is_correct,
                weight=outcome.evidence_weight,
            )

    domain_scores = [
        DomainScore(
            domain=domain,
            score=_score(evidence, config),
            confidence=_confidence(evidence.weighted_attempts, config),
            evidence_weight=evidence.weighted_attempts,
            weighted_correct=evidence.weighted_correct,
            weighted_attempts=evidence.weighted_attempts,
            attempted_questions=evidence.attempted_questions,
        )
        for domain, evidence in domain_evidence.items()
    ]

    concept_domain = _concept_domain_map(question_pool)
    concept_mastery = [
        ConceptMastery(
            concept_slug=concept_slug,
            score=_score(evidence, config),
            confidence=_confidence(evidence.weighted_attempts, config),
            evidence_weight=evidence.weighted_attempts,
            weighted_correct=evidence.weighted_correct,
            weighted_attempts=evidence.weighted_attempts,
            attempted_questions=evidence.attempted_questions,
        )
        for concept_slug, evidence in sorted(concept_evidence.items())
    ]

    weak_concepts = [
        WeakConcept(
            concept_slug=mastery.concept_slug,
            score=mastery.score,
            confidence=mastery.confidence,
            evidence_weight=mastery.evidence_weight,
            prerequisite_chain=build_prerequisite_chain(mastery.concept_slug, prerequisite_graph),
            domain=concept_domain.get(mastery.concept_slug),
        )
        for mastery in concept_mastery
        if mastery.score < config.weak_threshold
        and mastery.evidence_weight >= config.min_weak_evidence_weight
    ]
    weak_concepts.sort(key=lambda item: (item.score, item.confidence, item.concept_slug))

    return DiagnosisResult(
        algorithm_version=config.algorithm_version,
        status=state.status,
        answered_question_count=len(state.answered_question_ids),
        domain_scores=domain_scores,
        concept_mastery=concept_mastery,
        weak_concepts=weak_concepts,
    )


def build_prerequisite_chain(
    concept_slug: str,
    prerequisite_graph: dict[str, list[str]],
) -> list[str]:
    visited: set[str] = set()
    chain: list[str] = []

    def visit(slug: str, stack: set[str]) -> None:
        for prerequisite_slug in sorted(prerequisite_graph.get(slug, [])):
            if prerequisite_slug in stack:
                continue
            if prerequisite_slug not in visited:
                visited.add(prerequisite_slug)
                chain.append(prerequisite_slug)
                visit(prerequisite_slug, {*stack, prerequisite_slug})

    visit(concept_slug, {concept_slug})
    return chain


def select_next_candidates(
    question_pool: list[EngineQuestion],
    state: DiagnosisSessionState,
    result: DiagnosisResult,
    prerequisite_graph: dict[str, list[str]],
    limit: int = 1,
) -> list[str]:
    if limit <= 0:
        return []

    answered = set(state.answered_question_ids)
    candidates = [
        question
        for question in question_pool
        if question.external_id not in answered and question.review_status is ReviewStatus.APPROVED
    ]
    weak_by_slug = {weak.concept_slug: weak for weak in result.weak_concepts}
    mastered_slugs = {
        mastery.concept_slug
        for mastery in result.concept_mastery
        if mastery.score >= DEFAULT_CONFIG.weak_threshold
        and mastery.evidence_weight >= DEFAULT_CONFIG.min_weak_evidence_weight
    }

    ranked = [
        (
            _candidate_rank(question, state, weak_by_slug, mastered_slugs, prerequisite_graph),
            question,
        )
        for question in candidates
    ]
    ranked.sort(
        key=lambda item: (
            item[0][0],
            _DOMAIN_ORDER[item[1].domain],
            item[0][1],
            _DIFFICULTY_ORDER[item[1].difficulty],
            item[1].external_id,
        )
    )
    return [question.external_id for _, question in ranked[:limit]]


def _candidate_rank(
    question: EngineQuestion,
    state: DiagnosisSessionState,
    weak_by_slug: dict[str, WeakConcept],
    mastered_slugs: set[str],
    prerequisite_graph: dict[str, list[str]],
) -> tuple[int, float]:
    last_outcome = state.last_outcome
    question_concepts = set(question.concept_tags)
    question_prerequisites = set(question.prerequisite_tags)

    if last_outcome is not None and not last_outcome.is_correct:
        wrong_prerequisites: set[str] = set()
        for concept_slug in last_outcome.concept_tags:
            wrong_prerequisites.update(build_prerequisite_chain(concept_slug, prerequisite_graph))
        if question_concepts & wrong_prerequisites:
            return (0, 0.0)

    if last_outcome is not None and last_outcome.is_correct:
        domain_streak = state.consecutive_correct_by_domain.get(last_outcome.domain.value, 0)
        concept_streak = max(
            (
                state.consecutive_correct_by_concept.get(concept_slug, 0)
                for concept_slug in last_outcome.concept_tags
            ),
            default=0,
        )
        if domain_streak >= 2 or concept_streak >= 2:
            is_next_difficulty = (
                _DIFFICULTY_ORDER[question.difficulty] > _DIFFICULTY_ORDER[last_outcome.difficulty]
            )
            is_same_concept = bool(question_concepts & set(last_outcome.concept_tags))
            if is_next_difficulty and (question.domain == last_outcome.domain or is_same_concept):
                return (1, 0.0)

    if mastered_slugs:
        direct_prerequisites = {
            prerequisite
            for concept_slug in question.concept_tags
            for prerequisite in prerequisite_graph.get(concept_slug, [])
        }
        if (direct_prerequisites | question_prerequisites) & mastered_slugs:
            return (2, 0.0)

    weak_matches = question_concepts & set(weak_by_slug)
    if weak_matches:
        lowest_confidence = min(weak_by_slug[slug].confidence for slug in weak_matches)
        return (3, lowest_confidence)

    return (4, 0.0)


def _ordered_outcomes(state: DiagnosisSessionState) -> list[QuestionOutcome]:
    return [
        state.outcomes[question_id]
        for question_id in state.answered_question_ids
        if question_id in state.outcomes
    ]


def _rebuild_streaks(
    answered_question_ids: list[str],
    outcomes: dict[str, QuestionOutcome],
) -> tuple[dict[str, int], dict[str, int]]:
    consecutive_correct_by_domain: dict[str, int] = {}
    consecutive_correct_by_concept: dict[str, int] = {}
    for question_id in answered_question_ids:
        outcome = outcomes[question_id]
        domain_key = outcome.domain.value
        consecutive_correct_by_domain[domain_key] = (
            consecutive_correct_by_domain.get(domain_key, 0) + 1 if outcome.is_correct else 0
        )
        for concept_slug in outcome.concept_tags:
            consecutive_correct_by_concept[concept_slug] = (
                consecutive_correct_by_concept.get(concept_slug, 0) + 1 if outcome.is_correct else 0
            )
    return consecutive_correct_by_domain, consecutive_correct_by_concept


def _score(evidence: _Evidence, config: DiagnosisScoringConfig) -> int:
    return round(
        100
        * (config.alpha + evidence.weighted_correct)
        / (config.alpha + config.beta + evidence.weighted_attempts)
    )


def _confidence(evidence_weight: float, config: DiagnosisScoringConfig) -> float:
    return min(1.0, evidence_weight / config.full_confidence_evidence_weight)


def _concept_domain_map(question_pool: list[EngineQuestion]) -> dict[str, DiagnosisDomain]:
    concept_domain: dict[str, DiagnosisDomain] = {}
    for question in question_pool:
        for concept_slug in question.concept_tags:
            concept_domain.setdefault(concept_slug, question.domain)
    return concept_domain


def _unique_in_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
