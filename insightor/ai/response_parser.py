"""Response Parser — 将 AI 原始响应解析为 URF ReviewResult。

适配器模式: 支持 JSON / Markdown 包裹的 JSON 等多种格式。
"""

import json
import logging
import re
from uuid import uuid4

from insightor.schemas.urf import (
    CodeSuggestion,
    EditType,
    FileWalkthrough,
    Finding,
    FindingType,
    Location,
    MergeReadiness,
    MergeRecommendation,
    Position,
    PRSummary,
    QualityMetrics,
    Range,
    ReviewMeta,
    ReviewPriority,
    ReviewResult,
    ReviewStats,
    Severity,
)

logger = logging.getLogger(__name__)


class ResponseParser:
    """将 AI 返回的 JSON 解析为标准 ReviewResult。"""

    @staticmethod
    def parse(raw: str, meta: ReviewMeta) -> ReviewResult:
        data = _extract_json(raw)
        return ResponseParser.from_dict(data, meta)

    @staticmethod
    def from_dict(data: dict, meta: ReviewMeta) -> ReviewResult:
        """从已解析的 dict 构建 ReviewResult。"""
        # Summary
        summary_data = data.get("summary", {})
        summary = PRSummary(
            pr_type=summary_data.get("pr_type", ""),
            overview=summary_data.get("overview", ""),
            files_changed=meta.files_analyzed,
        )

        # Findings
        findings: list[Finding] = []
        for item in data.get("findings", []):
            findings.append(_parse_finding(item))

        # File walkthrough
        walkthrough: list[FileWalkthrough] = []
        for fw in data.get("files", []):
            walkthrough.append(FileWalkthrough(
                path=fw.get("path", ""),
                edit_type=_str_to_edit_type(fw.get("change", "modified")),
                summary=fw.get("change", fw.get("summary", "")),
            ))

        # Stats
        sev_counts: dict[str, int] = {}
        cat_counts: dict[str, int] = {}
        for f in findings:
            sev = f.severity.value
            cat = f.category
            sev_counts[sev] = sev_counts.get(sev, 0) + 1
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        stats = ReviewStats(
            total_findings=len(findings),
            by_severity=sev_counts,
            by_category=cat_counts,
            quality=QualityMetrics(
                confidence_distribution=_calc_confidence_distribution(findings),
            ),
        )

        # Merge readiness
        overall = data.get("overall", {})
        mr_score = float(overall.get("score", 80))
        mr = MergeReadiness(
            score=max(0, min(100, mr_score)),
            recommendation=_score_to_recommendation(mr_score),
            summary=overall.get("summary", ""),
        )

        return ReviewResult(
            meta=meta,
            summary=summary,
            file_walkthrough=walkthrough,
            findings=findings,
            stats=stats,
            merge_readiness=mr,
        )


class DescribeParser:
    """将 AI 返回的描述 JSON 解析为 ReviewResult。

    处理 describe 工具的 JSON 格式:
      { pr_type, overview, files: [{path, change}], diagram }
    """

    @staticmethod
    def parse(raw: str, meta: ReviewMeta) -> ReviewResult:
        data = _extract_json(raw)
        return DescribeParser.from_dict(data, meta)

    @staticmethod
    def from_dict(data: dict, meta: ReviewMeta) -> ReviewResult:
        pr_type = data.get("pr_type", "")
        overview = data.get("overview", "")
        diagram = data.get("diagram", "")

        summary = PRSummary(
            pr_type=pr_type,
            overview=overview,
            files_changed=meta.files_analyzed,
            diagram=diagram,
        )

        walkthrough: list[FileWalkthrough] = []
        for fw in data.get("files", []):
            walkthrough.append(FileWalkthrough(
                path=fw.get("path", ""),
                edit_type=_str_to_edit_type(fw.get("change", "modified")),
                summary=fw.get("change", ""),
            ))

        return ReviewResult(
            meta=meta,
            summary=summary,
            file_walkthrough=walkthrough,
        )


class MergeReadinessCalc:
    """独立工具: 从 findings 计算 MergeReadiness。

    当 AI 未提供 overall 评分时作为 fallback。
    """

    @staticmethod
    def calculate(
        findings: list[Finding],
        files_changed: int = 0,
    ) -> MergeReadiness:
        sev_counts: dict[str, int] = {}
        for f in findings:
            sev_counts[f.severity.value] = sev_counts.get(f.severity.value, 0) + 1

        c = sev_counts.get("critical", 0)
        h = sev_counts.get("high", 0)
        m = sev_counts.get("medium", 0)
        l = sev_counts.get("low", 0)

        score = 100.0 - (c * 30 + h * 10 + m * 3 + l * 1)
        score = max(0.0, min(100.0, score))

        blocking: list[str] = []
        for f in findings:
            if f.severity == Severity.CRITICAL:
                blocking.append(f.title)
        if h >= 3:
            for f in findings:
                if f.severity == Severity.HIGH:
                    blocking.append(f.title)

        if c > 0:
            priority = ReviewPriority.HIGH
        elif h > 0 or files_changed > 10:
            priority = ReviewPriority.MEDIUM
        else:
            priority = ReviewPriority.LOW

        parts = [f"风险分析发现 {len(findings)} 个问题"]
        if c:
            parts.append(f"其中严重 {c} 个")
        if h:
            parts.append(f"高 {h} 个")
        summary = "，".join(parts)

        return MergeReadiness(
            score=score,
            recommendation=_score_to_recommendation(score),
            blocking_issues=blocking,
            review_priority=priority.value,
            estimated_review_time_min=len(findings) * 2,
            summary=summary,
        )


