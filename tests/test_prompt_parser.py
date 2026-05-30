"""测试 PromptBuilder 和 ResponseParser。"""

import pytest

from insightor.ai.prompt_builder import PromptBuilder
from insightor.ai.response_parser import (
    ResponseParser, DescribeParser, RisksParser,
    MergeReadinessCalc, _extract_json,
)
from insightor.schemas.urf import (
    ReviewMeta, MergeRecommendation, MergeReadiness,
    ReviewPriority, Finding, Severity, Location, Range, Position,
)


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

class TestRepairTruncatedJSON:
    def test_truncated_mid_array(self):
        from insightor.ai.response_parser import _repair_truncated_json
        truncated = '{"findings": [{"title": "a"}, {"title": "b"'
        repaired = _repair_truncated_json(truncated)
        assert repaired is not None
        import json
        data = json.loads(repaired)
        assert len(data["findings"]) == 2

    def test_truncated_mid_string(self):
        from insightor.ai.response_parser import _repair_truncated_json
        truncated = '{"summary": {"overview": "something'
        repaired = _repair_truncated_json(truncated)
        # 不完整字符串被闭合并补齐括号 → 可解析
        assert repaired is not None
        import json
        data = json.loads(repaired)
        assert data["summary"]["overview"] == "something"

    def test_not_truncated(self):
        from insightor.ai.response_parser import _repair_truncated_json
        assert _repair_truncated_json('{"a": 1}') is None

    def test_extract_repairs_truncated(self):
        from insightor.ai.response_parser import _extract_json
        raw = '```json\n{"findings": [{"severity": "high", "category": "security", "title": "SQL注入", "file": "db.py", "line_start": 10, "line_end": 10, "confidence": 0.9}, {"severity": "medium"'
        data = _extract_json(raw)
        assert len(data.get("findings", [])) >= 1


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


# =============================================================================
# MergeReadinessCalc
# =============================================================================

def _make_finding(severity: str, title: str = "test", category: str = "logic") -> Finding:
    from insightor.schemas.urf import FindingType
    return Finding(
        type=FindingType.RISK,
        severity=severity,
        category=category,
        title=title,
        description="测试描述",
        location=Location(path="a.py", range=Range(start=Position(line=1), end=Position(line=1))),
    )


class TestMergeReadinessCalc:
    @pytest.fixture
    def calc(self):
        return MergeReadinessCalc()

    def test_no_findings(self):
        mr = MergeReadinessCalc.calculate([])
        assert mr.score == 100.0
        assert mr.recommendation == MergeRecommendation.SAFE_TO_MERGE
        assert mr.blocking_issues == []
        assert mr.review_priority == ReviewPriority.LOW.value

    def test_critical_only(self):
        findings = [_make_finding("critical", "SQL注入")]
        mr = MergeReadinessCalc.calculate(findings)
        assert mr.score == 70.0
        assert mr.recommendation == MergeRecommendation.NEEDS_REVIEW
        assert "SQL注入" in mr.blocking_issues
        assert mr.review_priority == ReviewPriority.HIGH.value

    def test_critical_blocks(self):
        findings = [
            _make_finding("critical", f"风险{i}")
            for i in range(3)
        ]
        mr = MergeReadinessCalc.calculate(findings)
        assert mr.score == 10.0
        assert mr.recommendation == MergeRecommendation.BLOCKED
        assert len(mr.blocking_issues) == 3

    def test_high_threshold_blocking(self):
        findings = [
            _make_finding("high", f"高{i}")
            for i in range(4)
        ]
        mr = MergeReadinessCalc.calculate(findings)
        assert mr.score == 60.0
        assert len(mr.blocking_issues) == 4

    def test_few_high_no_blocking(self):
        findings = [_make_finding("high", "高1"), _make_finding("high", "高2")]
        mr = MergeReadinessCalc.calculate(findings)
        assert len(mr.blocking_issues) == 0

    def test_mixed_severities(self):
        findings = [
            _make_finding("critical", "c1"),
            _make_finding("high", "h1"),
            _make_finding("medium", "m1"),
            _make_finding("medium", "m2"),
            _make_finding("low", "l1"),
        ]
        mr = MergeReadinessCalc.calculate(findings)
        assert mr.score == 53.0  # 100 - 30 - 10 - 3*2 - 1 = 53

    def test_score_clamped_low(self):
        findings = [_make_finding("critical", f"阻断{i}") for i in range(10)]
        mr = MergeReadinessCalc.calculate(findings)
        assert mr.score == 0.0

    def test_score_clamped_high(self):
        mr = MergeReadinessCalc.calculate([], files_changed=0)
        assert mr.score == 100.0

    def test_review_priority_high(self):
        findings = [_make_finding("high", "h1")]
        mr = MergeReadinessCalc.calculate(findings)
        assert mr.review_priority == ReviewPriority.MEDIUM.value

    def test_review_priority_files(self):
        mr = MergeReadinessCalc.calculate([], files_changed=11)
        assert mr.review_priority == ReviewPriority.MEDIUM.value

    def test_review_priority_low(self):
        mr = MergeReadinessCalc.calculate([], files_changed=0)
        assert mr.review_priority == ReviewPriority.LOW.value

    def test_estimated_review_time(self):
        mr = MergeReadinessCalc.calculate(
            [_make_finding("medium", f"m{i}") for i in range(5)],
        )
        assert mr.estimated_review_time_min == 10


