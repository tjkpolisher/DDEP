from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from ddep_backend.core.config import get_settings


def create_db_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session]:
    with SessionLocal() as session:
        yield session
