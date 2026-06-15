#!/usr/bin/env python3
"""Build deterministic native-imagegen tasks from approved illustrations."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from plan_io import (
    PlanError,
    atomic_write_text,
    find_anchor_matches,
    read_plan,
    read_text_preserving_newlines,
    resolve_article_path,
    resolve_artifact_path,
    sha256_file,
    validate_plan,
    validate_png,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 4:
        print(json.dumps({"valid": False, "error": "--batch-size must be between 1 and 4"}))
        return 1

    try:
        plan = read_plan(args.plan)
        validation = validate_plan(plan, args.plan, "generation")
        if validation["global_errors"]:
            raise PlanError(validation["global_errors"][0]["message"])
        article_text = read_text_preserving_newlines(resolve_article_path(args.plan, plan))
        errors_by_scope: dict[str, list[str]] = defaultdict(list)
        for error in validation["item_errors"]:
            errors_by_scope[error["scope"]].append(error["message"])
        tasks: list[dict[str, object]] = []
        skipped: list[dict[str, str]] = []
        protected_paths = {
            Path(args.plan).resolve(),
            resolve_article_path(args.plan, plan),
        }
        for item in plan.get("illustrations", []):
            if not isinstance(item, dict):
                continue
            for field in ("prompt_file", "output_file"):
                value = item.get(field)
                if not isinstance(value, str):
                    continue
                try:
                    protected_paths.add(resolve_artifact_path(args.plan, plan, value))
                except (OSError, PlanError):
                    continue

        for index, item in enumerate(plan.get("illustrations", [])):
            fallback_id = f"illustrations[{index}]"
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                skipped.append(
                    {
                        "id": fallback_id,
                        "reason": "; ".join(errors_by_scope.get(fallback_id, ["Invalid illustration item."])),
                    }
                )
                continue
            if item.get("approval") != "approved":
                continue
            item_id = item["id"]
            if item_id in errors_by_scope:
                skipped.append({"id": item_id, "reason": "; ".join(errors_by_scope[item_id])})
                continue
            if len(find_anchor_matches(article_text, item["insert_after"])) != 1:
                skipped.append({"id": item_id, "reason": "Anchor is not unique."})
                continue

            prompt_path = resolve_artifact_path(args.plan, plan, item["prompt_file"])
            output_path = resolve_artifact_path(args.plan, plan, item["output_file"])
            protected_paths.update({prompt_path, output_path})
            prompt_hash = sha256_file(prompt_path)
            generation = item["generation"]
            valid_existing, _, _ = validate_png(output_path)
            if (
                generation.get("status") == "generated"
                and generation.get("prompt_sha256") == prompt_hash
                and valid_existing
            ):
                skipped.append({"id": item_id, "reason": "Already generated from the same prompt."})
                continue
            if output_path.exists():
                skipped.append(
                    {
                        "id": item_id,
                        "reason": "Output file already exists; choose a new output_file or remove it explicitly.",
                    }
                )
                continue
            tasks.append(
                {
                    "id": item_id,
                    "prompt_file": str(prompt_path),
                    "output_file": str(output_path),
                    "aspect_ratio": plan["aspect_ratio"],
                    "prompt_sha256": prompt_hash,
                }
            )

        manifest_path = Path(args.output).resolve()
        if manifest_path.suffix.lower() != ".json":
            raise PlanError("Generation task output must be a .json file.")
        try:
            manifest_path.relative_to((resolve_article_path(args.plan, plan).parent / "imgs").resolve())
        except ValueError as exc:
            raise PlanError("Generation task output must be inside the article imgs/ directory.") from exc
        if manifest_path in protected_paths:
            raise PlanError("Generation task output cannot overwrite the plan, article, prompt, or image.")
        payload = {
            "backend": "native-imagegen",
            "batch_size": args.batch_size,
            "tasks": tasks,
            "skipped": skipped,
        }
        atomic_write_text(manifest_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (KeyError, OSError, PlanError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
