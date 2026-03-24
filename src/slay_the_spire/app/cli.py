from __future__ import annotations

import argparse

from slay_the_spire.app.session import interactive_loop, load_session, start_session


class TerminalInputPort:
    def read(self, prompt: str = "") -> str:
        return input(prompt)


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
        interactive_loop(session=session, input_port=TerminalInputPort(), output_writer=print)
        return 0

    if args.command == "load":
        session = load_session(
            save_path=args.save_path,
            content_root=args.content_root,
        )
        interactive_loop(session=session, input_port=TerminalInputPort(), output_writer=print)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
