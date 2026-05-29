"""Test Feedback Layer: DraftParser, QualityTracker, FeedbackCollector."""

import tempfile
from pathlib import Path
from uuid import UUID

import pytest

from insightor.feedback.collector import FeedbackCollector
from insightor.feedback.draft_parser import DraftParser
from insightor.feedback.quality_tracker import QualityTracker
from insightor.schemas.urf import (
    FeedbackStatus,
    Finding,
    FindingFeedback,
    FindingType,
    Location,
    Position,
    PRSummary,
    Range,
    ReviewMeta,
    ReviewResult,
    ReviewStats,
    Severity,
)


# =============================================================================
# Factories
# =============================================================================

def _make_result(findings=None):
    return ReviewResult(
        meta=ReviewMeta(pr_url="https://github.com/a/b/pull/1", commit_sha="abc12345"),
        summary=PRSummary(pr_type="feature", overview="test"),
        findings=findings or [],
        stats=ReviewStats(total_findings=len(findings or [])),
    )


def _make_finding(title="test", severity="medium", category="logic",
                  path="a.py", fid=None):
    return Finding(
        id=fid or UUID("00000000-0000-0000-0000-000000000001"),
        type=FindingType.RISK,
        severity=severity,
        category=category,
        title=title,
        description="test description",
        location=Location(
            path=path,
            range=Range(start=Position(line=1), end=Position(line=1)),
        ),
    )


# =============================================================================
# DraftParser
# =============================================================================

MD_NO_FEEDBACK = """\
# Insightor Review — PR #1

## 发现 (1)

### 1. 🔴 [high] Test Finding <!-- finding-id: 00000000-0000-0000-0000-000000000001 -->

- **类别:** logic
- **文件:** `a.py:1`
"""

MD_CONFIRMED = """\
# Insightor Review — PR #1

## 发现 (1)

### 1. 🔴 [high] Test Finding <!-- finding-id: 00000000-0000-0000-0000-000000000001 -->

- **类别:** logic
- **文件:** `a.py:1`
- **说明:** test description

- [ ] confirmed
- [x] false_positive
- [ ] addressed
- [ ] ignored
- **审查者:** dev@example.com
- **备注:** This is fine, handled by middleware
"""

MD_MULTIPLE = """\
# Insightor Review — PR #1

## 发现 (2)

### 1. 🔴 [high] Finding A <!-- finding-id: 00000000-0000-0000-0000-000000000001 -->

- **类别:** logic
- **文件:** `a.py:1`

- [x] confirmed
- [ ] false_positive
- [ ] addressed
- [ ] ignored

### 2. 🔴 [critical] Finding B <!-- finding-id: 00000000-0000-0000-0000-000000000002 -->

- **类别:** security
- **文件:** `b.py:42`

- [ ] confirmed
- [ ] false_positive
- [x] addressed
- [ ] ignored
"""

MD_NO_CHECKBOX = """\
# Insightor Review — PR #1

## 发现 (1)

### 1. 🔴 [high] Test <!-- finding-id: 00000000-0000-0000-0000-000000000001 -->

- **类别:** logic
- **文件:** `a.py:1`
"""


class TestDraftParser:
    def test_parse_no_feedback(self):
        orig = _make_result(findings=[_make_finding()])
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "draft.md"
            md.write_text(MD_NO_FEEDBACK, encoding="utf-8")
            updated, changes = DraftParser.parse(str(md), orig)
        assert changes == 0
        assert updated.findings[0].feedback is None

    def test_parse_confirmed_feedback(self):
        orig = _make_result(findings=[_make_finding()])
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "draft.md"
            md.write_text(MD_CONFIRMED, encoding="utf-8")
            updated, changes = DraftParser.parse(str(md), orig)
        assert changes == 1
        fb = updated.findings[0].feedback
        assert fb is not None
        assert fb.status == FeedbackStatus.FALSE_POSITIVE
        assert fb.reviewed_by == "dev@example.com"
        assert fb.reviewer_note == "This is fine, handled by middleware"

    def test_parse_multiple_findings(self):
        f1 = _make_finding("A", "high", "logic", "a.py",
                           fid=UUID("00000000-0000-0000-0000-000000000001"))
        f2 = _make_finding("B", "critical", "security", "b.py",
                           fid=UUID("00000000-0000-0000-0000-000000000002"))
        orig = _make_result(findings=[f1, f2])
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "draft.md"
            md.write_text(MD_MULTIPLE, encoding="utf-8")
            updated, changes = DraftParser.parse(str(md), orig)
        assert changes == 2
        assert updated.findings[0].feedback.status == FeedbackStatus.CONFIRMED
        assert updated.findings[1].feedback.status == FeedbackStatus.ADDRESSED

    def test_parse_no_checkbox_section(self):
        orig = _make_result(findings=[_make_finding()])
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "draft.md"
            md.write_text(MD_NO_CHECKBOX, encoding="utf-8")
            updated, changes = DraftParser.parse(str(md), orig)
        assert changes == 0
        assert updated.findings[0].feedback is None

    def test_parse_unknown_id(self):
        unknown_md = MD_NO_FEEDBACK.replace(
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000009999",
        )
        orig = _make_result(findings=[_make_finding()])
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "draft.md"
            md.write_text(unknown_md, encoding="utf-8")
            updated, changes = DraftParser.parse(str(md), orig)
        assert changes == 0
        assert updated.findings[0].feedback is None

    def test_parse_empty_findings(self):
        orig = _make_result(findings=[])
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "draft.md"
            md.write_text(MD_CONFIRMED, encoding="utf-8")
            updated, changes = DraftParser.parse(str(md), orig)
        assert changes == 0

    def test_parse_reviewer_note_only_no_checkbox(self):
        md_text = MD_NO_FEEDBACK + (
            "- **审查者:** someone\n"
            "- **备注:** a note\n"
        )
        orig = _make_result(findings=[_make_finding()])
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "draft.md"
            md.write_text(md_text, encoding="utf-8")
            updated, changes = DraftParser.parse(str(md), orig)
        assert changes == 0


