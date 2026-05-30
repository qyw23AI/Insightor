"""测试 Universal Review Format Schema。"""

import pytest
from insightor.schemas.urf import (
    AnalysisDepth,
    CodeSuggestion,
    EditType,
    FeedbackStatus,
    FileWalkthrough,
    Finding,
    FindingFeedback,
    FindingType,
    IncrementalStats,
    Location,
    MergeReadiness,
    MergeRecommendation,
    Position,
    PRSummary,
    QualityMetrics,
    Range,
    ReviewMeta,
    ReviewResult,
    ReviewStats,
    Severity,
)


class TestPRSummary:
    def test_default(self):
        s = PRSummary()
        assert s.pr_type == ""
        assert s.overview == ""

    def test_full(self):
        s = PRSummary(pr_type="feature", overview="添加了登录功能", files_changed=5, additions=100, deletions=20)
        assert s.pr_type == "feature"
        assert s.files_changed == 5


class TestFinding:
    def test_minimal(self):
        loc = Location(path="src/test.py", range=Range(start=Position(line=1), end=Position(line=1)))
        f = Finding(type=FindingType.RISK, severity=Severity.HIGH, category="security",
                     title="test", description="test", location=loc)
        assert f.confidence == 0.5
        assert f.fingerprint == ""

    def test_with_feedback(self):
        loc = Location(path="src/test.py", range=Range(start=Position(line=1), end=Position(line=1)))
        f = Finding(type=FindingType.RISK, severity=Severity.HIGH, category="security",
                     title="test", description="test", location=loc,
                     feedback=FindingFeedback(status=FeedbackStatus.CONFIRMED))
        assert f.feedback is not None
        assert f.feedback.status == FeedbackStatus.CONFIRMED

    def test_with_suggestion(self):
        loc = Location(path="src/test.py", range=Range(start=Position(line=1), end=Position(line=1)))
        f = Finding(type=FindingType.SUGGESTION, severity=Severity.MEDIUM, category="style",
                     title="命名建议", description="变量名应更有描述性", location=loc,
                     suggestion=CodeSuggestion(current_code="x = 1", suggested_code="user_count = 1", is_committable=True))
        assert f.suggestion is not None
        assert f.suggestion.is_committable is True


class TestMergeReadiness:
    def test_score_bounds(self):
        mr = MergeReadiness(score=75.5)
        assert 0 <= mr.score <= 100

    def test_defaults(self):
        mr = MergeReadiness()
        assert mr.recommendation == MergeRecommendation.NEEDS_REVIEW
        assert mr.review_priority == "medium"
        assert mr.blocking_issues == []


class TestQualityMetrics:
    def test_defaults(self):
        qm = QualityMetrics()
        assert qm.confidence_distribution == {}
        assert qm.self_reflection_avg_score is None


class TestReviewResult:
    def test_minimal(self):
        meta = ReviewMeta(pr_url="https://github.com/owner/repo/pull/1")
        result = ReviewResult(meta=meta)
        assert result.meta.pr_url == "https://github.com/owner/repo/pull/1"
        assert result.findings == []
        assert result.merge_readiness is None

    def test_full_v3_fields(self):
        meta = ReviewMeta(
            pr_url="https://github.com/owner/repo/pull/1",
            analysis_depth=AnalysisDepth.DEEP,
            is_incremental=True,
            context_layers=["diff", "issues", "related_files"],
        )
        result = ReviewResult(
            meta=meta,
            stats=ReviewStats(
                total_findings=5,
                by_severity={"high": 2, "medium": 3},
                incremental=IncrementalStats(new=2, resolved=1, reconfirmed=2),
                quality=QualityMetrics(test_files_in_diff=1),
            ),
            merge_readiness=MergeReadiness(score=75, recommendation=MergeRecommendation.NEEDS_REVIEW),
        )
        assert result.meta.is_incremental is True
        assert result.stats.total_findings == 5
        assert result.stats.incremental.new == 2
        assert result.merge_readiness.score == 75
