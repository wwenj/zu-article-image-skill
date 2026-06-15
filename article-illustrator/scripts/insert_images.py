#!/usr/bin/env python3
"""Insert verified generated images after exact Markdown anchors."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict

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
    write_plan,
)


def markdown_path_exists(text: str, image_path: str) -> bool:
    pattern = re.compile(r"!\[[^\]]*\]\(\s*<?" + re.escape(image_path) + r">?(?:\s+['\"][^'\"]*['\"])?\s*\)")
    return bool(pattern.search(text))


def choose_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def markdown_image_reference(title: str, image_path: str) -> str:
    alt = title.replace("\\", "\\\\").replace("]", "\\]") + "图"
    target = f"<{image_path}>" if any(char.isspace() or char in "()" for char in image_path) else image_path
    return f"![{alt}]({target})"


def insertion_block(before: str, after: str, references: list[str], newline: str) -> str:
    if before.endswith(newline * 2):
        prefix = ""
    elif before.endswith(newline):
        prefix = newline
    else:
        prefix = newline * 2
    if after.startswith(newline * 2):
        suffix = ""
    elif after.startswith(newline):
        suffix = newline
    else:
        suffix = newline * 2
    return prefix + (newline * 2).join(references) + suffix


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    args = parser.parse_args()
    try:
        plan = read_plan(args.plan)
        validation = validate_plan(plan, args.plan, "insertion")
        if validation["global_errors"]:
            raise PlanError(validation["global_errors"][0]["message"])
        article_path = resolve_article_path(args.plan, plan)
        text = read_text_preserving_newlines(article_path)
        newline = choose_newline(text)
        groups: dict[int, list[tuple[dict, str]]] = defaultdict(list)
        results: list[dict[str, str]] = []
        errors_by_scope: dict[str, list[str]] = defaultdict(list)
        for error in validation["item_errors"]:
            errors_by_scope[error["scope"]].append(error["message"])

        for index, item in enumerate(plan.get("illustrations", [])):
            fallback_id = f"illustrations[{index}]"
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                results.append(
                    {
                        "id": fallback_id,
                        "status": "failed",
                        "error": "; ".join(errors_by_scope.get(fallback_id, ["Invalid illustration item."])),
                    }
                )
                continue
            if item.get("generation", {}).get("status") != "generated":
                continue
            if item["id"] in errors_by_scope:
                error = "; ".join(errors_by_scope[item["id"]])
                insertion = item.get("insertion")
                if isinstance(insertion, dict):
                    insertion["status"] = "failed"
                    insertion["error"] = error
                results.append({"id": item["id"], "status": "failed", "error": error})
                continue
            image_path = item["output_file"].replace("\\", "/")
            if markdown_path_exists(text, image_path):
                item["insertion"]["status"] = "already_present"
                item["insertion"]["error"] = None
                results.append({"id": item["id"], "status": "already_present"})
                continue
            output_path = resolve_artifact_path(args.plan, plan, item["output_file"])
            valid, error, _ = validate_png(output_path)
            if not valid:
                item["insertion"]["status"] = "failed"
                item["insertion"]["error"] = error
                results.append({"id": item["id"], "status": "failed", "error": error or "Invalid PNG"})
                continue
            matches = find_anchor_matches(text, item["insert_after"])
            if len(matches) != 1:
                error = f"insert_after must match exactly once; found {len(matches)}."
                item["insertion"]["status"] = "failed"
                item["insertion"]["error"] = error
                results.append({"id": item["id"], "status": "failed", "error": error})
                continue
            reference = markdown_image_reference(item["title"], image_path)
            groups[matches[0][1]].append((item, reference))

        updated = text
        for offset in sorted(groups, reverse=True):
            entries = groups[offset]
            block = insertion_block(
                updated[:offset],
                updated[offset:],
                [reference for _, reference in entries],
                newline,
            )
            updated = updated[:offset] + block + updated[offset:]
            for item, _ in entries:
                item["insertion"]["status"] = "inserted"
                item["insertion"]["error"] = None
                results.append({"id": item["id"], "status": "inserted"})

        if updated != text:
            atomic_write_text(article_path, updated, newline="")
            plan["article"]["sha256"] = sha256_file(article_path)
        write_plan(args.plan, plan)
        summary = {
            "article": str(article_path),
            "inserted": sum(result["status"] == "inserted" for result in results),
            "already_present": sum(result["status"] == "already_present" for result in results),
            "failed": sum(result["status"] == "failed" for result in results),
            "results": results,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except (KeyError, OSError, PlanError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
