from collections import Counter
from pathlib import Path

import pytest
from pydantic import ValidationError

from ddep_backend.domains import DiagnosisDomain
from ddep_backend.question_db.cli import main
from ddep_backend.question_db.enums import AnswerType, Difficulty
from ddep_backend.question_db.grading import is_exact_short_answer_match
from ddep_backend.question_db.seed import (
    QuestionSeedManifest,
    SeedValidationError,
    load_and_validate_seed,
    validate_seed_manifest,
)

SEED_PATH = Path("seeds/phase01_questions.json")


def test_phase01_seed_distribution_contract() -> None:
    manifest = load_and_validate_seed(SEED_PATH)

    approved = manifest.approved_questions()
    assert len(approved) == 30

    domain_counts = Counter(question.domain for question in approved)
    assert domain_counts == {domain: 5 for domain in DiagnosisDomain}

    for domain in DiagnosisDomain:
        questions = [question for question in approved if question.domain is domain]
        answer_counts = Counter(question.answer_type for question in questions)
        difficulty_counts = Counter(question.difficulty for question in questions)
        assert answer_counts[AnswerType.SINGLE_CHOICE] + answer_counts[AnswerType.MULTI_SELECT] >= 3
        assert answer_counts[AnswerType.SHORT_ANSWER] >= 1
        assert difficulty_counts[Difficulty.EASY] >= 1
        assert difficulty_counts[Difficulty.MEDIUM] >= 2
        assert difficulty_counts[Difficulty.HARD] >= 1


def test_short_answer_exact_match_uses_trim_normalize_and_casefold() -> None:
    assert is_exact_short_answer_match(
        "  MAVLINK ",
        ["mavlink"],
        case_sensitive=False,
    )
    assert not is_exact_short_answer_match(
        "mav link",
        ["mavlink"],
        case_sensitive=False,
    )
    assert not is_exact_short_answer_match(
        "mavlink",
        ["MAVLink"],
        case_sensitive=True,
    )


def test_validation_rejects_unknown_question_tag() -> None:
    manifest = _manifest_with_question({"concept_tags": ["missing_tag"]})

    with pytest.raises(SeedValidationError, match="unknown concept tag 'missing_tag'"):
        validate_seed_manifest(manifest, enforce_distribution=False)


def test_validation_rejects_unknown_prerequisite_tag() -> None:
    manifest = _manifest_with_question({"prerequisites": ["missing_prerequisite"]})

    with pytest.raises(
        SeedValidationError,
        match="unknown prerequisite tag 'missing_prerequisite'",
    ):
        validate_seed_manifest(manifest, enforce_distribution=False)


def test_validation_rejects_approved_question_without_prerequisites() -> None:
    manifest = _manifest_with_question({"prerequisites": []})

    with pytest.raises(SeedValidationError, match="approved questions require prerequisites"):
        validate_seed_manifest(manifest, enforce_distribution=False)


def test_validation_allows_draft_without_prerequisites_only_when_included() -> None:
    manifest = _manifest_with_question(
        {
            "review_status": "draft",
            "prerequisites": [],
        }
    )

    with pytest.raises(
        SeedValidationError, match="empty draft prerequisites require --include-drafts"
    ):
        validate_seed_manifest(manifest, include_drafts=False, enforce_distribution=False)

    validate_seed_manifest(manifest, include_drafts=True, enforce_distribution=False)


def test_cli_include_drafts_allows_draft_only_seed(tmp_path: Path) -> None:
    question = _valid_question()
    question.update({"review_status": "draft", "prerequisites": []})
    manifest = QuestionSeedManifest.model_validate(
        {"concept_tags": _valid_tags(), "questions": [question]}
    )
    seed_path = tmp_path / "draft_seed.json"
    seed_path.write_text(manifest.model_dump_json(), encoding="utf-8")

    assert main(["validate", "--include-drafts", str(seed_path)]) == 0


