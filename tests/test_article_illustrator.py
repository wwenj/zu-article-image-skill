from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "article-illustrator"
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import plan_io  # noqa: E402


def write_dummy_png(path: Path, valid: bool = True, large: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    magic = plan_io.PNG_MAGIC if valid else b"not-a-png"
    payload = magic + (b"x" * (1200 if large else 20))
    path.write_bytes(payload)


def write_prompt(path: Path, item: dict, plan: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
id: "{item['id']}"
type: "{item['type']}"
style: "{plan['style']}"
aspect_ratio: "{plan['aspect_ratio']}"
output_file: "{item['output_file']}"
article_sha256: "{plan['article']['sha256']}"
---
USE CASE:
Demo
PURPOSE:
Demo
COMPOSITION:
Centered
NODES:
Demo node
LABELS:
Demo
RELATIONSHIPS:
None
COLORS:
Blue
STYLE:
Technical
CONSTRAINTS:
No watermark
ASPECT:
16:9
""",
        encoding="utf-8",
    )


class Fixture:
    def __init__(self, root: Path, article_text: str | None = None) -> None:
        self.root = root
        self.article = root / "article.md"
        self.imgs = root / "imgs"
        self.plan_path = self.imgs / "illustration-plan.md"
        self.anchor = "Anchor paragraph."
        self.article.write_text(
            article_text or f"# Demo\n\n{self.anchor}\n\nEnd.\n",
            encoding="utf-8",
            newline="",
        )
        self.prompt = self.imgs / "prompts" / "01-demo.md"
        self.output = self.imgs / "01-demo.png"
        self.plan = {
            "version": 1,
            "article": {"path": "../article.md", "sha256": plan_io.sha256_file(self.article)},
            "style": "technical",
            "aspect_ratio": "16:9",
            "illustrations": [self.item()],
        }
        write_prompt(self.prompt, self.plan["illustrations"][0], self.plan)
        plan_io.write_plan(self.plan_path, self.plan)

    def item(
        self,
        item_id: str = "01",
        *,
        anchor: str | None = None,
        approval: str = "approved",
        prompt_file: str | None = None,
        output_file: str | None = None,
    ) -> dict:
        return {
            "id": item_id,
            "title": f"Demo {item_id}",
            "approval": approval,
            "section": "Demo",
            "source_summary": "Demo source",
            "visual_purpose": "Demo purpose",
            "type": "concept",
            "insert_after": anchor if anchor is not None else self.anchor,
            "visual_content": ["center: demo"],
            "article_terms": ["Demo"],
            "prompt_file": prompt_file or f"imgs/prompts/{item_id}-demo.md",
            "output_file": output_file or f"imgs/{item_id}-demo.png",
            "generation": {
                "status": "not_started",
                "attempts": 0,
                "prompt_sha256": None,
                "error": None,
            },
            "qa": {"status": "not_checked", "notes": None},
            "insertion": {"status": "not_started", "error": None},
        }

    def save(self) -> None:
        plan_io.write_plan(self.plan_path, self.plan)


def run_script(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class PlanIoTests(unittest.TestCase):
    def test_reads_strict_single_yaml_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            self.assertEqual(plan_io.read_plan(fixture.plan_path)["version"], 1)
            fixture.plan["illustrations"][0]["insert_after"] = "First line\nSecond line"
            fixture.save()
            self.assertIn("insert_after: |", fixture.plan_path.read_text(encoding="utf-8"))
            fixture.plan_path.write_text(
                "# Illustration Plan\n\n```yaml\nversion: 1\n```\nextra\n", encoding="utf-8"
            )
            with self.assertRaises(plan_io.PlanError):
                plan_io.read_plan(fixture.plan_path)

    def test_rejects_missing_repeated_and_invalid_yaml_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.md"
            for content in (
                "# Illustration Plan\n",
                "# Illustration Plan\n\n```yaml\nversion: 1\n```\n\n```yaml\nversion: 1\n```\n",
                "# Illustration Plan\n\n```yaml\ninvalid: [\n```\n",
            ):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(plan_io.PlanError):
                    plan_io.read_plan(path)

    def test_anchor_matching_requires_full_block_and_supports_crlf_multiline(self) -> None:
        text = "# Demo\r\n\r\nFirst line\r\nSecond line\r\n\r\nEnd\r\n"
        self.assertEqual(len(plan_io.find_anchor_matches(text, "First line\nSecond line")), 1)
        self.assertEqual(plan_io.find_anchor_matches(text, "line"), [])
        repeated = "Same\n\nSame\n"
        self.assertEqual(len(plan_io.find_anchor_matches(repeated, "Same")), 2)

    def test_validation_detects_duplicates_path_traversal_and_hash_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            duplicate = fixture.item(
                "01",
                prompt_file="imgs/prompts/../escape.md",
                output_file="imgs/./01-demo.png",
            )
            fixture.plan["illustrations"].append(duplicate)
            fixture.save()
            result = plan_io.validate_plan(fixture.plan, fixture.plan_path)
            codes = {error["code"] for error in result["item_errors"]}
            self.assertIn("duplicate_id", codes)
            self.assertIn("prompt_file", codes)
            self.assertIn("duplicate_output_file", codes)

            fixture.article.write_text("changed", encoding="utf-8")
            result = plan_io.validate_plan(fixture.plan, fixture.plan_path)
            self.assertTrue(result["global_errors"])

    def test_validation_rejects_unsafe_markdown_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            fixture.plan["illustrations"][0]["output_file"] = "imgs/bad<path>.png"
            fixture.save()
            result = plan_io.validate_plan(fixture.plan, fixture.plan_path)
            self.assertIn("output_file", {error["code"] for error in result["item_errors"]})

    def test_atomic_write_failure_keeps_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "article.md"
            path.write_text("original", encoding="utf-8")
            with mock.patch.object(plan_io.os, "replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    plan_io.atomic_write_text(path, "changed")
            self.assertEqual(path.read_text(encoding="utf-8"), "original")


class ScriptTests(unittest.TestCase):
    def test_validate_plan_cli_outputs_json_and_nonzero_on_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            result = run_script("validate_plan.py", "--plan", fixture.plan_path, "--stage", "plan")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["valid"])
            fixture.article.write_text("changed", encoding="utf-8")
            result = run_script("validate_plan.py", "--plan", fixture.plan_path, "--stage", "plan")
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(json.loads(result.stdout)["valid"])

    def test_find_anchor_cli_reports_unique_and_repeated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            article.write_text("Same\n\nSame\n", encoding="utf-8")
            result = run_script("find_anchor.py", article, "Same")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["matches"], 2)

    def test_prepare_generation_includes_only_valid_approved_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            pending = fixture.item("02", approval="pending")
            missing_prompt = fixture.item("03", prompt_file="imgs/prompts/missing.md")
            fixture.plan["illustrations"].extend([pending, missing_prompt])
            fixture.save()
            output = fixture.imgs / "generation-tasks.json"
            result = run_script(
                "prepare_generation.py", "--plan", fixture.plan_path, "--output", output
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([task["id"] for task in payload["tasks"]], ["01"])
            self.assertEqual([item["id"] for item in payload["skipped"]], ["03"])

    def test_prepare_generation_allows_empty_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            fixture.plan["illustrations"] = []
            fixture.save()
            output = fixture.imgs / "generation-tasks.json"
            result = run_script(
                "prepare_generation.py", "--plan", fixture.plan_path, "--output", output
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["tasks"], [])

    def test_prepare_generation_skips_existing_same_prompt_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            write_dummy_png(fixture.output)
            item = fixture.plan["illustrations"][0]
            item["generation"]["status"] = "generated"
            item["generation"]["prompt_sha256"] = plan_io.sha256_file(fixture.prompt)
            fixture.save()
            output = fixture.imgs / "generation-tasks.json"
            result = run_script(
                "prepare_generation.py", "--plan", fixture.plan_path, "--output", output
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["tasks"], [])
            self.assertIn("Already generated", payload["skipped"][0]["reason"])

    def test_prepare_generation_skips_structurally_invalid_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            fixture.plan["illustrations"].append("invalid")
            fixture.save()
            output = fixture.imgs / "generation-tasks.json"
            result = run_script(
                "prepare_generation.py", "--plan", fixture.plan_path, "--output", output
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual([task["id"] for task in payload["tasks"]], ["01"])
            self.assertEqual(payload["skipped"][0]["id"], "illustrations[1]")

    def test_prepare_generation_skips_invalid_prompt_and_rejects_external_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            fixture.prompt.write_text("not a structured prompt", encoding="utf-8")
            output = fixture.imgs / "generation-tasks.json"
            result = run_script(
                "prepare_generation.py", "--plan", fixture.plan_path, "--output", output
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["tasks"], [])
            self.assertEqual(payload["skipped"][0]["id"], "01")

            external = fixture.root / "generation-tasks.json"
            result = run_script(
                "prepare_generation.py", "--plan", fixture.plan_path, "--output", external
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("inside the article imgs", json.loads(result.stdout)["error"])

            result = run_script(
                "prepare_generation.py",
                "--plan",
                fixture.plan_path,
                "--output",
                output,
                "--batch-size",
                "5",
            )
            self.assertNotEqual(result.returncode, 0)

    def test_record_generation_success_failure_and_png_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            write_dummy_png(fixture.output)
            result = run_script(
                "record_generation.py",
                "--plan",
                fixture.plan_path,
                "--id",
                "01",
                "--success",
                "--prompt-sha256",
                plan_io.sha256_file(fixture.prompt),
                "--qa",
                "needs_review",
                "--qa-notes",
                "Check labels",
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            item = plan_io.read_plan(fixture.plan_path)["illustrations"][0]
            self.assertEqual(item["generation"]["status"], "generated")
            self.assertEqual(item["qa"]["status"], "needs_review")

            fixture.output.unlink()
            result = run_script(
                "record_generation.py",
                "--plan",
                fixture.plan_path,
                "--id",
                "01",
                "--failure",
                "--error",
                "output missing",
            )
            self.assertEqual(result.returncode, 0)
            item = plan_io.read_plan(fixture.plan_path)["illustrations"][0]
            self.assertEqual(item["generation"]["status"], "failed")
            self.assertEqual(item["generation"]["attempts"], 2)

            write_dummy_png(fixture.output, valid=False)
            result = run_script(
                "record_generation.py", "--plan", fixture.plan_path, "--id", "01", "--success"
            )
            self.assertNotEqual(result.returncode, 0)

            write_dummy_png(fixture.output, valid=True, large=False)
            result = run_script(
                "record_generation.py", "--plan", fixture.plan_path, "--id", "01", "--success"
            )
            self.assertNotEqual(result.returncode, 0)

    def test_record_generation_rejects_changed_article_and_prompt_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            write_dummy_png(fixture.output)
            result = run_script(
                "record_generation.py",
                "--plan",
                fixture.plan_path,
                "--id",
                "01",
                "--success",
                "--prompt-sha256",
                "wrong",
            )
            self.assertNotEqual(result.returncode, 0)
            fixture.article.write_text("changed", encoding="utf-8")
            result = run_script(
                "record_generation.py", "--plan", fixture.plan_path, "--id", "01", "--failure", "--error", "x"
            )
            self.assertNotEqual(result.returncode, 0)

    def test_insert_is_idempotent_and_updates_article_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            write_dummy_png(fixture.output)
            item = fixture.plan["illustrations"][0]
            item["generation"]["status"] = "generated"
            item["generation"]["prompt_sha256"] = plan_io.sha256_file(fixture.prompt)
            fixture.save()

            first = run_script("insert_images.py", "--plan", fixture.plan_path)
            self.assertEqual(first.returncode, 0, first.stdout)
            self.assertEqual(json.loads(first.stdout)["inserted"], 1)
            text = fixture.article.read_text(encoding="utf-8")
            self.assertEqual(text.count("](imgs/01-demo.png)"), 1)
            plan = plan_io.read_plan(fixture.plan_path)
            self.assertEqual(plan["article"]["sha256"], plan_io.sha256_file(fixture.article))

            second = run_script("insert_images.py", "--plan", fixture.plan_path)
            self.assertEqual(second.returncode, 0, second.stdout)
            self.assertEqual(json.loads(second.stdout)["already_present"], 1)
            self.assertEqual(fixture.article.read_text(encoding="utf-8").count("](imgs/01-demo.png)"), 1)

    def test_insert_multiple_same_anchor_keeps_plan_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            second = fixture.item("02")
            fixture.plan["illustrations"].append(second)
            second_prompt = fixture.imgs / "prompts" / "02-demo.md"
            write_prompt(second_prompt, second, fixture.plan)
            for item in fixture.plan["illustrations"]:
                output = fixture.root / item["output_file"]
                prompt = fixture.root / item["prompt_file"]
                write_dummy_png(output)
                item["generation"]["status"] = "generated"
                item["generation"]["prompt_sha256"] = plan_io.sha256_file(prompt)
            fixture.save()
            result = run_script("insert_images.py", "--plan", fixture.plan_path)
            self.assertEqual(result.returncode, 0, result.stdout)
            text = fixture.article.read_text(encoding="utf-8")
            self.assertLess(text.index("imgs/01-demo.png"), text.index("imgs/02-demo.png"))

    def test_deterministic_end_to_end_preserves_crlf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp), "# Demo\r\n\r\nAnchor paragraph.\r\n\r\nEnd.\r\n")
            tasks_path = fixture.imgs / "generation-tasks.json"
            prepared = run_script(
                "prepare_generation.py", "--plan", fixture.plan_path, "--output", tasks_path
            )
            self.assertEqual(prepared.returncode, 0, prepared.stdout)
            task = json.loads(tasks_path.read_text(encoding="utf-8"))["tasks"][0]
            write_dummy_png(Path(task["output_file"]))
            recorded = run_script(
                "record_generation.py",
                "--plan",
                fixture.plan_path,
                "--id",
                "01",
                "--success",
                "--prompt-sha256",
                task["prompt_sha256"],
                "--qa",
                "passed",
            )
            self.assertEqual(recorded.returncode, 0, recorded.stdout)
            inserted = run_script("insert_images.py", "--plan", fixture.plan_path)
            self.assertEqual(inserted.returncode, 0, inserted.stdout)
            raw = fixture.article.read_bytes()
            self.assertIn(b"\r\n\r\n![Demo 01", raw)
            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))

    def test_insert_continues_when_one_item_anchor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            invalid = fixture.item("02", anchor="Missing anchor")
            fixture.plan["illustrations"].append(invalid)
            prompt = fixture.imgs / "prompts" / "02-demo.md"
            write_prompt(prompt, invalid, fixture.plan)
            for item in fixture.plan["illustrations"]:
                write_dummy_png(fixture.root / item["output_file"])
                item["generation"]["status"] = "generated"
                item["generation"]["prompt_sha256"] = plan_io.sha256_file(fixture.root / item["prompt_file"])
            fixture.save()
            result = run_script("insert_images.py", "--plan", fixture.plan_path)
            self.assertEqual(result.returncode, 0, result.stdout)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["inserted"], 1)
            self.assertEqual(summary["failed"], 1)

    def test_insert_rejects_prompt_changed_after_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            write_dummy_png(fixture.output)
            item = fixture.plan["illustrations"][0]
            item["generation"]["status"] = "generated"
            item["generation"]["prompt_sha256"] = plan_io.sha256_file(fixture.prompt)
            fixture.save()
            fixture.prompt.write_text(
                fixture.prompt.read_text(encoding="utf-8") + "\nchanged\n",
                encoding="utf-8",
            )
            result = run_script("insert_images.py", "--plan", fixture.plan_path)
            self.assertEqual(result.returncode, 0, result.stdout)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["inserted"], 0)
            self.assertEqual(summary["failed"], 1)

    def test_insert_reports_structurally_invalid_item_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Fixture(Path(tmp))
            write_dummy_png(fixture.output)
            item = fixture.plan["illustrations"][0]
            item["generation"]["status"] = "generated"
            item["generation"]["prompt_sha256"] = plan_io.sha256_file(fixture.prompt)
            fixture.plan["illustrations"].append("invalid")
            fixture.save()
            result = run_script("insert_images.py", "--plan", fixture.plan_path)
            self.assertEqual(result.returncode, 0, result.stdout)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["inserted"], 1)
            self.assertEqual(summary["failed"], 1)


if __name__ == "__main__":
    unittest.main()
