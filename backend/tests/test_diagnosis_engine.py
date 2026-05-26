from ddep_backend.diagnosis_engine import (
    DiagnosisSessionState,
    EngineChoice,
    EngineQuestion,
    SubmittedAnswer,
    apply_outcome,
    build_prerequisite_chain,
    calculate_result,
    complete_session,
    grade_submitted_answer,
    select_next_candidates,
)
from ddep_backend.domains import DiagnosisDomain
from ddep_backend.question_db.enums import AnswerType, Difficulty, ReviewStatus


def test_grades_single_choice_only_when_exactly_one_correct_key_is_submitted() -> None:
    question = _question(
        "q1",
        AnswerType.SINGLE_CHOICE,
        choices=[
            EngineChoice(key="A", text="Correct", is_correct=True),
            EngineChoice(key="B", text="Wrong"),
        ],
    )

    assert grade_submitted_answer(
        question, SubmittedAnswer(question_external_id="q1", choice_keys=["A"])
    ).is_correct
    assert not grade_submitted_answer(
        question,
        SubmittedAnswer(question_external_id="q1", choice_keys=["A", "B"]),
    ).is_correct
    assert not grade_submitted_answer(
        question, SubmittedAnswer(question_external_id="q1", choice_keys=[])
    ).is_correct


def test_grades_multi_select_by_exact_set_without_partial_credit() -> None:
    question = _question(
        "q1",
        AnswerType.MULTI_SELECT,
        choices=[
            EngineChoice(key="A", text="Correct", is_correct=True),
            EngineChoice(key="B", text="Correct", is_correct=True),
            EngineChoice(key="C", text="Wrong"),
        ],
    )

    assert grade_submitted_answer(
        question,
        SubmittedAnswer(question_external_id="q1", choice_keys=["B", "A", "A"]),
    ).is_correct
    assert not grade_submitted_answer(
        question,
        SubmittedAnswer(question_external_id="q1", choice_keys=["A"]),
    ).is_correct
    assert not grade_submitted_answer(
        question,
        SubmittedAnswer(question_external_id="q1", choice_keys=["A", "B", "C"]),
    ).is_correct


def test_grades_short_answer_with_existing_exact_match_helper() -> None:
    question = _question(
        "q1",
        AnswerType.SHORT_ANSWER,
        accepted_answers=["MAVLink", "mavlink2"],
    )
    case_sensitive = question.model_copy(update={"short_answer_case_sensitive": True})

    assert grade_submitted_answer(
        question,
        SubmittedAnswer(question_external_id="q1", short_answer="  mavlink "),
    ).is_correct
    assert not grade_submitted_answer(
        question,
        SubmittedAnswer(question_external_id="q1", short_answer="mav link"),
    ).is_correct
    assert not grade_submitted_answer(
        case_sensitive,
        SubmittedAnswer(question_external_id="q1", short_answer="mavlink"),
    ).is_correct


def test_calculates_bayes_lite_scores_and_confidence() -> None:
    easy = _question("easy", AnswerType.SINGLE_CHOICE, difficulty=Difficulty.EASY)
    hard = _question(
        "hard",
        AnswerType.SINGLE_CHOICE,
        difficulty=Difficulty.HARD,
        concept_tags=["advanced"],
    )
    state = DiagnosisSessionState()
    state = apply_outcome(
        state,
        grade_submitted_answer(
            easy, SubmittedAnswer(question_external_id="easy", choice_keys=["A"])
        ),
    )
    state = apply_outcome(
        state,
        grade_submitted_answer(
            hard, SubmittedAnswer(question_external_id="hard", choice_keys=["B"])
        ),
    )

    result = calculate_result([easy, hard], state, {})
    domain_score = result.domain_scores[0]

    assert domain_score.domain is DiagnosisDomain.AIRFRAME_AERODYNAMICS
    assert domain_score.score == 45
    assert domain_score.evidence_weight == 2.0
    assert domain_score.weighted_correct == 0.8
    assert domain_score.confidence == 2.0 / 3.0


def test_zero_answer_result_includes_all_six_domains() -> None:
    result = calculate_result([], DiagnosisSessionState(), {})

    assert [score.domain for score in result.domain_scores] == list(DiagnosisDomain)
    assert {score.score for score in result.domain_scores} == {50}
    assert {score.confidence for score in result.domain_scores} == {0.0}
    assert result.answered_question_count == 0


