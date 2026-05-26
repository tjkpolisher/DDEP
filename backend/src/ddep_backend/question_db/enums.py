from enum import StrEnum


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AnswerType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTI_SELECT = "multi_select"
    SHORT_ANSWER = "short_answer"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DEPRECATED = "deprecated"


class SourceType(StrEnum):
    OFFICIAL_DOCS = "official_docs"
    TECHNICAL_MANUAL = "technical_manual"
    COURSE_MATERIAL = "course_material"
    PAPER = "paper"
    INTERNAL_NOTE = "internal_note"
    EXPERT_REVIEW = "expert_review"
