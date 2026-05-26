import unicodedata


def normalize_short_answer(value: str, *, case_sensitive: bool) -> str:
    normalized = unicodedata.normalize("NFKC", value.strip())
    if case_sensitive:
        return normalized
    return normalized.casefold()


def is_exact_short_answer_match(
    response: str,
    accepted_answers: list[str],
    *,
    case_sensitive: bool,
) -> bool:
    normalized_response = normalize_short_answer(response, case_sensitive=case_sensitive)
    normalized_answers = {
        normalize_short_answer(answer, case_sensitive=case_sensitive) for answer in accepted_answers
    }
    return normalized_response in normalized_answers