class RisksParser:
    """将 AI 风险分析 JSON 解析为 ReviewResult。

    处理 risks 工具的 JSON 格式:
      { findings: [...], overall: { score, blocking_issues, ... } }
    overall 缺失时自动通过 MergeReadinessCalc 计算。
    """

    @staticmethod
    def parse(raw: str, meta: ReviewMeta) -> ReviewResult:
        data = _extract_json(raw)
        return RisksParser.from_dict(data, meta)

    @staticmethod
    def from_dict(data: dict, meta: ReviewMeta) -> ReviewResult:
        findings: list[Finding] = []
        for item in data.get("findings", []):
            findings.append(_parse_finding(item))

        overall = data.get("overall")
        if overall and "score" in overall:
            mr_score = float(overall["score"])
            mr = MergeReadiness(
                score=max(0.0, min(100.0, mr_score)),
                recommendation=_score_to_recommendation(mr_score),
                blocking_issues=overall.get("blocking_issues", []),
                review_priority=_parse_priority(overall.get("review_priority", "medium")),
                estimated_review_time_min=int(overall.get("estimated_review_time_min", len(findings) * 2)),
                summary=overall.get("summary", ""),
            )
        else:
            mr = MergeReadinessCalc.calculate(findings, files_changed=meta.files_analyzed)

        summary_data = data.get("summary", {})
        summary = PRSummary(
            pr_type=summary_data.get("pr_type", ""),
            overview=summary_data.get("overview", ""),
            files_changed=meta.files_analyzed,
        )

        walkthrough: list[FileWalkthrough] = []
        for fw in data.get("files", []):
            walkthrough.append(FileWalkthrough(
                path=fw.get("path", ""),
                edit_type=_str_to_edit_type(fw.get("change", "modified")),
                summary=fw.get("change", fw.get("summary", "")),
            ))

        sev_counts: dict[str, int] = {}
        cat_counts: dict[str, int] = {}
        for f in findings:
            sv = f.severity.value
            cat = f.category
            sev_counts[sv] = sev_counts.get(sv, 0) + 1
            cat_counts[cat] = cat_counts.get(cat, 0) + 1

        stats = ReviewStats(
            total_findings=len(findings),
            by_severity=sev_counts,
            by_category=cat_counts,
            quality=QualityMetrics(
                confidence_distribution=_calc_confidence_distribution(findings),
            ),
        )

        return ReviewResult(
            meta=meta,
            summary=summary,
            file_walkthrough=walkthrough,
            findings=findings,
            stats=stats,
            merge_readiness=mr,
        )