# =============================================================================
# RisksParser
# =============================================================================

class TestRisksParser:
    @pytest.fixture
    def meta(self):
        return ReviewMeta(pr_url="https://github.com/a/b/pull/1", files_analyzed=5)

    def test_from_dict_with_overall(self, meta):
        data = {
            "findings": [
                {"type": "risk", "severity": "critical", "category": "security",
                 "title": "SQL注入", "description": "未参数化", "file": "db.py",
                 "line_start": 10, "line_end": 10, "suggestion": "使用参数化查询",
                 "confidence": 0.95},
            ],
            "overall": {
                "score": 40,
                "blocking_issues": ["SQL注入"],
                "review_priority": "high",
                "estimated_review_time_min": 15,
                "summary": "严重安全问题",
            },
        }
        result = RisksParser.from_dict(data, meta)
        assert len(result.findings) == 1
        assert result.findings[0].title == "SQL注入"
        assert result.merge_readiness is not None
        assert result.merge_readiness.score == 40.0
        assert result.merge_readiness.review_priority == ReviewPriority.HIGH.value
        assert result.merge_readiness.blocking_issues == ["SQL注入"]

    def test_from_dict_missing_overall(self, meta):
        data = {
            "findings": [
                {"type": "risk", "severity": "critical", "category": "security",
                 "title": "密钥硬编码", "description": "JWT secret 写死", "file": "a.py",
                 "line_start": 1, "line_end": 1, "confidence": 0.9},
            ],
        }
        result = RisksParser.from_dict(data, meta)
        assert len(result.findings) == 1
        assert result.merge_readiness is not None
        assert result.merge_readiness.score == 70.0  # 100 - 30

    def test_from_dict_empty(self, meta):
        result = RisksParser.from_dict({}, meta)
        assert result.findings == []
        assert result.merge_readiness is not None
        assert result.merge_readiness.score == 100.0

    def test_with_summary(self, meta):
        data = {"summary": {"pr_type": "bugfix", "overview": "修复崩溃"}}
        result = RisksParser.from_dict(data, meta)
        assert result.summary.pr_type == "bugfix"

    def test_missing_summary(self, meta):
        result = RisksParser.from_dict({}, meta)
        assert result.summary.pr_type == ""

    def test_findings_mapped(self, meta):
        data = {
            "findings": [
                {"type": "risk", "severity": "high", "category": "performance",
                 "title": "N+1查询", "file": "query.py",
                 "line_start": 20, "line_end": 25, "confidence": 0.8},
            ],
        }
        result = RisksParser.from_dict(data, meta)
        assert len(result.findings) == 1
        f = result.findings[0]
        assert f.severity.value == "high"
        assert f.category == "performance"
        assert f.location.path == "query.py"

    def test_parse_raw(self, meta):
        raw = (
            '{"findings": [{"type": "risk", "severity": "low", "category": "style",'
            '"title": "命名不规范", "file": "x.py", "line_start": 1, "line_end": 1,'
            '"confidence": 0.3}], "overall": {"score": 95}}'
        )
        result = RisksParser.parse(raw, meta)
        assert len(result.findings) == 1
        assert result.merge_readiness.score == 95.0

    def test_no_files_in_data(self, meta):
        result = RisksParser.from_dict({"findings": []}, meta)
        assert result.file_walkthrough == []


# ImproveParser removed — merged into review pipeline
