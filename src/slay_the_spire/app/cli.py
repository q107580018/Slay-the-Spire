from __future__ import annotations

import argparse

from slay_the_spire.adapters.textual.textual_runner import run_textual_session
from slay_the_spire.app.session import load_session, start_session


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slay-the-spire")
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new")
    new_parser.add_argument("--seed", type=int, required=True)
    new_parser.add_argument("--character", default="ironclad")
    new_parser.add_argument("--content-root")
    new_parser.add_argument("--save-path")

    load_parser = subparsers.add_parser("load")
    load_parser.add_argument("--content-root")
    load_parser.add_argument("--save-path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "new":
        session = start_session(
            seed=args.seed,
            character_id=args.character,
            content_root=args.content_root,
            save_path=args.save_path,
        )
        run_textual_session(session=session)
        return 0

    if args.command == "load":
        session = load_session(
            save_path=args.save_path,
            content_root=args.content_root,
        )
        run_textual_session(session=session)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
