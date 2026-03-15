from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from resume_parser.pipeline import parse_resume_file
else:
    from .pipeline import parse_resume_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Parse a PDF or text resume into structured JSON."
    )
    parser.add_argument("input", help="Path to the input PDF or text file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Optional output JSON file path. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Include raw text, cleaned lines, sections and confidence scores.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = parse_resume_file(args.input)
    payload = result.to_dict(include_debug=args.debug)
    output = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
