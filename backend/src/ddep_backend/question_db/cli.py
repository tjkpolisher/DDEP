import argparse
import sys
from pathlib import Path

from ddep_backend.db.session import SessionLocal
from ddep_backend.question_db.importer import import_seed_manifest
from ddep_backend.question_db.seed import SeedValidationError, load_and_validate_seed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m ddep_backend.question_db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate a question seed file")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--include-drafts", action="store_true")

    import_parser = subparsers.add_parser("import", help="Validate and import a question seed file")
    import_parser.add_argument("path", type=Path)
    import_parser.add_argument("--include-drafts", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        manifest = load_and_validate_seed(
            args.path,
            include_drafts=args.include_drafts,
            enforce_distribution=not args.include_drafts,
        )
    except SeedValidationError as exc:
        print("Seed validation failed:", file=sys.stderr)
        for message in exc.messages:
            print(f"- {message}", file=sys.stderr)
        return 1

    if args.command == "validate":
        approved_count = len(manifest.approved_questions())
        print(f"Seed valid: {args.path} ({approved_count} approved questions)")
        return 0

    if args.command == "import":
        with SessionLocal.begin() as session:
            summary = import_seed_manifest(
                session,
                manifest,
                include_drafts=args.include_drafts,
            )
        print(
            "Import complete: "
            f"questions={summary.questions}, choices={summary.choices}, "
            f"concept_tags={summary.concept_tags}, "
            f"question_concept_tags={summary.question_concept_tags}, "
            f"question_prerequisite_tags={summary.question_prerequisite_tags}, "
            f"concept_tag_prerequisites={summary.concept_tag_prerequisites}",
        )
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2
