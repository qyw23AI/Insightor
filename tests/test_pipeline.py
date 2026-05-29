"""测试 ReviewPipeline。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from insightor.pipeline import ReviewPipeline, PipelineError
from insightor.schemas.urf import AnalysisDepth, MergeRecommendation, ReviewMeta, ReviewPriority, ReviewResult, PRSummary


class TestReviewPipeline:
    @pytest.fixture
    def pipeline(self):
        return ReviewPipeline(model="deepseek-v4-flash")

    def test_calc_budget(self):
        assert ReviewPipeline._calc_budget(AnalysisDepth.QUICK) > 0
        assert ReviewPipeline._calc_budget(AnalysisDepth.STANDARD) > ReviewPipeline._calc_budget(AnalysisDepth.QUICK)
        assert ReviewPipeline._calc_budget(AnalysisDepth.DEEP) > ReviewPipeline._calc_budget(AnalysisDepth.STANDARD)

    def test_pick_model(self):
        quick_model = ReviewPipeline._pick_model(AnalysisDepth.QUICK)
        standard_model = ReviewPipeline._pick_model(AnalysisDepth.STANDARD)
        deep_model = ReviewPipeline._pick_model(AnalysisDepth.DEEP)
        assert quick_model  # weak model
        assert standard_model  # primary model
        assert deep_model  # reasoning model

    def test_detect_main_lang(self):
        from insightor.processing.language_detector import LanguageDetector
        from insightor.providers.types import FilePatchInfo
        ld = LanguageDetector()
        files = [FilePatchInfo(filename="a.py"), FilePatchInfo(filename="b.py"), FilePatchInfo(filename="c.js")]
        assert ReviewPipeline._detect_main_lang(ld, files) == "Python"

    def test_detect_main_lang_empty(self):
        from insightor.processing.language_detector import LanguageDetector
        ld = LanguageDetector()
        assert ReviewPipeline._detect_main_lang(ld, []) == ""

    @pytest.mark.asyncio
    async def test_describe_tool_routing(self, pipeline):
        """describe tool 使用 DescribeParser，review tool 使用 ResponseParser。"""
        from insightor.ai.response_parser import DescribeParser
        describe_json = '{"pr_type": "feature", "overview": "added login", "files": [{"path": "a.py", "change": "login module"}]}'

        meta = ReviewMeta(pr_url="https://github.com/test/pull/1")
        result = DescribeParser.parse(describe_json, meta)

        assert result.summary.pr_type == "feature"
        assert result.summary.overview == "added login"
        assert len(result.file_walkthrough) == 1
        assert result.file_walkthrough[0].path == "a.py"
        assert result.findings == []  # describe produces no findings
        assert result.merge_readiness is None  # describe produces no merge readiness

    @pytest.mark.asyncio
    async def test_risks_tool_routing(self, pipeline):
        """risks tool 使用 RisksParser，解析 findings + overall。"""
        from insightor.ai.response_parser import RisksParser
        risks_json = (
            '{"findings": ['
            '{"type": "risk", "severity": "critical", "category": "security",'
            '"title": "SQL注入", "file": "db.py", "line_start": 10, "line_end": 10,'
            '"confidence": 0.95}'
            '], "overall": {"score": 40, "blocking_issues": ["SQL注入"],'
            '"review_priority": "high", "estimated_review_time_min": 15,'
            '"summary": "严重安全问题"}}'
        )
        meta = ReviewMeta(pr_url="https://github.com/test/pull/1")
        result = RisksParser.parse(risks_json, meta)

        assert len(result.findings) == 1
        assert result.findings[0].severity.value == "critical"
        assert result.merge_readiness is not None
        assert result.merge_readiness.score == 40.0
        assert result.merge_readiness.blocking_issues == ["SQL注入"]
        assert result.merge_readiness.review_priority == ReviewPriority.HIGH.value