class ImproveParser:
    """将 AI 代码建议 JSON 解析为 ReviewResult。

    处理 improve 工具的 JSON 格式:
      { summary, suggestions: [{..., current_code, suggested_code, is_committable}], files, overall }
    """

    @staticmethod
    def parse(raw: str, meta: ReviewMeta) -> ReviewResult:
        data = _extract_json(raw)
        return ImproveParser.from_dict(data, meta)

    @staticmethod
    def from_dict(data: dict, meta: ReviewMeta) -> ReviewResult:
        # 兼容 suggestions / findings 两种 key
        items = data.get("suggestions") or data.get("findings") or []

        findings: list[Finding] = []
        for item in items:
            sev = item.get("severity", "medium")
            try:
                severity = Severity(sev)
            except ValueError:
                severity = Severity.MEDIUM

            cat = item.get("category", "maintainability").lower()
            valid_cats = {"performance", "maintainability", "style", "logic", "reliability", "security",
                          "concurrency", "data_loss"}
            if cat not in valid_cats:
                cat = "maintainability"

            file = item.get("file", "")
            line_start = int(item.get("line_start", 1))
            line_end = int(item.get("line_end", line_start))

            current_code = item.get("current_code", "")
            suggested_code = item.get("suggested_code", "")
            is_committable = bool(item.get("is_committable", False) or item.get("committable", False))

            has_suggestion = bool(current_code or suggested_code)
            suggestion = None
            if has_suggestion:
                suggestion = CodeSuggestion(
                    current_code=current_code,
                    suggested_code=suggested_code,
                    is_committable=is_committable,
                )
            elif item.get("suggestion"):
                suggestion = CodeSuggestion(
                    current_code="",
                    suggested_code=str(item["suggestion"]),
                    is_committable=False,
                )

            findings.append(Finding(
                id=uuid4(),
                type=FindingType.SUGGESTION,
                severity=severity,
                category=cat,
                title=item.get("title", ""),
                description=item.get("description", ""),
                location=Location(
                    path=file,
                    range=Range(start=Position(line=line_start), end=Position(line=line_end)),
                ),
                suggestion=suggestion,
                confidence=float(item.get("confidence", 0.5)),
            ))

        # Summary
        summary_data = data.get("summary", {})
        summary = PRSummary(
            pr_type=summary_data.get("pr_type", ""),
            overview=summary_data.get("overview", ""),
            files_changed=meta.files_analyzed,
        )

        # File walkthrough
        walkthrough: list[FileWalkthrough] = []
        for fw in data.get("files", []):
            walkthrough.append(FileWalkthrough(
                path=fw.get("path", ""),
                edit_type=_str_to_edit_type(fw.get("change", "modified")),
                summary=fw.get("change", fw.get("summary", "")),
            ))

        # Stats
        sev_counts: dict[str, int] = {}
        cat_counts: dict[str, int] = {}
        for f in findings:
            sv = f.severity.value
            ct = f.category
            sev_counts[sv] = sev_counts.get(sv, 0) + 1
            cat_counts[ct] = cat_counts.get(ct, 0) + 1

        stats = ReviewStats(
            total_findings=len(findings),
            by_severity=sev_counts,
            by_category=cat_counts,
            quality=QualityMetrics(
                confidence_distribution=_calc_confidence_distribution(findings),
            ),
        )

        # Merge readiness
        overall = data.get("overall")
        if overall and "score" in overall:
            mr_score = float(overall["score"])
            mr = MergeReadiness(
                score=max(0.0, min(100.0, mr_score)),
                recommendation=_score_to_recommendation(mr_score),
                blocking_issues=overall.get("blocking_issues", []),
                review_priority=_parse_priority(overall.get("review_priority", "medium")),
                estimated_review_time_min=int(overall.get("estimated_review_time_min", len(findings) * 2)),
                summary=overall.get("summary", ""),
            )
        else:
            mr = MergeReadinessCalc.calculate(findings, files_changed=meta.files_analyzed)

        return ReviewResult(
            meta=meta,
            summary=summary,
            file_walkthrough=walkthrough,
            findings=findings,
            stats=stats,
            merge_readiness=mr,
        )


# =============================================================================
# 内部辅助
# =============================================================================

def _extract_json(raw: str) -> dict:
    """从 LLM 原始响应中提取 JSON。"""
    raw = raw.strip()

    # 1. 尝试直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 2. 提取 ```json ... ``` 包裹的内容
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 从第一个 { 到最后一个 } 提取
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning("无法从响应中提取 JSON, 返回空结果")
    return {}


def _parse_finding(item: dict) -> Finding:
    sev = item.get("severity", "medium")
    try:
        severity = Severity(sev)
    except ValueError:
        severity = Severity.MEDIUM

    cat = item.get("category", "logic").lower()
    valid_cats = {"security", "performance", "logic", "concurrency", "data_loss", "style"}
    if cat not in valid_cats:
        cat = "logic"

    file = item.get("file", "")
    line_start = int(item.get("line_start", 1))
    line_end = int(item.get("line_end", line_start))

    suggestion_text = item.get("suggestion", "")
    has_suggestion = bool(suggestion_text)
    suggestion = None
    if has_suggestion:
        suggestion = CodeSuggestion(
            current_code="",
            suggested_code=suggestion_text,
            is_committable=False,
        )

    return Finding(
        id=uuid4(),
        type=FindingType(item.get("type", "observation")),
        severity=severity,
        category=cat,
        title=item.get("title", ""),
        description=item.get("description", ""),
        location=Location(
            path=file,
            range=Range(start=Position(line=line_start), end=Position(line=line_end)),
        ),
        suggestion=suggestion,
        confidence=float(item.get("confidence", 0.5)),
    )


def _calc_confidence_distribution(findings: list[Finding]) -> dict[str, float]:
    if not findings:
        return {}
    confs = [f.confidence for f in findings]
    return {
        "avg": round(sum(confs) / len(confs), 3),
        "min": round(min(confs), 3),
        "max": round(max(confs), 3),
    }


def _str_to_edit_type(s: str) -> EditType:
    s = s.lower()
    if "add" in s: return EditType.ADDED
    if "delet" in s or "remov" in s: return EditType.DELETED
    if "renam" in s: return EditType.RENAMED
    return EditType.MODIFIED


def _parse_priority(priority: str) -> ReviewPriority:
    try:
        return ReviewPriority(priority.lower())
    except ValueError:
        return ReviewPriority.MEDIUM


def _score_to_recommendation(score: float) -> MergeRecommendation:
    if score >= 80: return MergeRecommendation.SAFE_TO_MERGE
    if score >= 50: return MergeRecommendation.NEEDS_REVIEW
    if score >= 20: return MergeRecommendation.NEEDS_WORK
    return MergeRecommendation.BLOCKED
