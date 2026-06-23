from __future__ import annotations

import argparse
import json
from pathlib import Path

from .guard import assert_no_sentinels, event_to_json
from .mock_lab import run_mock_lab
from .report import write_html_report
from .summarize import load_events, summarize_events


def cmd_summarize(args: argparse.Namespace) -> int:
    summary = summarize_events(load_events(args.input))
    Path(args.output).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    summary = json.loads(Path(args.input).read_text(encoding="utf-8"))
    write_html_report(summary, args.output)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    events = load_events(args.input)
    serialized = "\n".join(event_to_json(event) for event in events)
    assert_no_sentinels(serialized, args.sentinel or [])
    return 0


def cmd_mock_lab(args: argparse.Namespace) -> int:
    evaluation = run_mock_lab(args.output_dir)
    print(f"mock lab passed: {evaluation['passed']}/{evaluation['total']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="llm-route-meter")
    sub = parser.add_subparsers(required=True)

    summarize = sub.add_parser("summarize")
    summarize.add_argument("--input", required=True)
    summarize.add_argument("--output", required=True)
    summarize.set_defaults(func=cmd_summarize)

    report = sub.add_parser("report")
    report.add_argument("--input", required=True)
    report.add_argument("--output", required=True)
    report.set_defaults(func=cmd_report)

    validate = sub.add_parser("validate")
    validate.add_argument("--input", required=True)
    validate.add_argument("--sentinel", action="append", default=[])
    validate.set_defaults(func=cmd_validate)

    mock_lab = sub.add_parser("mock-lab")
    mock_lab.add_argument("--output-dir", required=True)
    mock_lab.set_defaults(func=cmd_mock_lab)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