# =============================================================================
# QualityTracker
# =============================================================================

class TestQualityTracker:
    def test_track_confirmed(self):
        f = _make_finding(category="security")
        f.feedback = FindingFeedback(status=FeedbackStatus.CONFIRMED)
        result = _make_result(findings=[f])

        with tempfile.TemporaryDirectory() as tmp:
            qt = QualityTracker(storage_dir=tmp)
            qt.track(result)
            assert qt.get_precision("security") == 1.0

    def test_track_mixed_feedback(self):
        f1 = _make_finding("A", category="security")
        f1.feedback = FindingFeedback(status=FeedbackStatus.CONFIRMED)
        f2 = _make_finding("B", category="security")
        f2.feedback = FindingFeedback(status=FeedbackStatus.FALSE_POSITIVE)
        f3 = _make_finding("C", category="security")
        f3.feedback = FindingFeedback(status=FeedbackStatus.CONFIRMED)
        result = _make_result(findings=[f1, f2, f3])

        with tempfile.TemporaryDirectory() as tmp:
            qt = QualityTracker(storage_dir=tmp)
            qt.track(result)
            assert qt.get_precision("security") == pytest.approx(2.0 / 3.0)

    def test_get_precision_no_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            qt = QualityTracker(storage_dir=tmp)
            assert qt.get_precision("nonexistent") == 0.0

    def test_get_precision_multiple_categories(self):
        f1 = _make_finding("A", category="security")
        f1.feedback = FindingFeedback(status=FeedbackStatus.CONFIRMED)
        f2 = _make_finding("B", category="performance")
        f2.feedback = FindingFeedback(status=FeedbackStatus.FALSE_POSITIVE)
        result = _make_result(findings=[f1, f2])

        with tempfile.TemporaryDirectory() as tmp:
            qt = QualityTracker(storage_dir=tmp)
            qt.track(result)
            assert qt.get_precision("security") == 1.0
            assert qt.get_precision("performance") == 0.0

    def test_export_metrics(self):
        f1 = _make_finding("A", category="security")
        f1.feedback = FindingFeedback(status=FeedbackStatus.CONFIRMED)
        f2 = _make_finding("B", category="performance")
        f2.feedback = FindingFeedback(status=FeedbackStatus.FALSE_POSITIVE)
        result = _make_result(findings=[f1, f2])

        with tempfile.TemporaryDirectory() as tmp:
            qt = QualityTracker(storage_dir=tmp)
            qt.track(result)
            metrics = qt.export_metrics()
            assert "security" in metrics.historical_precision
            assert "performance" in metrics.historical_precision
            assert metrics.historical_precision["security"] == 1.0

    def test_persistence(self):
        f = _make_finding(category="logic")
        f.feedback = FindingFeedback(status=FeedbackStatus.CONFIRMED)
        result = _make_result(findings=[f])

        with tempfile.TemporaryDirectory() as tmp:
            qt1 = QualityTracker(storage_dir=tmp)
            qt1.track(result)
            qt2 = QualityTracker(storage_dir=tmp)
            assert qt2.get_precision("logic") == 1.0
            assert "logic" in qt2.export_metrics().historical_precision

    def test_track_no_feedback_skip(self):
        f = _make_finding(category="security")
        f.feedback = None
        result = _make_result(findings=[f])

        with tempfile.TemporaryDirectory() as tmp:
            qt = QualityTracker(storage_dir=tmp)
            qt.track(result)
            assert qt.get_precision("security") == 0.0

    def test_cumulative_tracking(self):
        f1 = _make_finding("A", category="security")
        f1.feedback = FindingFeedback(status=FeedbackStatus.CONFIRMED)
        f2 = _make_finding("B", category="security")
        f2.feedback = FindingFeedback(status=FeedbackStatus.CONFIRMED)

        with tempfile.TemporaryDirectory() as tmp:
            qt = QualityTracker(storage_dir=tmp)
            qt.track(_make_result(findings=[f1]))
            qt.track(_make_result(findings=[f2]))
            assert qt.get_precision("security") == 1.0


# =============================================================================
# FeedbackCollector
# =============================================================================

class TestFeedbackCollector:
    @pytest.mark.asyncio
    async def test_collect_noop(self):
        collector = FeedbackCollector()
        result = _make_result()
        returned = await collector.collect(result)
        assert returned is result

    @pytest.mark.asyncio
    async def test_read_comment_reactions_raises(self):
        collector = FeedbackCollector()
        with pytest.raises(NotImplementedError):
            await collector.read_comment_reactions(
                "https://api.github.com/repos/a/b/issues/comments/123"
            )
