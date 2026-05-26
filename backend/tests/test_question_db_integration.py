import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from ddep_backend.core.config import get_settings
from ddep_backend.question_db.importer import import_seed_manifest
from ddep_backend.question_db.models import (
    ConceptTag,
    ConceptTagPrerequisite,
    Question,
    QuestionChoice,
    QuestionConceptTag,
    QuestionPrerequisiteTag,
)
from ddep_backend.question_db.seed import QuestionSeedManifest, load_and_validate_seed

SEED_PATH = Path("seeds/phase01_questions.json")


@pytest.mark.skipif(
    "DDEP_TEST_DATABASE_URL" not in os.environ,
    reason="DDEP_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)
def test_seed_import_is_idempotent_against_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = os.environ["DDEP_TEST_DATABASE_URL"]
    database_name = make_url(database_url).database
    if database_name == "ddep":
        pytest.fail("DDEP_TEST_DATABASE_URL must not point at the normal ddep database")

    monkeypatch.setenv("DDEP_DATABASE_URL", database_url)
    get_settings.cache_clear()
    try:
        _upgrade_database()
        manifest = load_and_validate_seed(SEED_PATH)
        engine = create_engine(database_url, pool_pre_ping=True)
        try:
            first_counts = _import_and_count(engine, manifest)
            second_counts = _import_and_count(engine, manifest)
        finally:
            engine.dispose()
    finally:
        get_settings.cache_clear()

    assert first_counts == second_counts
    assert first_counts["questions"] == 30
    assert first_counts["choices"] == 96
    assert first_counts["concept_tags"] >= 36


def _upgrade_database() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")


def _import_and_count(engine: Engine, manifest: QuestionSeedManifest) -> dict[str, int]:
    with Session(engine) as session:
        with session.begin():
            import_seed_manifest(session, manifest)
        return {
            "questions": session.scalar(select(func.count()).select_from(Question)) or 0,
            "choices": session.scalar(select(func.count()).select_from(QuestionChoice)) or 0,
            "concept_tags": session.scalar(select(func.count()).select_from(ConceptTag)) or 0,
            "question_concept_tags": session.scalar(
                select(func.count()).select_from(QuestionConceptTag)
            )
            or 0,
            "question_prerequisite_tags": session.scalar(
                select(func.count()).select_from(QuestionPrerequisiteTag)
            )
            or 0,
            "concept_tag_prerequisites": session.scalar(
                select(func.count()).select_from(ConceptTagPrerequisite)
            )
            or 0,
        }