def test_cli_validation_error_returns_nonzero(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    question = _valid_question()
    question["concept_tags"] = ["missing_tag"]
    seed_path = tmp_path / "invalid_seed.json"
    seed_path.write_text(
        QuestionSeedManifest.model_validate(
            {"concept_tags": _valid_tags(), "questions": [question]}
        ).model_dump_json(),
        encoding="utf-8",
    )

    assert main(["validate", str(seed_path)]) == 1
    captured = capsys.readouterr()
    assert "Seed validation failed" in captured.err
    assert "unknown concept tag 'missing_tag'" in captured.err


def test_validation_rejects_duplicate_and_cyclic_concept_tags() -> None:
    manifest = QuestionSeedManifest.model_validate(
        {
            "concept_tags": [
                {
                    "slug": "basic_physics",
                    "label": "Basic physics",
                    "description": "Base",
                    "domain": None,
                    "prerequisites": ["pid_control"],
                },
                {
                    "slug": "control_loop_basics",
                    "label": "Control loop basics",
                    "description": "Feedback basics",
                    "domain": None,
                    "prerequisites": ["basic_physics"],
                },
                {
                    "slug": "pid_control",
                    "label": "PID",
                    "description": "PID",
                    "domain": "control",
                    "prerequisites": ["control_loop_basics"],
                },
                {
                    "slug": "duplicate_tag",
                    "label": "Duplicate",
                    "description": "Duplicate",
                    "domain": None,
                    "prerequisites": [],
                },
                {
                    "slug": "duplicate_tag",
                    "label": "Duplicate again",
                    "description": "Duplicate again",
                    "domain": None,
                    "prerequisites": [],
                },
            ],
            "questions": [_valid_question()],
        }
    )

    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_manifest(manifest, enforce_distribution=False)

    message = str(exc_info.value)
    assert "duplicate tag slug" in message
    assert "cyclic prerequisites" in message


def test_question_answer_shape_rejects_invalid_single_choice() -> None:
    question = _valid_question()
    question["choices"] = [
        {"key": "A", "text": "A", "is_correct": True},
        {"key": "B", "text": "B", "is_correct": True},
    ]

    with pytest.raises(ValueError, match="single_choice requires exactly 1 correct choice"):
        QuestionSeedManifest.model_validate(
            {
                "concept_tags": _valid_tags(),
                "questions": [question],
            }
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("domain", "math_physics", "Input should be"),
        ("difficulty", "trivial", "Input should be"),
        ("answer_type", "freeform", "Input should be"),
        ("review_status", "published", "Input should be"),
        ("source_type", "blog", "Input should be"),
    ],
)
def test_controlled_enum_fields_reject_unknown_values(
    field: str,
    value: str,
    message: str,
) -> None:
    question = _valid_question()
    question[field] = value

    with pytest.raises(ValidationError, match=message):
        QuestionSeedManifest.model_validate(
            {"concept_tags": _valid_tags(), "questions": [question]}
        )


def test_tag_slug_must_be_lower_snake_ascii() -> None:
    tags = _valid_tags()
    tags[1]["slug"] = "Bad-Slug"

    with pytest.raises(ValidationError, match="lower snake_case ASCII"):
        QuestionSeedManifest.model_validate(
            {"concept_tags": tags, "questions": [_valid_question()]}
        )


def test_multi_select_requires_at_least_two_correct_choices() -> None:
    question = _valid_question()
    question.update(
        {
            "answer_type": "multi_select",
            "choices": [
                {"key": "A", "text": "A", "is_correct": True},
                {"key": "B", "text": "B", "is_correct": False},
                {"key": "C", "text": "C", "is_correct": False},
            ],
        }
    )

    with pytest.raises(ValueError, match="multi_select requires at least 2 correct choices"):
        QuestionSeedManifest.model_validate(
            {"concept_tags": _valid_tags(), "questions": [question]}
        )


def test_short_answer_rejects_choices_and_requires_answers() -> None:
    question = _valid_question()
    question.update({"answer_type": "short_answer", "accepted_answers": []})

    with pytest.raises(ValueError, match="short_answer must not define choices"):
        QuestionSeedManifest.model_validate(
            {"concept_tags": _valid_tags(), "questions": [question]}
        )

    question["choices"] = []
    with pytest.raises(ValueError, match="short_answer requires accepted_answers"):
        QuestionSeedManifest.model_validate(
            {"concept_tags": _valid_tags(), "questions": [question]}
        )


def _manifest_with_question(overrides: dict[str, object]) -> QuestionSeedManifest:
    question = _valid_question()
    question.update(overrides)
    return QuestionSeedManifest.model_validate(
        {
            "concept_tags": _valid_tags(),
            "questions": [question],
        }
    )


def _valid_tags() -> list[dict[str, object]]:
    return [
        {
            "slug": "control_loop_basics",
            "label": "Control loop basics",
            "description": "Feedback basics",
            "domain": None,
            "prerequisites": [],
        },
        {
            "slug": "pid_control",
            "label": "PID",
            "description": "PID control",
            "domain": "control",
            "prerequisites": ["control_loop_basics"],
        },
    ]


def _valid_question() -> dict[str, object]:
    return {
        "external_id": "unit-control-001",
        "domain": "control",
        "subdomain": "PID",
        "difficulty": "easy",
        "answer_type": "single_choice",
        "review_status": "approved",
        "source_type": "expert_review",
        "source_title": "Unit test source",
        "source_url": None,
        "source_reference": "UNIT-001",
        "concept_tags": ["pid_control"],
        "prerequisites": ["control_loop_basics"],
        "prompt": "What controller uses proportional, integral, and derivative terms?",
        "choices": [
            {"key": "A", "text": "PID", "is_correct": True},
            {"key": "B", "text": "HTML", "is_correct": False},
        ],
        "accepted_answers": [],
        "short_answer_case_sensitive": False,
        "explanation": "PID combines P, I, and D terms.",
    }