def test_multi_tag_question_counts_domain_once_and_each_concept_once() -> None:
    question = _question(
        "q1",
        AnswerType.SINGLE_CHOICE,
        concept_tags=["lift", "drag"],
    )
    state = apply_outcome(
        DiagnosisSessionState(),
        grade_submitted_answer(
            question, SubmittedAnswer(question_external_id="q1", choice_keys=["A"])
        ),
    )

    result = calculate_result([question], state, {})

    assert result.domain_scores[0].attempted_questions == 1
    assert {
        mastery.concept_slug: mastery.attempted_questions for mastery in result.concept_mastery
    } == {
        "drag": 1,
        "lift": 1,
    }


def test_weak_concepts_require_threshold_and_minimum_evidence() -> None:
    easy_wrong = _question("easy", AnswerType.SINGLE_CHOICE, difficulty=Difficulty.EASY)
    medium_wrong = easy_wrong.model_copy(
        update={"external_id": "medium", "difficulty": Difficulty.MEDIUM}
    )
    state = apply_outcome(
        DiagnosisSessionState(),
        grade_submitted_answer(
            easy_wrong, SubmittedAnswer(question_external_id="easy", choice_keys=["B"])
        ),
    )
    result = calculate_result([easy_wrong], state, {})
    assert result.weak_concepts == []

    state = apply_outcome(
        state,
        grade_submitted_answer(
            medium_wrong, SubmittedAnswer(question_external_id="medium", choice_keys=["B"])
        ),
    )
    result = calculate_result([easy_wrong, medium_wrong], state, {"lift": ["basic_physics"]})
    assert [weak.concept_slug for weak in result.weak_concepts] == ["lift"]
    assert result.weak_concepts[0].prerequisite_chain == ["basic_physics"]


def test_prerequisite_chain_is_sorted_deduplicated_and_cycle_safe() -> None:
    graph = {
        "advanced": ["z_base", "a_base"],
        "a_base": ["shared"],
        "z_base": ["shared"],
        "shared": ["advanced"],
    }

    assert build_prerequisite_chain("advanced", graph) == ["a_base", "shared", "z_base"]


def test_apply_outcome_tracks_state_streaks_and_completion_is_explicit() -> None:
    question = _question("q1", AnswerType.SINGLE_CHOICE)
    correct = grade_submitted_answer(
        question, SubmittedAnswer(question_external_id="q1", choice_keys=["A"])
    )
    wrong = grade_submitted_answer(
        question, SubmittedAnswer(question_external_id="q1", choice_keys=["B"])
    )

    state = apply_outcome(DiagnosisSessionState(), correct)
    state = apply_outcome(state, correct)
    assert state.answered_question_ids == ["q1"]
    assert state.consecutive_correct_by_domain[DiagnosisDomain.AIRFRAME_AERODYNAMICS.value] == 1

    state = apply_outcome(state, wrong)
    assert state.status == "active"
    assert state.consecutive_correct_by_domain[DiagnosisDomain.AIRFRAME_AERODYNAMICS.value] == 0
    assert complete_session(state).status == "completed"


def test_selects_wrong_answer_prerequisite_fallback_first() -> None:
    advanced = _question("advanced", AnswerType.SINGLE_CHOICE, concept_tags=["advanced"])
    base = _question("base", AnswerType.SINGLE_CHOICE, concept_tags=["base"])
    fallback = _question("fallback", AnswerType.SINGLE_CHOICE, concept_tags=["other"])
    state = apply_outcome(
        DiagnosisSessionState(),
        grade_submitted_answer(
            advanced, SubmittedAnswer(question_external_id="advanced", choice_keys=["B"])
        ),
    )
    result = calculate_result([advanced, base, fallback], state, {"advanced": ["base"]})

    assert select_next_candidates(
        [advanced, base, fallback], state, result, {"advanced": ["base"]}
    ) == ["base"]


