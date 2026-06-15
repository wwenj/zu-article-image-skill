#!/usr/bin/env python3
"""Validate an article-illustrator plan."""

from __future__ import annotations

import argparse
import json
import sys

from plan_io import PlanError, read_plan, validate_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--stage", choices=("plan", "generation", "insertion"), default="plan")
    args = parser.parse_args()
    try:
        result = validate_plan(read_plan(args.plan), args.plan, args.stage)
    except PlanError as exc:
        result = {
            "valid": False,
            "stage": args.stage,
            "global_errors": [{"scope": "plan", "code": "plan", "message": str(exc)}],
            "item_errors": [],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())

