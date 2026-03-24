from __future__ import annotations

import argparse

from slay_the_spire.app.session import render_session, start_session


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slay-the-spire")
    subparsers = parser.add_subparsers(dest="command")

    new_parser = subparsers.add_parser("new")
    new_parser.add_argument("--seed", type=int, required=True)
    new_parser.add_argument("--character", default="ironclad")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "new":
        session = start_session(seed=args.seed, character_id=args.character)
        print(render_session(session))
        return 0

    parser.print_help()
    return 0
