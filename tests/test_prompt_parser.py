"""测试 PromptBuilder 和 ResponseParser。"""

import pytest

from insightor.ai.prompt_builder import PromptBuilder
from insightor.ai.response_parser import ResponseParser, DescribeParser, _extract_json
from insightor.schemas.urf import ReviewMeta, MergeRecommendation


# =============================================================================
# PromptBuilder
# =============================================================================

class TestPromptBuilder:
    @pytest.fixture
    def builder(self):
        return PromptBuilder()

    def test_build_review(self, builder):
        sys_p, usr_p = builder.build("review", {"title": "test", "diff": "diff content"})
        assert "代码审查" in sys_p
        assert "test" in usr_p
        assert "diff content" in usr_p

    def test_build_describe(self, builder):
        sys_p, usr_p = builder.build("describe", {"title": "test", "diff": "x"})
        assert "文档撰写" in sys_p or "总结" in sys_p
        assert "test" in usr_p

    def test_build_risks(self, builder):
        sys_p, usr_p = builder.build("risks", {"title": "test", "diff": "x"})
        assert "安全" in sys_p or "风险" in sys_p or "审计" in sys_p

    def test_custom_rules_injected(self, builder):
        sys_p, _ = builder.build("review", {
            "title": "t", "diff": "d",
            "custom_rules": ["规则A", "规则B"],
        })
        assert "规则A" in sys_p
        assert "规则B" in sys_p

    def test_focus_categories_injected(self, builder):
        _, usr_p = builder.build("risks", {
            "title": "t", "diff": "d",
            "focus_categories": ["security", "performance"],
        })
        assert "security" in usr_p

    def test_caching(self, builder):
        sys1, _ = builder.build("review", {"title": "a", "diff": "d"})
        sys2, _ = builder.build("review", {"title": "b", "diff": "e"})
        assert sys1 == sys2  # system prompt same for same tool

    def test_unknown_tool_raises(self, builder):
        with pytest.raises(FileNotFoundError):
            builder.build("nonexistent", {})


# =============================================================================
# ResponseParser
# =============================================================================

class TestExtractJSON:
    def test_pure_json(self):
        assert _extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_fenced(self):
        raw = '```json\n{"a": 1}\n```'
        assert _extract_json(raw) == {"a": 1}

    def test_markdown_fenced_no_lang(self):
        raw = '```\n{"a": 1}\n```'
        assert _extract_json(raw) == {"a": 1}

    def test_json_with_surrounding_text(self):
        raw = '一些文字\n{"a": 1}\n更多文字'
        assert _extract_json(raw) == {"a": 1}

    def test_invalid_returns_empty(self):
        assert _extract_json("not json at all") == {}


class TestResponseParser:
    @pytest.fixture
    def meta(self):
        return ReviewMeta(pr_url="https://github.com/a/b/pull/1")

    def test_parse_basic(self, meta):
        data = {
            "summary": {"pr_type": "feature", "overview": "添加了登录"},
            "findings": [
                {"type": "risk", "severity": "high", "category": "security",
                 "title": "密钥硬编码", "description": "JWT secret 写死在代码中",
                 "file": "login.py", "line_start": 10, "line_end": 10,
                 "suggestion": "改用环境变量", "confidence": 0.9},
            ],
            "overall": {"score": 70, "summary": "需要修复安全问题"},
        }
        result = ResponseParser.from_dict(data, meta)
        assert result.summary.pr_type == "feature"
        assert result.summary.overview == "添加了登录"
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.severity.value == "high"
        assert f.category == "security"
        assert f.location.path == "login.py"
        assert f.suggestion is not None
        assert f.confidence == 0.9

    def test_parse_empty(self, meta):
        result = ResponseParser.from_dict({}, meta)
        assert result.summary.overview == ""
        assert result.findings == []

    def test_parse_with_files(self, meta):
        data = {
            "files": [
                {"path": "a.py", "change": "添加登录"},
                {"path": "b.py", "change": "删除旧代码"},
            ],
        }
        result = ResponseParser.from_dict(data, meta)
        assert len(result.file_walkthrough) == 2

    def test_merge_readiness_score_range(self, meta):
        data = {"overall": {"score": 85}}
        result = ResponseParser.from_dict(data, meta)
        assert result.merge_readiness is not None
        assert result.merge_readiness.recommendation == MergeRecommendation.SAFE_TO_MERGE

    def test_unknown_severity_falls_to_medium(self, meta):
        data = {"findings": [{"severity": "unknown_level", "category": "style",
                               "title": "t", "description": "d", "file": "f.py",
                               "line_start": 1, "line_end": 1}]}
        result = ResponseParser.from_dict(data, meta)
        assert result.findings[0].severity.value == "medium"

    def test_parse_raw_string(self, meta):
        raw = '{"summary": {"pr_type": "bugfix", "overview": "修复了崩溃"}}'
        result = ResponseParser.parse(raw, meta)
        assert result.summary.pr_type == "bugfix"