def test_selects_difficulty_escalation_before_deeper_adjacent_concept() -> None:
    easy_1 = _question("easy-1", AnswerType.SINGLE_CHOICE, difficulty=Difficulty.EASY)
    easy_2 = _question("easy-2", AnswerType.SINGLE_CHOICE, difficulty=Difficulty.EASY)
    medium_same = _question("medium-same", AnswerType.SINGLE_CHOICE, difficulty=Difficulty.MEDIUM)
    deeper = _question(
        "deeper",
        AnswerType.SINGLE_CHOICE,
        difficulty=Difficulty.EASY,
        concept_tags=["deeper"],
    )
    state = DiagnosisSessionState()
    for question in (easy_1, easy_2):
        state = apply_outcome(
            state,
            grade_submitted_answer(
                question,
                SubmittedAnswer(question_external_id=question.external_id, choice_keys=["A"]),
            ),
        )
    result = calculate_result([easy_1, easy_2, medium_same, deeper], state, {"deeper": ["lift"]})

    assert select_next_candidates(
        [easy_1, easy_2, medium_same, deeper],
        state,
        result,
        {"deeper": ["lift"]},
    ) == ["medium-same"]


def test_selects_weak_concept_before_fallback_and_excludes_answered_or_unapproved() -> None:
    weak = _question("weak", AnswerType.SINGLE_CHOICE)
    weak_next = _question("weak-next", AnswerType.SINGLE_CHOICE)
    answered_again = _question("answered-again", AnswerType.SINGLE_CHOICE)
    draft = _question("draft", AnswerType.SINGLE_CHOICE).model_copy(
        update={"review_status": ReviewStatus.DRAFT}
    )
    fallback = _question(
        "fallback",
        AnswerType.SINGLE_CHOICE,
        domain=DiagnosisDomain.SOFTWARE,
        concept_tags=["other"],
    )
    state = apply_outcome(
        DiagnosisSessionState(),
        grade_submitted_answer(
            weak, SubmittedAnswer(question_external_id="weak", choice_keys=["B"])
        ),
    )
    state = apply_outcome(
        state,
        grade_submitted_answer(
            answered_again,
            SubmittedAnswer(question_external_id="answered-again", choice_keys=["B"]),
        ),
    )
    result = calculate_result([weak, weak_next, answered_again, draft, fallback], state, {})

    assert select_next_candidates(
        [weak, weak_next, answered_again, draft, fallback], state, result, {}
    ) == ["weak-next"]


def test_candidate_tie_break_is_deterministic() -> None:
    software = _question(
        "b-software",
        AnswerType.SINGLE_CHOICE,
        domain=DiagnosisDomain.SOFTWARE,
        difficulty=Difficulty.EASY,
        concept_tags=["software"],
    )
    airframe = _question(
        "a-airframe",
        AnswerType.SINGLE_CHOICE,
        domain=DiagnosisDomain.AIRFRAME_AERODYNAMICS,
        difficulty=Difficulty.EASY,
        concept_tags=["airframe"],
    )
    result = calculate_result([software, airframe], DiagnosisSessionState(), {})

    assert select_next_candidates(
        [software, airframe], DiagnosisSessionState(), result, {}, limit=2
    ) == [
        "a-airframe",
        "b-software",
    ]


def test_candidate_exhaustion_does_not_complete_session() -> None:
    answered = _question("answered", AnswerType.SINGLE_CHOICE)
    state = apply_outcome(
        DiagnosisSessionState(),
        grade_submitted_answer(
            answered,
            SubmittedAnswer(question_external_id="answered", choice_keys=["A"]),
        ),
    )
    result = calculate_result([answered], state, {})

    assert select_next_candidates([answered], state, result, {}) == []
    assert state.status == "active"


def _question(
    external_id: str,
    answer_type: AnswerType,
    *,
    domain: DiagnosisDomain = DiagnosisDomain.AIRFRAME_AERODYNAMICS,
    difficulty: Difficulty = Difficulty.MEDIUM,
    concept_tags: list[str] | None = None,
    choices: list[EngineChoice] | None = None,
    accepted_answers: list[str] | None = None,
) -> EngineQuestion:
    return EngineQuestion(
        external_id=external_id,
        domain=domain,
        difficulty=difficulty,
        answer_type=answer_type,
        concept_tags=concept_tags or ["lift"],
        choices=choices
        or [
            EngineChoice(key="A", text="Correct", is_correct=True),
            EngineChoice(key="B", text="Wrong"),
        ],
        accepted_answers=accepted_answers or [],
    )
