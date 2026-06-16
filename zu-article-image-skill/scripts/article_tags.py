#!/usr/bin/env python3
"""Scan and synchronize inline article illustration prompt tags."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TAG_MARKER = "<!-- article-illustration"
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RATIO_PATTERN = re.compile(r"^(?P<width>\d+(?:\.\d+)?):(?P<height>\d+(?:\.\d+)?)$")
ATTRIBUTE_PATTERN = re.compile(r'\s+([a-z]+)="([^"\r\n]*)"')
ALLOWED_ATTRIBUTES = {"id", "ratio", "alt"}


@dataclass
class ParsedTag:
    start: int
    end: int
    line: int
    attributes: dict[str, str]
    prompt: str
    errors: list[str]


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def choose_newline(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def line_number(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def line_bounds(text: str, offset: int) -> tuple[int, int]:
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n", offset)
    if end < 0:
        return start, len(text)
    if end > 0 and text[end - 1] == "\r":
        end -= 1
    return start, end


def parse_attributes(raw: str) -> tuple[dict[str, str], list[str]]:
    attributes: dict[str, str] = {}
    errors: list[str] = []
    cursor = 0
    for match in ATTRIBUTE_PATTERN.finditer(raw):
        if raw[cursor : match.start()].strip():
            errors.append("Malformed tag attributes.")
            break
        key, value = match.groups()
        if key not in ALLOWED_ATTRIBUTES:
            errors.append(f"Unsupported attribute: {key}")
        elif key in attributes:
            errors.append(f"Duplicate attribute: {key}")
        elif "-->" in value:
            errors.append(f"Attribute {key} cannot contain '-->'.")
        else:
            attributes[key] = value
        cursor = match.end()
    if raw[cursor:].strip():
        errors.append("Malformed tag attributes.")
    return attributes, errors


def parse_tags(text: str) -> tuple[list[ParsedTag], list[dict[str, Any]]]:
    tags: list[ParsedTag] = []
    errors: list[dict[str, Any]] = []
    cursor = 0
    while True:
        start = text.find(TAG_MARKER, cursor)
        if start < 0:
            break
        tag_line = line_number(text, start)
        opening_line_start, _ = line_bounds(text, start)
        tag_errors: list[str] = []
        if text[opening_line_start:start].strip():
            tag_errors.append("Opening marker must start on its own line.")

        header_start = start + len(TAG_MARKER)
        newline_at = text.find("\n", header_start)
        if newline_at < 0:
            errors.append(
                {"line": tag_line, "status": "error", "errors": ["Unclosed illustration tag."]}
            )
            break
        header_end = newline_at - 1 if newline_at > 0 and text[newline_at - 1] == "\r" else newline_at
        raw_attributes = text[header_start:header_end]
        attributes, attribute_errors = parse_attributes(raw_attributes)
        tag_errors.extend(attribute_errors)

        close_at = text.find("-->", newline_at + 1)
        if close_at < 0:
            errors.append(
                {
                    "id": attributes.get("id"),
                    "line": tag_line,
                    "status": "error",
                    "errors": tag_errors + ["Unclosed illustration tag."],
                }
            )
            break

        close_line_start, close_line_end = line_bounds(text, close_at)
        if text[close_line_start:close_at].strip() or text[close_at + 3 : close_line_end].strip():
            tag_errors.append("Prompt cannot contain '-->'; closing marker must be on its own line.")
        end = close_line_end
        prompt = text[newline_at + 1 : close_line_start].strip()
        if not prompt:
            tag_errors.append("Prompt must not be empty.")

        tag_id = attributes.get("id", "")
        valid_id = bool(tag_id and ID_PATTERN.fullmatch(tag_id))
        if not tag_id:
            tag_errors.append("Missing required id attribute.")
        elif not valid_id:
            tag_errors.append("id must contain only lowercase letters, digits, and hyphens.")

        ratio = attributes.get("ratio", "16:9")
        ratio_match = RATIO_PATTERN.fullmatch(ratio)
        if not ratio_match or float(ratio_match["width"]) <= 0 or float(ratio_match["height"]) <= 0:
            tag_errors.append("ratio must be a positive width:height value.")

        if "alt" in attributes and not attributes["alt"].strip():
            tag_errors.append("alt must not be empty when provided.")

        tags.append(
            ParsedTag(
                start=start,
                end=end,
                line=tag_line,
                attributes=attributes,
                prompt=prompt,
                errors=tag_errors,
            )
        )
        cursor = end

    return tags, errors


def image_reference_pattern(image_path: str) -> re.Pattern[str]:
    return re.compile(
        r"!\[[^\]\r\n]*\]\(\s*<?"
        + re.escape(image_path)
        + r">?(?:\s+['\"][^'\"]*['\"])?\s*\)"
    )


def markdown_reference(alt: str, image_path: str) -> str:
    safe_alt = alt.replace("\\", "\\\\").replace("]", "\\]")
    return f"![{safe_alt}]({image_path})"


def scan_article(article: Path) -> dict[str, Any]:
    if not article.is_file():
        return {
            "valid": False,
            "article": str(article),
            "items": [],
            "errors": [{"status": "error", "errors": [f"Article not found: {article}"]}],
        }
    try:
        text = read_text(article)
    except OSError as exc:
        return {
            "valid": False,
            "article": str(article),
            "items": [],
            "errors": [{"status": "error", "errors": [str(exc)]}],
        }

    tags, structural_errors = parse_tags(text)
    id_counts = Counter(tag.attributes.get("id") for tag in tags if tag.attributes.get("id"))
    items: list[dict[str, Any]] = []

    for tag in tags:
        tag_id = tag.attributes.get("id", "")
        errors = list(tag.errors)
        if tag_id and id_counts[tag_id] > 1:
            errors.append(f"Duplicate id: {tag_id}")

        ratio = tag.attributes.get("ratio", "16:9")
        alt = tag.attributes.get("alt", "").strip() or f"文章插图 {tag_id or 'unknown'}"
        valid_id = bool(tag_id and ID_PATTERN.fullmatch(tag_id))
        image_path = f"imgs/{tag_id}.png" if valid_id else None
        output_path = str((article.parent / image_path).resolve()) if image_path else None
        references = len(image_reference_pattern(image_path).findall(text)) if image_path else 0
        image_exists = bool(output_path and Path(output_path).is_file())

        if references > 1:
            errors.append(f"Duplicate image references: {references}")

        if errors:
            status = "error"
        elif not image_exists:
            status = "needs_generation"
        elif references == 0:
            status = "needs_insertion"
        else:
            status = "complete"

        items.append(
            {
                "id": tag_id or None,
                "ratio": ratio,
                "alt": alt,
                "prompt": tag.prompt,
                "line": tag.line,
                "image_path": image_path,
                "output_path": output_path,
                "image_exists": image_exists,
                "image_references": references,
                "status": status,
                "errors": errors,
                "_start": tag.start,
                "_end": tag.end,
            }
        )

    errors = structural_errors + [
        {"id": item["id"], "line": item["line"], "status": "error", "errors": item["errors"]}
        for item in items
        if item["status"] == "error"
    ]
    summary = {
        "total": len(items),
        "needs_generation": sum(item["status"] == "needs_generation" for item in items),
        "needs_insertion": sum(item["status"] == "needs_insertion" for item in items),
        "complete": sum(item["status"] == "complete" for item in items),
        "error": len(errors),
    }
    return {
        "valid": not errors,
        "article": str(article),
        "items": items,
        "errors": errors,
        "summary": summary,
        "_text": text,
    }


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    output = {key: value for key, value in result.items() if not key.startswith("_")}
    output["items"] = [
        {key: value for key, value in item.items() if not key.startswith("_")}
        for item in result.get("items", [])
    ]
    return output


def atomic_write(path: Path, content: str) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def insertion_block(before: str, after: str, reference: str, newline: str) -> str:
    prefix = newline if before.endswith(newline) else newline * 2
    if after.startswith(newline * 2):
        suffix = ""
    elif after.startswith(newline):
        suffix = newline
    else:
        suffix = newline * 2
    return prefix + reference + suffix


def sync_article(article: Path) -> tuple[dict[str, Any], int]:
    result = scan_article(article)
    if result["errors"]:
        public = public_result(result)
        public["modified"] = False
        return public, 1

    text = result["_text"]
    newline = choose_newline(text)
    insertions = [
        item for item in result["items"] if item["status"] == "needs_insertion"
    ]
    updated = text
    for item in sorted(insertions, key=lambda value: value["_end"], reverse=True):
        offset = item["_end"]
        reference = markdown_reference(item["alt"], item["image_path"])
        block = insertion_block(updated[:offset], updated[offset:], reference, newline)
        updated = updated[:offset] + block + updated[offset:]

    if updated != text:
        atomic_write(article, updated)

    final = scan_article(article)
    public = public_result(final)
    public["modified"] = updated != text
    public["inserted"] = len(insertions)
    return public, 0 if final["valid"] else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("scan", "sync"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("article")
    args = parser.parse_args()

    article = Path(args.article).resolve()
    if args.command == "scan":
        result = scan_article(article)
        print(json.dumps(public_result(result), ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1

    result, exit_code = sync_article(article)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
