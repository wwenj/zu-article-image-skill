#!/usr/bin/env python3
"""Find an exact Markdown anchor, including multiline anchors and CRLF articles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from plan_io import find_anchor_matches, line_number_at, read_text_preserving_newlines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("article")
    parser.add_argument("anchor")
    args = parser.parse_args()
    path = Path(args.article).resolve()
    if not path.is_file():
        print(json.dumps({"valid": False, "matches": 0, "error": f"Article not found: {path}"}))
        return 1
    try:
        text = read_text_preserving_newlines(path)
    except OSError as exc:
        print(json.dumps({"valid": False, "matches": 0, "error": str(exc)}))
        return 1
    matches = find_anchor_matches(text, args.anchor)
    result = {
        "valid": len(matches) == 1,
        "matches": len(matches),
        "locations": [
            {
                "start_offset": start,
                "end_offset": end,
                "start_line": line_number_at(text, start),
                "end_line": line_number_at(text, end),
            }
            for start, end in matches
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
