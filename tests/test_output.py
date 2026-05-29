"""测试 Output 层：CompositeOutput, ConsoleOutput, MarkdownFileOutput, JSONOutput, FingerprintGenerator。"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from insightor.output.base import CompositeOutput
from insightor.output.console import ConsoleOutput
from insightor.output.fingerprint import FingerprintGenerator
from insightor.output.json_output import JSONOutput
from insightor.output.markdown import MarkdownFileOutput
from insightor.schemas.urf import (
    CodeSuggestion,
    Finding,
    FindingType,
    Location,
    MergeReadiness,
    Position,
    PRSummary,
    Range,
    ReviewMeta,
    ReviewResult,
    ReviewStats,
    Severity,
)


def _make_result(findings=None, summary=None, merge_readiness=None):
    return ReviewResult(
        meta=ReviewMeta(pr_url="https://github.com/a/b/pull/1", commit_sha="abc12345"),
        summary=summary or PRSummary(pr_type="feature", overview="测试审查"),
        findings=findings or [],
        stats=ReviewStats(total_findings=len(findings or [])),
        merge_readiness=merge_readiness,
    )


def _make_finding(title="test", severity="medium", category="logic", path="a.py"):
    return Finding(
        type=FindingType.RISK,
        severity=severity,
        category=category,
        title=title,
        description="测试描述",
        location=Location(path=path, range=Range(start=Position(line=1), end=Position(line=1))),
        suggestion=CodeSuggestion(current_code="old", suggested_code="new"),
    )


# =============================================================================
# FingerprintGenerator
# =============================================================================

class TestFingerprintGenerator:
    def test_generate_consistent(self):
        f1 = _make_finding("aa", "high", "security", "x.py")
        f2 = _make_finding("aa", "high", "security", "x.py")
        assert FingerprintGenerator.generate(f1) == FingerprintGenerator.generate(f2)

    def test_generate_different(self):
        f1 = _make_finding("aa", "high", "security", "x.py")
        f2 = _make_finding("bb", "high", "security", "x.py")
        assert FingerprintGenerator.generate(f1) != FingerprintGenerator.generate(f2)

    def test_deduplicate_removes_dupes(self):
        f1 = _make_finding("dup", "high", "security", "x.py")
        f2 = _make_finding("dup", "high", "security", "x.py")
        f3 = _make_finding("unique", "low", "style", "y.py")
        result = FingerprintGenerator.deduplicate([f1, f2, f3])
        assert len(result) == 2

    def test_deduplicate_sets_fingerprint(self):
        f = _make_finding("aa")
        result = FingerprintGenerator.deduplicate([f])
        assert result[0].fingerprint != ""

    def test_deduplicate_empty(self):
        assert FingerprintGenerator.deduplicate([]) == []


# =============================================================================
# CompositeOutput
# =============================================================================

class SpyService:
    """测试用 spy：记录 post/flush 调用。"""
    def __init__(self):
        self.posted: list[ReviewResult] = []
        self.flushed = False

    def post(self, result):
        self.posted.append(result)

    def flush(self):
        self.flushed = True


class TestCompositeOutput:
    def test_post_calls_all_services(self):
        s1, s2 = SpyService(), SpyService()
        co = CompositeOutput([s1, s2])
        result = _make_result()
        co.post(result)
        assert len(s1.posted) == 1
        assert len(s2.posted) == 1

    def test_flush_calls_all_services(self):
        s1, s2 = SpyService(), SpyService()
        co = CompositeOutput([s1, s2])
        co.flush()
        assert s1.flushed
        assert s2.flushed

    def test_post_swallows_errors(self):
        class FailingService:
            def post(self, result):
                raise RuntimeError("fail")
            def flush(self):
                pass
        co = CompositeOutput([FailingService(), SpyService()])
        co.post(_make_result())  # should not raise

    def test_add_appends(self):
        s1, s2 = SpyService(), SpyService()
        co = CompositeOutput([s1])
        co.add(s2)
        co.post(_make_result())
        assert len(s1.posted) == 1
        assert len(s2.posted) == 1


# =============================================================================
# ConsoleOutput
# =============================================================================

class TestConsoleOutput:
    def test_post_no_findings(self):
        co = ConsoleOutput()
        co.post(_make_result())  # 不应抛异常

    def test_post_with_findings(self):
        findings = [_make_finding(f"f{i}") for i in range(3)]
        co = ConsoleOutput()
        co.post(_make_result(findings=findings))  # 不应抛异常

    def test_post_with_merge_readiness(self):
        result = _make_result(
            findings=[_make_finding("critical_finding", "critical", "security")],
            merge_readiness=MergeReadiness(score=70, blocking_issues=["critical_finding"], summary="需修复"),
        )
        ConsoleOutput().post(result)  # 不应抛异常


# =============================================================================
# MarkdownFileOutput
# =============================================================================

class TestMarkdownFileOutput:
    def test_post_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = MarkdownFileOutput(output_dir=tmp)
            result = _make_result(
                findings=[_make_finding("密钥硬编码", "high", "security", "auth.py")],
                merge_readiness=MergeReadiness(score=70, summary="需审查"),
            )
            md.post(result)
            md.flush()
            files = list(Path(tmp).glob("*.md"))
            assert len(files) == 1
            content = files[0].read_text(encoding="utf-8")
            assert "Insightor Review" in content
            assert "密钥硬编码" in content
            assert "70" in content

    def test_post_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = MarkdownFileOutput(output_dir=tmp)
            md.post(_make_result())
            files = list(Path(tmp).glob("*.md"))
            assert len(files) == 1
            content = files[0].read_text(encoding="utf-8")
            assert "Insightor Review" in content
            assert "feature" in content

    def test_post_with_multiple_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            md = MarkdownFileOutput(output_dir=tmp)
            findings = [_make_finding(f"f{i}", "medium", "logic", f"f{i}.py") for i in range(5)]
            md.post(_make_result(findings=findings))
            content = list(Path(tmp).glob("*.md"))[0].read_text(encoding="utf-8")
            assert "发现 (5)" in content


# =============================================================================
# JSONOutput
# =============================================================================

class TestJSONOutput:
    def test_post_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            jo = JSONOutput(output_dir=tmp)
            result = _make_result(
                findings=[_make_finding("test_finding")],
                merge_readiness=MergeReadiness(score=85),
            )
            jo.post(result)
            files = list(Path(tmp).glob("*.json"))
            assert len(files) == 1
            data = json.loads(files[0].read_text(encoding="utf-8"))
            assert data["meta"]["pr_url"] == "https://github.com/a/b/pull/1"
            assert len(data["findings"]) == 1

    def test_post_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            jo = JSONOutput(output_dir=tmp)
            result = _make_result()
            jo.post(result)
            files = list(Path(tmp).glob("*.json"))
            data = json.loads(files[0].read_text(encoding="utf-8"))
            assert "meta" in data
            assert "summary" in data
            assert "findings" in data

    def test_post_creates_dir_if_not_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = os.path.join(tmp, "nested", "reviews")
            jo = JSONOutput(output_dir=outdir)
            jo.post(_make_result())
            assert Path(outdir).exists()
            assert len(list(Path(outdir).glob("*.json"))) == 1
