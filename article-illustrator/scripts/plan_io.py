#!/usr/bin/env python3
"""Shared deterministic helpers for article-illustrator plans."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised only without dependency
    raise SystemExit(
        "PyYAML is required. Install it with: python3 -m pip install 'PyYAML>=6,<7'"
    ) from exc


PLAN_PATTERN = re.compile(
    r"\A(?:\ufeff)?# Illustration Plan\r?\n\r?\n```yaml\r?\n"
    r"(?P<yaml>[\s\S]*?)\r?\n```\r?\n?\Z"
)
PROMPT_PATTERN = re.compile(
    r"\A(?:\ufeff)?---\r?\n(?P<yaml>[\s\S]*?)\r?\n---\r?\n(?P<body>[\s\S]+)\Z"
)
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
TYPES = {"concept", "process", "comparison", "architecture", "scene"}
STYLES = {"technical", "editorial", "sketch-note"}
APPROVALS = {"pending", "approved", "skip"}
GENERATION_STATUSES = {"not_started", "generated", "failed"}
QA_STATUSES = {"not_checked", "passed", "needs_review"}
INSERTION_STATUSES = {"not_started", "inserted", "already_present", "failed"}


class PlanError(ValueError):
    """Raised when a plan or related artifact violates the contract."""


class LiteralSafeDumper(yaml.SafeDumper):
    """Emit multiline strings as human-editable YAML literal blocks."""


def represent_string(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


LiteralSafeDumper.add_representer(str, represent_string)


def read_text_preserving_newlines(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def read_plan(plan_path: str | Path) -> dict[str, Any]:
    path = Path(plan_path).resolve()
    try:
        content = read_text_preserving_newlines(path)
    except OSError as exc:
        raise PlanError(f"Cannot read plan: {path}: {exc}") from exc

    match = PLAN_PATTERN.fullmatch(content)
    if not match:
        raise PlanError(
            "Plan must contain only '# Illustration Plan' and exactly one fenced yaml block."
        )
    try:
        parsed = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError as exc:
        raise PlanError(f"Invalid YAML in plan: {exc}") from exc
    if not isinstance(parsed, dict):
        raise PlanError("Plan YAML root must be a mapping.")
    return parsed


def render_plan(plan: dict[str, Any]) -> str:
    body = yaml.dump(
        plan,
        Dumper=LiteralSafeDumper,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=1000,
    ).rstrip()
    return f"# Illustration Plan\n\n```yaml\n{body}\n```\n"


def validate_prompt_file(
    prompt_path: str | Path, item: dict[str, Any], plan: dict[str, Any]
) -> dict[str, Any]:
    path = Path(prompt_path)
    try:
        content = read_text_preserving_newlines(path)
    except OSError as exc:
        raise PlanError(f"Cannot read prompt file: {path}: {exc}") from exc
    match = PROMPT_PATTERN.fullmatch(content)
    if not match:
        raise PlanError(f"Prompt must contain YAML frontmatter and a non-empty body: {path}")
    try:
        metadata = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError as exc:
        raise PlanError(f"Invalid prompt frontmatter: {path}: {exc}") from exc
    if not isinstance(metadata, dict):
        raise PlanError(f"Prompt frontmatter must be a mapping: {path}")

    expected = {
        "id": item["id"],
        "type": item["type"],
        "style": plan["style"],
        "aspect_ratio": plan["aspect_ratio"],
        "output_file": item["output_file"],
    }
    if item.get("generation", {}).get("status") != "generated":
        expected["article_sha256"] = plan["article"]["sha256"]
    for key, value in expected.items():
        if str(metadata.get(key)) != str(value):
            raise PlanError(
                f"Prompt frontmatter {key} does not match the plan: expected {value!r}."
            )
    if not isinstance(metadata.get("article_sha256"), str) or not metadata["article_sha256"]:
        raise PlanError(f"Prompt frontmatter article_sha256 must be a non-empty string: {path}")

    body = match.group("body")
    required_groups = [
        ("USE CASE",),
        ("PURPOSE",),
        ("COMPOSITION",),
        ("ZONES", "STEPS", "NODES"),
        ("LABELS",),
        ("RELATIONSHIPS",),
        ("COLORS",),
        ("STYLE",),
        ("CONSTRAINTS",),
        ("ASPECT",),
    ]
    cursor = 0
    for group in required_groups:
        positions = []
        for heading in group:
            found = re.search(rf"(?m)^{re.escape(heading)}:\s*$", body[cursor:])
            if found:
                positions.append((found.start(), found.end(), heading))
        if not positions:
            raise PlanError(f"Prompt is missing required section {'/'.join(group)}: {path}")
        start, end, _ = min(positions)
        if start < 0:
            raise PlanError(f"Prompt sections are out of order: {path}")
        cursor += end
    return metadata


def atomic_write_text(path: str | Path, content: str, newline: str = "") -> None:
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def write_plan(plan_path: str | Path, plan: dict[str, Any]) -> None:
    atomic_write_text(plan_path, render_plan(plan))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def resolve_article_path(plan_path: str | Path, plan: dict[str, Any]) -> Path:
    article = plan.get("article")
    if not isinstance(article, dict) or not isinstance(article.get("path"), str):
        raise PlanError("article.path must be a string.")
    return (Path(plan_path).resolve().parent / article["path"]).resolve()


def article_dir(plan_path: str | Path, plan: dict[str, Any]) -> Path:
    return resolve_article_path(plan_path, plan).parent


def resolve_artifact_path(
    plan_path: str | Path, plan: dict[str, Any], relative_path: str
) -> Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise PlanError("Artifact path must be a non-empty string.")
    if any(ord(char) < 32 for char in relative_path) or "<" in relative_path or ">" in relative_path:
        raise PlanError(f"Artifact path contains unsafe Markdown characters: {relative_path!r}")
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise PlanError(f"Artifact path must be relative and cannot contain '..': {relative_path}")
    if not candidate.parts or candidate.parts[0] != "imgs":
        raise PlanError(f"Artifact path must be inside imgs/: {relative_path}")
    base = article_dir(plan_path, plan)
    resolved = (base / candidate).resolve()
    imgs_dir = (base / "imgs").resolve()
    try:
        resolved.relative_to(imgs_dir)
    except ValueError as exc:
        raise PlanError(f"Artifact path escapes imgs/: {relative_path}") from exc
    if resolved == resolve_article_path(plan_path, plan):
        raise PlanError(f"Artifact path cannot overwrite the article: {relative_path}")
    return resolved


def normalize_newlines_with_boundaries(text: str) -> tuple[str, list[int]]:
    normalized: list[str] = []
    boundaries = [0]
    index = 0
    while index < len(text):
        if text.startswith("\r\n", index):
            normalized.append("\n")
            index += 2
        elif text[index] == "\r":
            normalized.append("\n")
            index += 1
        else:
            normalized.append(text[index])
            index += 1
        boundaries.append(index)
    return "".join(normalized), boundaries


def find_anchor_matches(text: str, anchor: str) -> list[tuple[int, int]]:
    if not isinstance(anchor, str) or not anchor:
        return []
    normalized_text, boundaries = normalize_newlines_with_boundaries(text)
    normalized_anchor = anchor.replace("\r\n", "\n").replace("\r", "\n")
    matches: list[tuple[int, int]] = []
    start = 0
    while True:
        index = normalized_text.find(normalized_anchor, start)
        if index < 0:
            break
        end_index = index + len(normalized_anchor)
        starts_at_block_boundary = index == 0 or normalized_text[index - 1] == "\n"
        ends_at_block_boundary = (
            end_index == len(normalized_text)
            or normalized_text[end_index] == "\n"
            or normalized_anchor.endswith("\n")
        )
        if starts_at_block_boundary and ends_at_block_boundary:
            matches.append((boundaries[index], boundaries[end_index]))
        start = index + max(1, len(normalized_anchor))
    return matches


def line_number_at(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1


def validate_png(path: str | Path) -> tuple[bool, str | None, int]:
    image = Path(path)
    try:
        size = image.stat().st_size
    except OSError:
        return False, f"Output file not found: {image}", 0
    if size < 1000:
        return False, f"Output file too small: {size} bytes", size
    try:
        with image.open("rb") as handle:
            magic = handle.read(len(PNG_MAGIC))
    except OSError as exc:
        return False, f"Cannot read output file: {exc}", size
    if magic != PNG_MAGIC:
        return False, "Output is not a valid PNG: magic bytes mismatch", size
    return True, None, size


def required_string(
    mapping: Any, key: str, errors: list[dict[str, str]], scope: str
) -> str | None:
    if not isinstance(mapping, dict) or not isinstance(mapping.get(key), str) or not mapping[key]:
        errors.append({"scope": scope, "code": "required", "message": f"{key} must be a non-empty string."})
        return None
    return mapping[key]


def validate_plan(
    plan: dict[str, Any], plan_path: str | Path, stage: str = "plan"
) -> dict[str, Any]:
    if stage not in {"plan", "generation", "insertion"}:
        raise PlanError(f"Unsupported validation stage: {stage}")

    global_errors: list[dict[str, str]] = []
    item_errors: list[dict[str, str]] = []

    if plan.get("version") != 1:
        global_errors.append({"scope": "plan", "code": "version", "message": "version must be 1."})
    article = plan.get("article")
    article_path_value = required_string(article, "path", global_errors, "article")
    expected_hash = required_string(article, "sha256", global_errors, "article")
    style = required_string(plan, "style", global_errors, "plan")
    if style and style not in STYLES:
        global_errors.append({"scope": "plan", "code": "style", "message": f"Unsupported style: {style}"})
    required_string(plan, "aspect_ratio", global_errors, "plan")

    illustrations = plan.get("illustrations")
    if not isinstance(illustrations, list):
        global_errors.append(
            {"scope": "plan", "code": "illustrations", "message": "illustrations must be a list."}
        )
        illustrations = []

    article_path: Path | None = None
    article_text: str | None = None
    if article_path_value:
        try:
            article_path = resolve_article_path(plan_path, plan)
            if not article_path.is_file():
                raise PlanError(f"Article does not exist: {article_path}")
            if article_path == Path(plan_path).resolve():
                raise PlanError("Article path cannot be the illustration plan itself.")
            if article_path.suffix.lower() not in {".md", ".markdown"}:
                raise PlanError(f"Article must be a Markdown file: {article_path}")
            if article_path.stat().st_size == 0:
                raise PlanError(f"Article is empty: {article_path}")
            if expected_hash and sha256_file(article_path) != expected_hash:
                raise PlanError("Article SHA-256 does not match the plan.")
            article_text = read_text_preserving_newlines(article_path)
        except (OSError, PlanError) as exc:
            global_errors.append({"scope": "article", "code": "article", "message": str(exc)})

    seen_ids: set[str] = set()
    seen_prompts: set[str] = set()
    seen_outputs: set[str] = set()
    for index, item in enumerate(illustrations):
        scope = f"illustrations[{index}]"
        if not isinstance(item, dict):
            item_errors.append({"scope": scope, "code": "type", "message": "Illustration must be a mapping."})
            continue
        item_id = required_string(item, "id", item_errors, scope) or scope
        required_string(item, "title", item_errors, item_id)
        required_string(item, "section", item_errors, item_id)
        required_string(item, "source_summary", item_errors, item_id)
        required_string(item, "visual_purpose", item_errors, item_id)
        anchor = required_string(item, "insert_after", item_errors, item_id)
        prompt_file = required_string(item, "prompt_file", item_errors, item_id)
        output_file = required_string(item, "output_file", item_errors, item_id)

        if item_id in seen_ids:
            item_errors.append({"scope": item_id, "code": "duplicate_id", "message": f"Duplicate id: {item_id}"})
        seen_ids.add(item_id)

        approval = item.get("approval")
        if approval not in APPROVALS:
            item_errors.append({"scope": item_id, "code": "approval", "message": f"Invalid approval: {approval}"})
        illustration_type = item.get("type")
        if illustration_type not in TYPES:
            item_errors.append({"scope": item_id, "code": "type", "message": f"Invalid type: {illustration_type}"})
        if not isinstance(item.get("visual_content"), list) or not item.get("visual_content") or not all(
            isinstance(value, str) and value for value in item.get("visual_content", [])
        ):
            item_errors.append({"scope": item_id, "code": "visual_content", "message": "visual_content must be a non-empty string list."})
        if not isinstance(item.get("article_terms"), list) or not all(
            isinstance(value, str) and value for value in item.get("article_terms", [])
        ):
            item_errors.append({"scope": item_id, "code": "article_terms", "message": "article_terms must be a string list."})

        generation = item.get("generation")
        qa = item.get("qa")
        insertion = item.get("insertion")
        if not isinstance(generation, dict):
            item_errors.append({"scope": item_id, "code": "generation", "message": "generation must be a mapping."})
            generation = {}
        if not isinstance(qa, dict):
            item_errors.append({"scope": item_id, "code": "qa", "message": "qa must be a mapping."})
            qa = {}
        if not isinstance(insertion, dict):
            item_errors.append({"scope": item_id, "code": "insertion", "message": "insertion must be a mapping."})
            insertion = {}

        generation_status = generation.get("status")
        insertion_status = insertion.get("status")
        if generation_status not in GENERATION_STATUSES:
            item_errors.append({"scope": item_id, "code": "generation_status", "message": f"Invalid generation.status: {generation_status}"})
        if not isinstance(generation.get("attempts"), int) or generation.get("attempts", -1) < 0:
            item_errors.append({"scope": item_id, "code": "attempts", "message": "generation.attempts must be a non-negative integer."})
        if generation_status == "generated" and not generation.get("prompt_sha256"):
            item_errors.append({"scope": item_id, "code": "prompt_sha256", "message": "Generated items require generation.prompt_sha256."})
        if generation_status == "failed" and not generation.get("error"):
            item_errors.append({"scope": item_id, "code": "generation_error", "message": "Failed generation requires an error."})
        if qa.get("status") not in QA_STATUSES:
            item_errors.append({"scope": item_id, "code": "qa_status", "message": f"Invalid qa.status: {qa.get('status')}"})
        if insertion_status not in INSERTION_STATUSES:
            item_errors.append({"scope": item_id, "code": "insertion_status", "message": f"Invalid insertion.status: {insertion_status}"})
        if insertion_status in {"inserted", "already_present"} and generation_status != "generated":
            item_errors.append({"scope": item_id, "code": "state", "message": "Inserted items must have generation.status generated."})
        if insertion_status == "failed" and not insertion.get("error"):
            item_errors.append({"scope": item_id, "code": "insertion_error", "message": "Failed insertion requires an error."})

        for field, value, seen, extension in (
            ("prompt_file", prompt_file, seen_prompts, ".md"),
            ("output_file", output_file, seen_outputs, ".png"),
        ):
            if not value:
                continue
            try:
                resolved = resolve_artifact_path(plan_path, plan, value)
                if resolved.suffix.lower() != extension:
                    raise PlanError(f"{field} must end with {extension}: {value}")
                resolved_key = str(resolved)
                if resolved_key in seen:
                    item_errors.append({"scope": item_id, "code": f"duplicate_{field}", "message": f"Duplicate {field}: {value}"})
                seen.add(resolved_key)
            except (OSError, PlanError) as exc:
                item_errors.append({"scope": item_id, "code": field, "message": str(exc)})

        check_anchor = stage == "plan" or approval == "approved" or generation_status == "generated"
        if check_anchor and anchor and article_text is not None:
            matches = find_anchor_matches(article_text, anchor)
            if len(matches) != 1:
                item_errors.append(
                    {
                        "scope": item_id,
                        "code": "anchor",
                        "message": f"insert_after must match exactly once; found {len(matches)}.",
                    }
                )

        check_prompt = (
            stage == "generation" and approval == "approved"
        ) or (
            stage == "insertion" and generation_status == "generated"
        )
        if check_prompt and prompt_file:
            try:
                prompt_path = resolve_artifact_path(plan_path, plan, prompt_file)
                if not prompt_path.is_file():
                    raise PlanError(f"Prompt file does not exist: {prompt_file}")
                validate_prompt_file(prompt_path, item, plan)
                if (
                    stage == "insertion"
                    and generation_status == "generated"
                    and sha256_file(prompt_path) != generation.get("prompt_sha256")
                ):
                    raise PlanError("Prompt file changed after the image was generated.")
            except (KeyError, OSError, PlanError) as exc:
                item_errors.append({"scope": item_id, "code": "prompt_file", "message": str(exc)})

        if stage == "insertion" and generation_status == "generated" and output_file:
            try:
                output_path = resolve_artifact_path(plan_path, plan, output_file)
                valid, error, _ = validate_png(output_path)
                if not valid:
                    raise PlanError(error or f"Invalid PNG: {output_file}")
            except (OSError, PlanError) as exc:
                item_errors.append({"scope": item_id, "code": "output_file", "message": str(exc)})

    return {
        "valid": not global_errors and not item_errors,
        "stage": stage,
        "global_errors": global_errors,
        "item_errors": item_errors,
        "illustration_count": len(illustrations),
    }


def find_illustration(plan: dict[str, Any], item_id: str) -> dict[str, Any]:
    for item in plan.get("illustrations", []):
        if isinstance(item, dict) and item.get("id") == item_id:
            return item
    raise PlanError(f"Illustration id not found: {item_id}")
