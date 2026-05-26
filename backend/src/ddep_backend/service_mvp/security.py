from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from ddep_backend.core.config import Settings


def hash_secret(value: str, settings: Settings) -> str:
    return sha256(f"{settings.access_token_secret}:{value}".encode()).hexdigest()


def new_bearer_token() -> str:
    return token_urlsafe(32)


def session_expiry(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(hours=settings.access_token_ttl_hours)
