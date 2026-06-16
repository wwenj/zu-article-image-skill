from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "zu-article-image-skill" / "scripts" / "article_tags.py"
sys.path.insert(0, str(SCRIPT_PATH.parent))

import article_tags  # noqa: E402


def tag(
    tag_id: str = "01-agent-runtime",
    *,
    ratio: str | None = "16:9",
    alt: str | None = "Agent 执行流程",
    prompt: str = "创建一张横向流程插图。\n\n展示 Router、Planner 和 Executor。",
) -> str:
    attributes = [f'id="{tag_id}"']
    if ratio is not None:
        attributes.append(f'ratio="{ratio}"')
    if alt is not None:
        attributes.append(f'alt="{alt}"')
    return (
        f"<!-- article-illustration {' '.join(attributes)}\n"
        f"{prompt}\n"
        "-->"
    )


def article_with(*tags: str, newline: str = "\n") -> str:
    content = "# Demo\n\nIntro.\n\n" + "\n\nParagraph.\n\n".join(tags) + "\n\nEnd.\n"
    return content.replace("\n", newline)


def run_script(command: str, article: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), command, str(article)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class ScanTests(unittest.TestCase):
    def test_scans_multiple_natural_language_tags_in_article_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            article.write_text(
                article_with(tag(), tag("02-context", alt="上下文结构")),
                encoding="utf-8",
            )
            result = article_tags.scan_article(article)
            self.assertTrue(result["valid"])
            self.assertEqual([item["id"] for item in result["items"]], ["01-agent-runtime", "02-context"])
            self.assertEqual(result["items"][0]["prompt"], "创建一张横向流程插图。\n\n展示 Router、Planner 和 Executor。")
            self.assertLess(result["items"][0]["line"], result["items"][1]["line"])

    def test_defaults_ratio_alt_and_fixed_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            article.write_text(article_with(tag("simple", ratio=None, alt=None)), encoding="utf-8")
            item = article_tags.scan_article(article)["items"][0]
            self.assertEqual(item["ratio"], "16:9")
            self.assertEqual(item["alt"], "文章插图 simple")
            self.assertEqual(item["image_path"], "imgs/simple.png")
            self.assertEqual(item["output_path"], str((root / "imgs/simple.png").resolve()))

    def test_reports_duplicate_invalid_empty_unclosed_and_inline_close(self) -> None:
        cases = {
            "duplicate": article_with(tag("same"), tag("same")),
            "invalid": article_with(tag("Bad_ID")),
            "empty": article_with(tag(prompt="   ")),
            "unclosed": "# Demo\n\n<!-- article-illustration id=\"one\"\nPrompt\n",
            "inline-close": article_with(tag(prompt="Prompt --> trailing text")),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in cases.items():
                article = root / f"{name}.md"
                article.write_text(content, encoding="utf-8")
                result = article_tags.scan_article(article)
                self.assertFalse(result["valid"], name)
                self.assertGreater(result["summary"]["error"] if "summary" in result else len(result["errors"]), 0)

    def test_reports_malformed_attributes_ratio_and_duplicate_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            content = article_with(
                '<!-- article-illustration id="one" ratio="0:9" unknown="x"\nPrompt\n-->'
            )
            content += "\n![One](imgs/one.png)\n![Again](imgs/one.png)\n"
            article.write_text(content, encoding="utf-8")
            result = article_tags.scan_article(article)
            self.assertFalse(result["valid"])
            errors = " ".join(result["items"][0]["errors"])
            self.assertIn("Unsupported attribute", errors)
            self.assertIn("ratio", errors)
            self.assertIn("Duplicate image references", errors)

    def test_status_needs_generation_when_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            article.write_text(article_with(tag()), encoding="utf-8")
            item = article_tags.scan_article(article)["items"][0]
            self.assertEqual(item["status"], "needs_generation")
            self.assertFalse(item["image_exists"])

    def test_status_needs_insertion_when_image_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            article.write_text(article_with(tag()), encoding="utf-8")
            image = root / "imgs/01-agent-runtime.png"
            image.parent.mkdir()
            image.write_bytes(b"image")
            item = article_tags.scan_article(article)["items"][0]
            self.assertEqual(item["status"], "needs_insertion")

    def test_status_complete_when_image_and_reference_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            article.write_text(
                article_with(tag()) + "\n![Agent 执行流程](imgs/01-agent-runtime.png)\n",
                encoding="utf-8",
            )
            image = root / "imgs/01-agent-runtime.png"
            image.parent.mkdir()
            image.write_bytes(b"image")
            item = article_tags.scan_article(article)["items"][0]
            self.assertEqual(item["status"], "complete")

    def test_scan_cli_outputs_public_json_and_nonzero_for_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            article = Path(tmp) / "article.md"
            article.write_text(article_with(tag()), encoding="utf-8")
            success = run_script("scan", article)
            self.assertEqual(success.returncode, 0, success.stderr)
            payload = json.loads(success.stdout)
            self.assertNotIn("_text", payload)
            self.assertNotIn("_start", payload["items"][0])

            article.write_text(article_with(tag("INVALID")), encoding="utf-8")
            failure = run_script("scan", article)
            self.assertNotEqual(failure.returncode, 0)
            self.assertFalse(json.loads(failure.stdout)["valid"])


class SyncTests(unittest.TestCase):
    def test_sync_inserts_reference_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            original_tag = tag()
            article.write_text(article_with(original_tag), encoding="utf-8")
            image = root / "imgs/01-agent-runtime.png"
            image.parent.mkdir()
            image.write_bytes(b"image")

            first, code = article_tags.sync_article(article)
            self.assertEqual(code, 0)
            self.assertTrue(first["modified"])
            self.assertEqual(first["inserted"], 1)
            content = article.read_text(encoding="utf-8")
            self.assertIn(original_tag, content)
            self.assertEqual(content.count("](imgs/01-agent-runtime.png)"), 1)

            second, code = article_tags.sync_article(article)
            self.assertEqual(code, 0)
            self.assertFalse(second["modified"])
            self.assertEqual(second["inserted"], 0)
            self.assertEqual(article.read_text(encoding="utf-8").count("](imgs/01-agent-runtime.png)"), 1)

    def test_sync_multiple_tags_preserves_article_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            article.write_text(article_with(tag("one", alt="One"), tag("two", alt="Two")), encoding="utf-8")
            (root / "imgs").mkdir()
            (root / "imgs/one.png").write_bytes(b"one")
            (root / "imgs/two.png").write_bytes(b"two")
            result, code = article_tags.sync_article(article)
            self.assertEqual(code, 0)
            self.assertEqual(result["inserted"], 2)
            content = article.read_text(encoding="utf-8")
            self.assertLess(content.index("imgs/one.png"), content.index("imgs/two.png"))

    def test_sync_preserves_crlf_and_prompt_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            prompt = "第一段 Prompt。\n\n第二段 Prompt。"
            content = article_with(tag(prompt=prompt), newline="\r\n")
            article.write_bytes(content.encode("utf-8"))
            image = root / "imgs/01-agent-runtime.png"
            image.parent.mkdir()
            image.write_bytes(b"image")
            result, code = article_tags.sync_article(article)
            self.assertEqual(code, 0)
            self.assertTrue(result["modified"])
            raw = article.read_bytes()
            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
            self.assertIn(prompt.replace("\n", "\r\n").encode("utf-8"), raw)

    def test_sync_does_not_modify_article_when_any_tag_has_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            content = article_with(tag("valid"), tag("INVALID"))
            article.write_text(content, encoding="utf-8")
            (root / "imgs").mkdir()
            (root / "imgs/valid.png").write_bytes(b"image")
            result, code = article_tags.sync_article(article)
            self.assertNotEqual(code, 0)
            self.assertFalse(result["modified"])
            self.assertEqual(article.read_text(encoding="utf-8"), content)

    def test_atomic_write_failure_preserves_original(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            article = root / "article.md"
            content = article_with(tag())
            article.write_text(content, encoding="utf-8")
            image = root / "imgs/01-agent-runtime.png"
            image.parent.mkdir()
            image.write_bytes(b"image")
            with mock.patch.object(article_tags.os, "replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    article_tags.sync_article(article)
            self.assertEqual(article.read_text(encoding="utf-8"), content)


if __name__ == "__main__":
    unittest.main()
