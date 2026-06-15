#!/usr/bin/env python3
"""Record and verify one native imagegen result."""

from __future__ import annotations

import argparse
import json
import sys

from plan_io import (
    PlanError,
    find_illustration,
    read_plan,
    resolve_article_path,
    resolve_artifact_path,
    sha256_file,
    validate_prompt_file,
    validate_png,
    write_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--id", required=True)
    outcome = parser.add_mutually_exclusive_group(required=True)
    outcome.add_argument("--success", action="store_true")
    outcome.add_argument("--failure", action="store_true")
    parser.add_argument("--error")
    parser.add_argument("--prompt-sha256")
    parser.add_argument("--qa", choices=("not_checked", "passed", "needs_review"), default="not_checked")
    parser.add_argument("--qa-notes")
    args = parser.parse_args()

    try:
        plan = read_plan(args.plan)
        article_path = resolve_article_path(args.plan, plan)
        if sha256_file(article_path) != plan["article"]["sha256"]:
            raise PlanError("Article SHA-256 does not match the plan.")
        item = find_illustration(plan, args.id)
        if item.get("approval") != "approved":
            raise PlanError("Only approved illustrations can record generation results.")
        generation = item["generation"]
        generation["attempts"] = int(generation.get("attempts", 0)) + 1

        if args.failure:
            if not args.error:
                raise PlanError("--error is required with --failure")
            generation["status"] = "failed"
            generation["prompt_sha256"] = None
            generation["error"] = args.error
            item["qa"]["status"] = "not_checked"
            item["qa"]["notes"] = None
        else:
            if not args.prompt_sha256:
                raise PlanError("--prompt-sha256 is required with --success")
            prompt_path = resolve_artifact_path(args.plan, plan, item["prompt_file"])
            output_path = resolve_artifact_path(args.plan, plan, item["output_file"])
            if not prompt_path.is_file():
                raise PlanError(f"Prompt file not found: {prompt_path}")
            validate_prompt_file(prompt_path, item, plan)
            prompt_hash = sha256_file(prompt_path)
            if args.prompt_sha256 != prompt_hash:
                raise PlanError("Prompt SHA-256 does not match the generation task.")
            valid, error, size = validate_png(output_path)
            if not valid:
                raise PlanError(error or f"Invalid PNG: {output_path}")
            generation["status"] = "generated"
            generation["prompt_sha256"] = prompt_hash
            generation["error"] = None
            item["qa"]["status"] = args.qa
            item["qa"]["notes"] = args.qa_notes
        item["insertion"]["status"] = "not_started"
        item["insertion"]["error"] = None

        write_plan(args.plan, plan)
        result = {
            "id": args.id,
            "generation": item["generation"],
            "qa": item["qa"],
        }
        if args.success:
            result["bytes"] = size
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (KeyError, OSError, PlanError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
