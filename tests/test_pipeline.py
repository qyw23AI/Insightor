"""测试 ReviewPipeline。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from insightor.pipeline import ReviewPipeline, PipelineError
from insightor.schemas.urf import AnalysisDepth, MergeRecommendation, ReviewMeta, ReviewResult, PRSummary


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
