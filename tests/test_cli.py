"""Test Insightor CLI — commands, help text, argument parsing."""

import re
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from insightor.cli import main


@pytest.fixture
def runner():
    return CliRunner()


# =============================================================================
# Main group
# =============================================================================

class TestMainGroup:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Insightor" in result.output
        assert "review" in result.output
        assert "describe" in result.output
        assert "risks" in result.output
        assert "improve" in result.output
        assert "publish" in result.output

    def test_no_args_shows_help_or_error(self, runner):
        result = runner.invoke(main)
        # click group with no default command exits with 2 (no_args_is_help)
        assert result.exit_code in (0, 2)


# =============================================================================
# review
# =============================================================================

class TestReviewCommand:
    def test_help(self, runner):
        result = runner.invoke(main, ["review", "--help"])
        assert result.exit_code == 0
        assert "review" in result.output
        assert "--depth" in result.output
        assert "--incremental" in result.output
        assert "--debug" in result.output

    def test_missing_url_shows_error(self, runner):
        result = runner.invoke(main, ["review"])
        assert result.exit_code != 0

    def test_invalid_depth_rejected(self, runner):
        result = runner.invoke(main, ["review", "https://github.com/a/b/pull/1", "--depth", "invalid"])
        assert result.exit_code != 0

    def test_valid_depth_accepted(self, runner):
        with patch("insightor.cli._review", new_callable=AsyncMock) as mock_review:
            result = runner.invoke(main, ["review", "https://github.com/a/b/pull/1", "--depth", "deep"])
        assert result.exit_code == 0

    def test_debug_flag_accepted(self, runner):
        with patch("insightor.cli._debug_review", new_callable=AsyncMock):
            result = runner.invoke(main, ["review", "https://github.com/a/b/pull/1", "--debug"])
        assert result.exit_code == 0

    def test_incremental_flag_accepted(self, runner):
        with patch("insightor.cli._review", new_callable=AsyncMock) as mock_review:
            result = runner.invoke(main, ["review", "https://github.com/a/b/pull/1", "--incremental"])
        assert result.exit_code == 0


# =============================================================================
# describe
# =============================================================================

class TestDescribeCommand:
    def test_help(self, runner):
        result = runner.invoke(main, ["describe", "--help"])
        assert result.exit_code == 0
        assert "describe" in result.output

    def test_missing_url_shows_error(self, runner):
        result = runner.invoke(main, ["describe"])
        assert result.exit_code != 0

    def test_valid_depth_accepted(self, runner):
        with patch("insightor.cli._describe", new_callable=AsyncMock):
            result = runner.invoke(main, ["describe", "https://github.com/a/b/pull/1", "--depth", "quick"])
        assert result.exit_code == 0


# =============================================================================
# risks
# =============================================================================

class TestRisksCommand:
    def test_help(self, runner):
        result = runner.invoke(main, ["risks", "--help"])
        assert result.exit_code == 0
        assert "risks" in result.output
        assert "--focus" in result.output

    def test_focus_option_accepted(self, runner):
        with patch("insightor.cli._risks", new_callable=AsyncMock):
            result = runner.invoke(main, ["risks", "https://github.com/a/b/pull/1", "--focus", "security"])
        assert result.exit_code == 0


# =============================================================================
# improve
# =============================================================================

class TestImproveCommand:
    def test_help(self, runner):
        result = runner.invoke(main, ["improve", "--help"])
        assert result.exit_code == 0
        assert "improve" in result.output
        assert "--committable-only" in result.output

    def test_committable_only_flag_accepted(self, runner):
        with patch("insightor.cli._improve", new_callable=AsyncMock):
            result = runner.invoke(main, ["improve", "https://github.com/a/b/pull/1", "--committable-only"])
        assert result.exit_code == 0


# =============================================================================
# publish
# =============================================================================

