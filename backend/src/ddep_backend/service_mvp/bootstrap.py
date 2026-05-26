import argparse
import os

from sqlalchemy import select

from ddep_backend.core.config import get_settings
from ddep_backend.db.session import SessionLocal
from ddep_backend.service_mvp.models import InviteCode
from ddep_backend.service_mvp.security import hash_secret


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ddep_backend.service_mvp.bootstrap")
    parser.add_argument(
        "--code",
        default=os.environ.get("DDEP_BOOTSTRAP_INVITE_CODE", "beta"),
        help="Plain invite code to hash and seed",
    )
    parser.add_argument(
        "--label",
        default=os.environ.get("DDEP_BOOTSTRAP_INVITE_LABEL", "Local beta"),
        help="Human-readable invite label",
    )
    parser.add_argument(
        "--operator",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("DDEP_BOOTSTRAP_INVITE_OPERATOR", default=True),
        help="Whether this invite grants ops-event access",
    )
    parser.add_argument("--max-uses", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    code_hash = hash_secret(args.code, settings)
    with SessionLocal.begin() as session:
        invite = session.scalar(select(InviteCode).where(InviteCode.code_hash == code_hash))
        if invite is None:
            invite = InviteCode(code_hash=code_hash, label=args.label)
            session.add(invite)
        invite.label = args.label
        invite.is_active = True
        invite.grants_operator = args.operator
        invite.max_uses = args.max_uses
    print(
        "Invite ready: "
        f"label={args.label!r}, operator={args.operator}, "
        "code=<redacted>",
    )
    return 0


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
