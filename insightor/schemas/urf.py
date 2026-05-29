"""Universal Review Format (URF) — 所有 AI 分析结果统一输出到该 Schema。

源自 Reviewdog 的 RDF (Reviewdog Diagnostic Format) 模式：定义显式中间数据模型
是所有可扩展性的基础。
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# =============================================================================
# 基础类型
# =============================================================================

class AnalysisDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class FindingType(str, Enum):
    RISK = "risk"
    SUGGESTION = "suggestion"
    OBSERVATION = "observation"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EditType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class FeedbackStatus(str, Enum):
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    ADDRESSED = "addressed"
    IGNORED = "ignored"


class MergeRecommendation(str, Enum):
    SAFE_TO_MERGE = "safe_to_merge"
    NEEDS_REVIEW = "needs_review"
    NEEDS_WORK = "needs_work"
    BLOCKED = "blocked"


class ReviewPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =============================================================================
# 位置信息
# =============================================================================

class Position(BaseModel):
    line: int = Field(ge=1, description="行号 (1-based)")
    column: int = Field(default=1, ge=1, description="列号 (1-based)")


class Range(BaseModel):
    start: Position
    end: Position


class Location(BaseModel):
    path: str = Field(description="文件相对路径")
    range: Range = Field(description="代码范围")


# =============================================================================
# 代码建议
# =============================================================================

class CodeSuggestion(BaseModel):
    current_code: str = Field(default="", description="当前代码")
    suggested_code: str = Field(default="", description="建议修改后的代码")
    is_committable: bool = Field(default=False, description="是否可直接应用")


# =============================================================================
# 反馈闭环 (V3 新增)
# =============================================================================

class FindingFeedback(BaseModel):
    status: FeedbackStatus | None = None
    reviewer_note: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


# =============================================================================
# Finding (核心发现)
# =============================================================================

class Finding(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: FindingType
    severity: Severity
    category: str = Field(description="security | performance | logic | concurrency | data_loss | style | ...")
    title: str = Field(description="一句话标题")
    description: str = Field(description="详细描述")
    location: Location
    suggestion: CodeSuggestion | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="置信度")
    fingerprint: str = Field(default="", description="SHA256 去重指纹")
    feedback: FindingFeedback | None = None  # V3: 开发者反馈


# =============================================================================
# PR 总结
# =============================================================================

class PRSummary(BaseModel):
    pr_type: str = Field(default="", description="feature | bugfix | refactor | docs | ci")
    overview: str = Field(default="", description="一句话概述")
    files_changed: int = 0
    additions: int = 0
    deletions: int = 0
    diagram: str = Field(default="", description="Mermaid 流程图代码，无则为空字符串")


class FileWalkthrough(BaseModel):
    path: str
    edit_type: EditType
    summary: str = ""
    risk_count: int = 0
    suggestion_count: int = 0


# =============================================================================
# 统计信息 (V3 增强)
# =============================================================================

class IncrementalStats(BaseModel):
    new: int = 0
    resolved: int = 0
    reconfirmed: int = 0
    obsolete: int = 0


class QualityMetrics(BaseModel):
    confidence_distribution: dict[str, float] = Field(default_factory=dict)
    self_reflection_avg_score: float | None = None
    historical_precision: dict[str, float] = Field(default_factory=dict)
    test_files_in_diff: int = 0


class ReviewStats(BaseModel):
    total_findings: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    incremental: IncrementalStats | None = None
    quality: QualityMetrics | None = None


# =============================================================================
# 合并就绪评估 (V3 新增)
# =============================================================================

class MergeReadiness(BaseModel):
    score: float = Field(default=100.0, ge=0.0, le=100.0, description="综合评分 0-100")
    recommendation: MergeRecommendation = MergeRecommendation.NEEDS_REVIEW
    blocking_issues: list[str] = Field(default_factory=list, description="阻断性问题")
    review_priority: ReviewPriority = ReviewPriority.MEDIUM
    estimated_review_time_min: int = Field(default=0, description="人工审查预估时间(分钟)")
    summary: str = ""


# =============================================================================
# 上下文摘要 (V3 新增)
# =============================================================================

class ContextSummary(BaseModel):
    layers_used: list[str] = Field(default_factory=list)
    related_files_analyzed: list[str] = Field(default_factory=list)
    issues_referenced: list[str] = Field(default_factory=list)
    tokens_by_layer: dict[str, int] = Field(default_factory=dict)


# =============================================================================
# 元信息 (V3 增强)
# =============================================================================

class ReviewMeta(BaseModel):
    pr_url: str
    commit_sha: str = ""
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    model: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: int = 0
    tokens_used: int = 0
    files_analyzed: int = 0
    files_skipped: int = 0
    # V3 增量审查
    is_incremental: bool = False
    base_review_id: str | None = None
    new_findings_count: int = 0
    resolved_findings_count: int = 0
    reconfirmed_findings_count: int = 0
    # V3 上下文层
    context_layers: list[str] = Field(default_factory=list)


# =============================================================================
# 顶层 ReviewResult
# =============================================================================

class ReviewResult(BaseModel):
    """Universal Review Format — 所有 Insightor 工具的统一输出格式。"""
    meta: ReviewMeta
    summary: PRSummary = Field(default_factory=PRSummary)
    file_walkthrough: list[FileWalkthrough] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    stats: ReviewStats = Field(default_factory=ReviewStats)
    merge_readiness: MergeReadiness | None = None
    context_summary: ContextSummary | None = None