class TestPublishCommand:
    def test_help(self, runner):
        result = runner.invoke(main, ["publish", "--help"])
        assert result.exit_code == 0
        assert "publish" in result.output
        assert "--dry-run" in result.output

    def test_missing_path_shows_error(self, runner):
        result = runner.invoke(main, ["publish"])
        assert result.exit_code != 0

    def test_nonexistent_file_shows_error(self, runner):
        result = runner.invoke(main, ["publish", "/nonexistent/path.md"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_file_without_pr_url_shows_error(self, runner):
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "test.md"
            md.write_text("# No PR URL here", encoding="utf-8")
            result = runner.invoke(main, ["publish", str(md)])
        assert result.exit_code == 1
        assert "PR URL" in result.output

    def test_dry_run_with_valid_markdown(self, runner):
        md_content = """# Insightor Review -- PR #1

> PR: https://github.com/a/b/pull/1

## Findings (1)

### 1. [high] Test Finding <!-- finding-id: 00000000-0000-0000-0000-000000000001 -->

- **Category:** logic
- **File:** `a.py:1`

- [x] confirmed
- [ ] false_positive
- [ ] addressed
- [ ] ignored

<!-- insightor-pr-url: https://github.com/a/b/pull/1 -->
"""
        import json as _json
        json_content = _json.dumps({
            "meta": {"pr_url": "https://github.com/a/b/pull/1", "commit_sha": "abc12345"},
            "summary": {"pr_type": "feature", "overview": "test"},
            "file_walkthrough": [],
            "findings": [{
                "id": "00000000-0000-0000-0000-000000000001",
                "type": "risk", "severity": "high", "category": "logic",
                "title": "Test Finding", "description": "",
                "location": {"path": "a.py", "range": {"start": {"line": 1}, "end": {"line": 1}}},
                "confidence": 0.5, "fingerprint": "",
            }],
            "stats": {"total_findings": 1, "by_severity": {}, "by_category": {}},
        })

        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "insightor-review-1.md"
            md_path.write_text(md_content, encoding="utf-8")

            reviews_dir = Path(tmp) / ".insightor" / "reviews"
            reviews_dir.mkdir(parents=True)
            json_path = reviews_dir / "insightor-review-1-abc12345-20260101-120000.json"
            json_path.write_text(json_content, encoding="utf-8")

            import os as _os
            old_cwd = _os.getcwd()
            try:
                _os.chdir(tmp)
                result = runner.invoke(main, ["publish", str(md_path), "--dry-run"])
                assert result.exit_code == 0
                assert "DRY RUN" in result.output
                assert "Test Finding" in result.output
            finally:
                _os.chdir(old_cwd)


# =============================================================================
# full
# =============================================================================

class TestFullCommand:
    def test_help(self, runner):
        result = runner.invoke(main, ["full", "--help"])
        assert result.exit_code == 0
        assert "full" in result.output
        assert "--skip" in result.output

    def test_missing_url_shows_error(self, runner):
        result = runner.invoke(main, ["full"])
        assert result.exit_code != 0

    def test_skip_option_accepted(self, runner):
        with patch("insightor.cli._full", new_callable=AsyncMock):
            result = runner.invoke(
                main, ["full", "https://github.com/a/b/pull/1",
                       "--skip", "describe", "--skip", "review"]
            )
        assert result.exit_code == 0

    def test_debug_flag_accepted(self, runner):
        with patch("insightor.cli._debug_tool", new_callable=AsyncMock):
            result = runner.invoke(
                main, ["full", "https://github.com/a/b/pull/1", "--debug"]
            )
        assert result.exit_code == 0


# =============================================================================
# full-review publish — only posts improve suggestions
# =============================================================================

class TestFullPublish:
    def test_full_review_publish_filters_to_improve_only(self, runner):
        md_content = """# Insightor Full Review -- PR #1

> PR: https://github.com/a/b/pull/1

---

## 1. PR Summary (describe)

**Type:** feature

---

## 2. Risk Analysis (risks)

### Risk Findings (1)

#### 1. [critical] Risk Title
- **Category:** security
- **File:** `a.py:1`

---

## 3. Code Suggestions (improve)

### Suggestions (1)

#### 1. [medium] Improve Title <!-- finding-id: 00000000-0000-0000-0000-000000000001 -->

- **Category:** maintainability
- **File:** `b.py:10`

- [x] confirmed
- [ ] false_positive
- [ ] addressed
- [ ] ignored

---

<!-- insightor-full-review -->
<!-- insightor-pr-url: https://github.com/a/b/pull/1 -->
"""
        import json as _json
        json_content = _json.dumps({
            "meta": {"pr_url": "https://github.com/a/b/pull/1", "commit_sha": "abc12345"},
            "summary": {"pr_type": "feature", "overview": "test"},
            "file_walkthrough": [],
            "findings": [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "type": "suggestion", "severity": "medium", "category": "maintainability",
                    "title": "Improve Title", "description": "",
                    "location": {"path": "b.py", "range": {"start": {"line": 10}, "end": {"line": 10}}},
                    "confidence": 0.5, "fingerprint": "",
                },
                {
                    "id": "00000000-0000-0000-0000-000000000002",
                    "type": "risk", "severity": "critical", "category": "security",
                    "title": "Risk Title", "description": "",
                    "location": {"path": "a.py", "range": {"start": {"line": 1}, "end": {"line": 1}}},
                    "confidence": 0.9, "fingerprint": "",
                },
            ],
            "stats": {"total_findings": 2, "by_severity": {}, "by_category": {}},
        })

        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "insightor-full-review-1.md"
            md_path.write_text(md_content, encoding="utf-8")

            reviews_dir = Path(tmp) / ".insightor" / "reviews"
            reviews_dir.mkdir(parents=True)
            json_path = reviews_dir / "insightor-review-1-abc12345-20260101-120000.json"
            json_path.write_text(json_content, encoding="utf-8")

            import os as _os
            old_cwd = _os.getcwd()
            try:
                _os.chdir(tmp)
                result = runner.invoke(main, ["publish", str(md_path), "--dry-run"])
                assert result.exit_code == 0
                assert "Full review detected" in result.output
                # Risk finding should NOT appear (only improve)
                assert "Risk Title" not in result.output
                # Improve finding SHOULD appear
                assert "Improve Title" in result.output
            finally:
                _os.chdir(old_cwd)