# =============================================================================
# DescribeParser
# =============================================================================

class TestDescribeParser:
    @pytest.fixture
    def meta(self):
        return ReviewMeta(pr_url="https://github.com/a/b/pull/1", files_analyzed=3)

    def test_from_dict_basic(self, meta):
        data = {"pr_type": "feature", "overview": "添加用户认证模块"}
        result = DescribeParser.from_dict(data, meta)
        assert result.summary.pr_type == "feature"
        assert result.summary.overview == "添加用户认证模块"
        assert result.summary.diagram == ""
        assert result.file_walkthrough == []
        assert result.findings == []

    def test_from_dict_full_with_diagram(self, meta):
        data = {
            "pr_type": "feature",
            "overview": "添加 JWT 登录与刷新功能",
            "files": [
                {"path": "src/auth/login.py", "change": "添加 JWT token 生成"},
                {"path": "src/auth/refresh.py", "change": "添加 token 刷新逻辑"},
            ],
            "diagram": "flowchart TD\n  Login-->JWT-->Refresh",
        }
        result = DescribeParser.from_dict(data, meta)
        assert result.summary.pr_type == "feature"
        assert "JWT" in result.summary.overview
        assert "flowchart TD" in result.summary.diagram
        assert len(result.file_walkthrough) == 2
        assert result.file_walkthrough[0].path == "src/auth/login.py"
        assert result.file_walkthrough[0].summary == "添加 JWT token 生成"
        assert result.findings == []
        assert result.merge_readiness is None

    def test_from_dict_empty(self, meta):
        result = DescribeParser.from_dict({}, meta)
        assert result.summary.pr_type == ""
        assert result.summary.overview == ""
        assert result.summary.diagram == ""
        assert result.file_walkthrough == []

    def test_from_dict_with_files(self, meta):
        data = {
            "files": [
                {"path": "a.py", "change": "重构登录逻辑"},
                {"path": "tests/test_b.py", "change": "新增 session 测试"},
            ],
        }
        result = DescribeParser.from_dict(data, meta)
        assert len(result.file_walkthrough) == 2
        assert result.file_walkthrough[1].path == "tests/test_b.py"

    def test_from_dict_files_edit_type(self, meta):
        data = {
            "files": [
                {"path": "new.py", "change": "add login module"},
                {"path": "old.py", "change": "delete deprecated code"},
                {"path": "moved.py", "change": "rename module"},
            ],
        }
        result = DescribeParser.from_dict(data, meta)
        assert result.file_walkthrough[0].edit_type.value == "added"
        assert result.file_walkthrough[1].edit_type.value == "deleted"
        assert result.file_walkthrough[2].edit_type.value == "renamed"

    def test_parse_raw(self, meta):
        raw = '{"pr_type": "docs", "overview": "更新 README"}'
        result = DescribeParser.parse(raw, meta)
        assert result.summary.pr_type == "docs"
        assert result.summary.overview == "更新 README"

    def test_parse_returns_review_result(self, meta):
        raw = '{"pr_type": "refactor"}'
        result = DescribeParser.parse(raw, meta)
        assert result.meta == meta
        assert result.summary.pr_type == "refactor"
        assert result.file_walkthrough == []
        assert result.findings == []
