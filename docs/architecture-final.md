# Insightor 最终架构设计与 PR 拆分计划

> 融合 PR-Agent (AI Review 核心) + Reviewdog (可扩展架构) + Aider (上下文排序算法) + 分层上下文管线 + 质量闭环，为 Insightor 设计的最终架构。

---

## 一、最终架构全景图

```
用户输入 (PR URL + 命令 + 选项)
    │
    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Layer 0: 环境感知层 (Environment)                                        │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ · BuildInfo: 自动检测 CI 环境                                      │   │
│  │ · ConfigLoader: default → .insightor.yml → env → CLI (四级覆盖)    │   │
│  │ · AnalysisDepth: quick | standard | deep                          │   │
│  │ · IncrementalDetector: (由 CacheManager.get_base_for_incremental 实现) │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│  Layer 1: 入口层 (Entry)                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ · CLI (click): insightor full/review/describe/risks/publish            │   │
│  │ · Web (FastAPI): SSE 流式分析 + Tab 结果展示                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│  Layer 2: 数据获取层 (Provider)                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ GitProvider (Protocol)                                             │   │
│  │  ├── GitHubProvider · get_pr_info / get_files / get_commits        │   │
│  │  ├── GitLabProvider  (未来)                                       │   │
│  │  └── LocalGitProvider (未来)                                       │   │
│  │                                                                    │   │
│  │ ★ ContextProvider (Protocol) — 分层上下文获取                       │   │
│  │  ├── DiffContextSource      · PR diff + commits (Layer 1)          │   │
│  │  ├── FileContextSource      · 文件上下文扩展 (Layer 2)              │   │
│  │  ├── IssueContextSource     · GitHub Issues API (Layer 3)          │   │
│  │  ├── RelatedFileSource      · 关联文件发现 (Layer 4)               │   │
│  │  └── RepoAnalysisSource     · 全仓库 AST 分析 (Layer 5)           │   │
│  │                                                                    │   │
│  │ DiffService (Protocol)                                             │   │
│  │  ├── GitHubDiffService · PR diff API                              │   │
│  │  └── LocalDiffService  · git diff 命令                            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│  Layer 3: 数据处理层 (Processing)                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ FileFilter       · 忽略规则 (glob/regex/生成代码)                   │   │
│  │ LanguageDetector · 语言识别 + 主语言优先排序                         │   │
│  │ TokenEstimator   · tiktoken 精确 + 估算系数                        │   │
│  │ DiffCompressor   · 渐进压缩 (Level 0→3)                            │   │
│  │                                                                    │   │
│  │ ★ Context Pipeline (Aider 启发) —— 5层上下文智能组装                │   │
│  │  ├── SymbolExtractor · tree-sitter 符号提取 (def/ref)              │   │
│  │  ├── TagCache · diskcache + mtime 增量解析                         │   │
│  │  ├── DependencyGraph · nx.MultiDiGraph 文件级符号依赖               │   │
│  │  ├── RelevanceRanker · 个性化 PageRank (50x/10x/0.1x 加权)        │   │
│  │  ├── BudgetFitter · 二分搜索 Token 最优选择                        │   │
│  │  └── CompactCodeRenderer · Tree View 骨架渲染                      │   │
│  │                                                                    │   │
│  │ IncrementalDiffer· 增量 diff + 结果合并策略                         │   │
│  │ CacheManager     · (PR_URL + SHA) 结果缓存 + Tag 缓存              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│  Layer 4: AI 分析层 (AI Engine)                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ AIHandler (Protocol)                                               │   │
│  │  └── LiteLLMHandler · 多模型统一 + fallback 链 + 流式调用           │   │
│  │                                                                    │   │
│  │ PromptBuilder · Jinja2 模板 + custom_rules + conventions 注入       │   │
│  │                                                                    │   │
│  │ ResponseParser (适配器): JSONParser / YAMLParser → URF             │   │
│  │ StreamParser (★新): 增量解析流式 AI 输出 → 逐条 yield Finding       │   │
│  │                                                                    │   │
│  │ SelfReflector · deep 模式二次评分 (风险 + 建议均校验)               │   │
│  │                                                                    │   │
│  │ MergeReadinessCalc (★新) · 综合评分 + 阻断项 + 审查优先级           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│  Layer 5: 输出层 (Output) 组合模式 + 反馈闭环                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ CompositeOutputService                                             │   │
│  │  ├── ConsoleOutput          · Rich 美化 + 流式实时更新              │   │
│  │  ├── MarkdownFileOutput     · insightor-review-{pr}.md             │   │
│  │  ├── GitHubCommentOutput    · PR 评论 + 行内评论 + reaction 回读   │   │
│  │  └── JSONOutput             · API 响应 + 缓存持久化                │   │
│  │                                                                    │   │
│  │ FingerprintGenerator  · SHA256 指纹 (去重 + 过时清理)              │   │
│  │ FeedbackCollector (★新) · 收集开发者反馈 → 更新 QualityMetrics      │   │
│  │ QualityTracker (★新)    · 跟踪历史准确率 + 置信度校准               │   │
│  │ GracefulDegradation     · API 失败 → 终端降级                      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 二、Universal Review Format (URF v3)

```json
{
  "$schema": "https://insightor.dev/urf-v1.json",
  "meta": {
    "pr_url": "https://github.com/owner/repo/pull/123",
    "commit_sha": "abc123def456",
    "analysis_depth": "deep",
    "model": "claude-sonnet-4-6",
    "timestamp": "2026-05-29T10:00:00Z",
    "duration_ms": 45000,
    "tokens_used": 12000,

    "is_incremental": true,
    "base_review_id": "uuid-of-previous-review",
    "new_findings_count": 3,
    "resolved_findings_count": 2,
    "reconfirmed_findings_count": 7,

    "context_layers": ["diff", "file_context", "issues", "related_files"]
  },
  "summary": {
    "pr_type": "feature",
    "overview": "添加了用户认证模块，支持 JWT 登录与刷新"
  },
  "file_walkthrough": [{
    "path": "src/auth/login.py",
    "edit_type": "modified",
    "summary": "重构登录逻辑，添加 JWT token 生成",
    "risk_count": 1,
    "suggestion_count": 2
  }],
  "findings": [{
    "id": "uuid-v4",
    "type": "risk",
    "severity": "high",
    "category": "security",
    "title": "JWT secret 硬编码在代码中",
    "description": "...",
    "location": {
      "path": "src/auth/login.py",
      "range": { "start": { "line": 23 }, "end": { "line": 23 } }
    },
    "suggestion": {
      "current_code": "SECRET_KEY = \"hardcoded-secret-12345\"",
      "suggested_code": "SECRET_KEY = os.environ.get(\"JWT_SECRET\")"
    },
    "confidence": 0.92,
    "fingerprint": "sha256:abc123",
    "feedback": {
      "status": "confirmed",
      "reviewer_note": "确实需要修复，已改为环境变量",
      "reviewed_by": "dev-username",
      "reviewed_at": "2026-05-29T12:00:00Z"
    }
  }],
  "stats": {
    "total_findings": 10,
    "by_severity": { "critical": 0, "high": 2, "medium": 5, "low": 3 },
    "by_category": { "security": 2, "performance": 1, "logic": 2, "style": 5 },
    "incremental": {
      "new": 3, "resolved": 2, "reconfirmed": 7, "obsolete": 0
    },
    "quality": {
      "confidence_distribution": { "high": 0.6, "medium": 0.3, "low": 0.1 },
      "self_reflection_avg_score": 7.8,
      "historical_precision": { "security": 0.88, "performance": 0.75, "logic": 0.62 },
      "test_files_in_diff": 2
    }
  },
  "merge_readiness": {
    "score": 68,
    "recommendation": "needs_review",
    "blocking_issues": ["JWT secret 硬编码"],
    "review_priority": "medium",
    "estimated_review_time_min": 15,
    "summary": "有 1 个高优先级安全问题需要修复，其余改动风险可控"
  },
  "context_summary": {
    "layers_used": ["diff", "file_context", "issues"],
    "related_files_analyzed": ["src/auth/middleware.py", "src/api/handlers.py"],
    "issues_referenced": ["#42 - 实现 JWT 认证"],
    "tokens_by_layer": { "diff": 6000, "issues": 800, "related_files": 1200 }
  }
}
```

---

## 三、分层上下文管线（核心设计）

来自 PR-Agent（Token 管理）、Reviewdog（过滤定位）、Aider（仓库地图）、Sourcegraph（代码智能）的融合设计：

```
┌──────────────────────────────────────────────────────────────────┐
│                    Context Pipeline (分层上下文管线)                 │
│                                                                   │
│  Layer 1 (必选): PR Diff + Description + Commits                  │
│    · 成本: 0 额外 API 调用                                         │
│    · Token: ~2K-20K                                               │
│    · 内容: unified diff + PR body + commit messages               │
│                                                                   │
│  Layer 2 (必选): 文件级上下文扩展                                    │
│    · 成本: 0 额外 API 调用                                         │
│    · Token: ~1K-5K                                                │
│    · 内容: 每个 hunk ±N 行上下文 + import 语句解析                  │
│                                                                   │
│  Layer 3 (standard+): Issue/Ticket 关联                            │
│    · 成本: 1 API 调用                                              │
│    · Token: ~500-2K                                               │
│    · 内容: 从 PR 描述提取 issue 引用 → GitHub Issues API 拉取       │
│                                                                   │
│  Layer 4 (standard+): 关联文件发现                                  │
│    · 成本: 2-3 API 调用 / git 操作                                  │
│    · Token: ~1K-3K                                                │
│    · 内容: 识别被修改符号的 callers/callees → 拉取关键片段           │
│                                                                   │
│  Layer 5 (deep): 仓库结构分析 + AST                                │
│    · 成本: git clone + tree-sitter parse                          │
│    · Token: ~2K-5K                                                │
│    · 内容: 仓库地图 + 影响范围 + 项目约定                           │
│                                                                   │
│  由 AnalysisDepth 控制启用层:                                       │
│  ┌─────────┬──────────┬──────────┬──────────┐                    │
│  │         │  quick   │ standard │   deep   │                    │
│  ├─────────┼──────────┼──────────┼──────────┤                    │
│  │ Layer 1 │    ✅    │    ✅    │    ✅    │                    │
│  │ Layer 2 │    ✅    │    ✅    │    ✅    │                    │
│  │ Layer 3 │          │    ✅    │    ✅    │                    │
│  │ Layer 4 │          │    ✅    │    ✅    │                    │
│  │ Layer 5 │          │          │    ✅    │                    │
│  └─────────┴──────────┴──────────┴──────────┘                    │
└──────────────────────────────────────────────────────────────────┘
```

### ContextProvider 接口设计

```python
class ContextSource(Protocol):
    """单个上下文来源"""
    name: str                    # "diff", "issues", "related_files", ...
    layer: int                   # 1-5
    async def fetch(self, pr_info: PRInfo, files: list[FilePatchInfo]) -> ContextChunk: ...
    def estimate_tokens(self, chunk: ContextChunk) -> int: ...

@dataclass
class ContextChunk:
    source_name: str
    content: str                # 可注入 Prompt 的文本
    metadata: dict              # {tokens, related_files, issues, ...}

class ContextPipeline:
    """管理分层上下文的获取、预算分配和组装"""
    def __init__(self, sources: list[ContextSource], token_budget: int)
    async def gather(
        self, pr_info: PRInfo, files: list[FilePatchInfo], depth: AnalysisDepth
    ) -> AssembledContext: ...
    def allocate_budget(self, depth: AnalysisDepth) -> dict[str, int]: ...

@dataclass
class AssembledContext:
    chunks: list[ContextChunk]
    total_tokens: int
    remaining_budget: int      # 剩余 token 预算给 diff
    summary: ContextSummary     # 用于 URF 的 context_summary 字段
```

### 关联文件发现策略（Layer 4 核心）

```python
class RelatedFileSource(ContextSource):
    """
    发现与变更代码相关的文件。

    策略：
    1. 从 diff 中提取被修改的符号（函数名/类名/导出的变量）
    2. 通过 GitHub Search API 或 git grep 查找引用这些符号的文件
    3. 通过 .insightor.yml 的 dependency_map 补充项目级关联
    4. 对关联文件仅提取函数签名等骨架信息（节省 token）
    """
    async def fetch(self, pr_info, files) -> ContextChunk:
        modified_symbols = self._extract_symbols(files)
        callers = await self._find_callers(pr_info, modified_symbols)
        dependency_map = self._load_dependency_map()
        manual_related = self._apply_dependency_map(files, dependency_map)
        return self._assemble_chunk(callers, manual_related)
```

### .insightor.yml 上下文相关配置

```yaml
# .insightor.yml - 完整版
context:
  # Issue 关联
  issue_trackers:
    - pattern: "#(\\d+)"                    # GitHub issue
      url_template: "https://github.com/{owner}/{repo}/issues/{id}"
    - pattern: "(PROJ-\\d+)"               # Jira
      enabled: false

  # 依赖映射
  dependency_map:
    "src/models/":    ["src/services/", "src/api/", "tests/"]
    "src/middleware/": ["src/api/", "tests/"]
    "migrations/":    ["src/models/", "tests/"]

  # 上下文层控制
  max_related_files: 5        # Layer 4 最多拉取 N 个关联文件
  related_file_context_lines: 30  # 每个关联文件只取前 N 行
  
  # 忽略的上下文源
  disabled_layers: []          # 强制禁用某些层

review:
  # 自定义规则
  custom_rules: |
    1. 所有 /api/ 路由处理器必须有 @require_auth 装饰器
    2. 数据库查询必须使用参数化查询，禁止字符串拼接 SQL
    3. 金额计算必须使用 Decimal 而非 float

  # 团队约定
  conventions: |
    - 使用 async/await 而非回调
    - 错误消息使用中文
    - 日志使用 structlog 而非 print

  # 已知安全模式（减少误报）
  safe_patterns:
    - "logger\\.debug\\(.*password.*\\)"
    - "eval\\(json_data\\)"           # 已在上层验证 JSON 安全性

  # 关注领域
  focus_categories: ["security", "performance"]
  min_severity: medium
  max_suggestions: 15
```

---

## 四、增量审查与反馈闭环

### 增量审查流程

```
首次审查 PR (commit abc):
  → 全量分析 → 保存 ReviewResult

下次 push (commit def):
  → IncrementalDiffer.compare(abc, def)
  → 仅分析变更文件
  → 加载旧 result → 合并:
      ┌──────────────────────────────────────┐
      │ 新 Finding           → 追加          │
      │ 旧 Finding 在新 diff  → 重新评估      │
      │ 旧 Finding 未变更范围 → 保留+reconfirmed│
      │ 旧 Finding 代码删除   → 标记 resolved  │
      └──────────────────────────────────────┘
  → 输出增量统计: "新增 2 风险，修复 3 问题，5 待处理"
```

### 反馈闭环

```
AI 输出 Findings
    │
    ▼
开发者查看 → 标记 confirmed / false_positive / addressed / ignored
    │
    ▼
FeedbackCollector 收集反馈
    │
    ├──→ 更新 ReviewResult (finding.feedback 字段)
    ├──→ 更新 QualityMetrics (每 category 的准确率)
    └──→ 反馈积累 → Prompt 优化 → safe_patterns 更新
```

---

## 五、技术栈

| 层面 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | LLM/GitHub 生态最丰富 |
| GitHub API | `PyGithub` | 成熟的 Python SDK |
| LLM 调用 | `litellm` + `anthropic` SDK + raw HTTP | 双路径：Anthropic 原生直连（绕过网关 CLI 限制）+ LiteLLM 统一兜底 |
| Prompt 存储 | `.toml` 文件 | 可读、与 PR-Agent 兼容 |
| Prompt 渲染 | `Jinja2` | Python 标准模板引擎 |
| 配置系统 | `tomllib` + `.env` | 四级覆盖 |
| CLI 框架 | `click` | 丰富命令行体验 |
| 终端展示 | `rich` | 语法高亮、进度条、实时更新 |
| Web 框架 | `FastAPI` + SSE | 异步、流式输出 |
| Token 计算 | `tiktoken` | GPT 系列精确计算 |
| 代码解析 | `tree-sitter` (未来) | AST 级上下文提取 (Layer 5) |
| 测试 | `pytest` + `pytest-asyncio` | 标准测试栈 |

---

## 六、PR 拆分计划（共 18 个 PR，5 天）

---

### Day 1 — 基础数据层 + 核心模型

---

#### PR #1：项目工程搭建 + 配置系统 + URF Schema v3

**标题**：搭建项目骨架、四级配置系统与 Universal Review Format v3

**功能描述**：
初始化 Python 项目，建立 6 层目录结构。实现「默认 TOML → `.insightor.yml` 项目文件 → 环境变量 → CLI 参数」四级配置覆盖。定义 URF v3 Schema（含 Finding.feedback、MergeReadiness、QualityMetrics、ContextSummary）。

**关键新增（vs V2）**：
- `.insightor.yml` 支持 `custom_rules`、`conventions`、`safe_patterns`、`dependency_map`
- URF 新增：`MergeReadiness`、`QualityMetrics`、`FindingFeedback`、`IncrementalStats`、`ContextSummary`
- 新增 `context/default.toml` 上下文管线默认配置

**涉及接口**：

```python
# ===== 配置层 =====
class ConfigLoader:
    def __init__(self, config_path: str = None)
    def get(self, key_path: str, default: Any = None) -> Any
    def get_section(self, section: str) -> dict[str, Any]
    def load_project_config(self, repo_root: str) -> dict | None
    def apply_cli_args(self, **kwargs: Any) -> None
    def get_rules(self) -> list[str]           # custom_rules
    def get_conventions(self) -> list[str]     # coding conventions
    def get_safe_patterns(self) -> list[str]
    def get_dependency_map(self) -> dict[str, list[str]]
    def get_focus_categories(self) -> list[str]

# ===== URF Schema (Pydantic v3) =====
class ReviewMeta(BaseModel):
    pr_url: str; commit_sha: str; analysis_depth: str; model: str
    timestamp: datetime; duration_ms: int; tokens_used: int
    # ★ v3 新增
    is_incremental: bool = False
    base_review_id: str | None = None
    new_findings_count: int = 0
    resolved_findings_count: int = 0
    reconfirmed_findings_count: int = 0
    context_layers: list[str] = []

class FindingFeedback(BaseModel):  # ★ v3 新增
    status: Literal["confirmed","false_positive","addressed","ignored"] | None
    reviewer_note: str | None; reviewed_by: str | None
    reviewed_at: datetime | None

class Finding(BaseModel):
    id: UUID; type: str; severity: str; category: str
    title: str; description: str; location: Location
    suggestion: CodeSuggestion | None; confidence: float; fingerprint: str
    feedback: FindingFeedback | None = None  # ★ v3 新增

class IncrementalStats(BaseModel):  # ★ v3 新增
    new: int = 0; resolved: int = 0; reconfirmed: int = 0; obsolete: int = 0

class QualityMetrics(BaseModel):  # ★ v3 新增
    confidence_distribution: dict[str, float] = {}
    self_reflection_avg_score: float | None = None
    historical_precision: dict[str, float] = {}  # per-category
    test_files_in_diff: int = 0

class MergeReadiness(BaseModel):  # ★ v3 新增
    score: float  # 0-100
    recommendation: str  # safe_to_merge | needs_review | needs_work | blocked
    blocking_issues: list[str] = []
    review_priority: str = "medium"
    estimated_review_time_min: int = 0
    summary: str = ""

class ContextSummary(BaseModel):  # ★ v3 新增
    layers_used: list[str] = []
    related_files_analyzed: list[str] = []
    issues_referenced: list[str] = []
    tokens_by_layer: dict[str, int] = {}

class ReviewResult(BaseModel):
    meta: ReviewMeta; summary: PRSummary
    file_walkthrough: list[FileWalkthrough]; findings: list[Finding]
    stats: ReviewStats
    merge_readiness: MergeReadiness | None = None       # ★ v3 新增
    context_summary: ContextSummary | None = None        # ★ v3 新增

# ===== 目录结构 =====
insightor/
├── schemas/urf.py         # URF dataclasses
├── config/
│   ├── loader.py
│   ├── default.toml        # 全局默认
│   └── context.toml        # 上下文管线默认
├── environment/
│   └── buildinfo.py        # CI 环境检测 + 增量检测
├── providers/              # Layer 2
├── processing/             # Layer 3 (含 ContextPipeline)
├── ai/                     # Layer 4
├── output/                 # Layer 5 (含 Feedback/Quality)
└── tools/                  # review/describe/risks
```

**目录结构**：
```
insightor/
├── __init__.py
├── schemas/
│   ├── __init__.py
│   ├── urf.py              # ★ 含所有 v3 类
│   └── urf-v1.json         # JSON Schema
├── config/
│   ├── __init__.py
│   ├── loader.py           # ConfigLoader
│   ├── default.toml        # 全局默认配置
│   └── context.toml        # 上下文管线配置
├── environment/
│   ├── __init__.py
│   └── buildinfo.py        # CI 环境检测 + 增量检测
├── providers/              # Layer 2
├── processing/             # Layer 3
├── ai/                     # Layer 4
├── output/                 # Layer 5
└── tools/                  # review/describe/risks
```

**测试方式**：
- URF Schema JSON 校验
- 四级配置覆盖优先级
- .insightor.yml 解析（含 rules/conventions/safe_patterns/dependency_map）

---

#### PR #2：GitHub Provider — PR 数据获取

*(与 V2 基本一致，无重大变更)*

**标题**：实现 GitHub API 客户端，支持获取 PR 元数据与 Diff 文件

**涉及接口**：

```python
class GitProvider(Protocol):
    def get_pr_info(self, pr_url: str) -> PRInfo: ...
    def get_files(self, pr_url: str) -> list[FilePatchInfo]: ...
    def get_commits(self, pr_url: str) -> list[CommitInfo]: ...
    def get_repo_settings(self, pr_url: str) -> str | None: ...
    def get_issue_context(self, pr_url: str, issue_refs: list[str]) -> list[IssueInfo]: ...  # ★ Layer 3 用

class DiffService(Protocol):
    def get_diff(self, ctx) -> bytes: ...
    def get_strip(self) -> int: ...

@dataclass
class IssueInfo:  # ★ v3 新增
    number: int; title: str; body: str; labels: list[str]
```

---

#### PR #3：Diff 处理管线（已实现部分）

**标题**：实现 PR Diff 多阶段处理管线——文件过滤、语言检测、Token 估算与渐进压缩

**功能描述**：
对获取的 diff 数据进行多阶段处理：智能过滤无关文件（锁文件/图片/生成代码）、自动语言检测与优先级排序、精确 Token 估算、渐进压缩适配 Token 预算。

> **注意**：原计划中「分层上下文管线 (Context Pipeline)」部分（tree-sitter 符号提取、依赖图、PageRank 排序等）未在本 PR 实现，已拆分为独立 PR #13-16。

**涉及接口**：

```python
# ===== 文件处理 =====
class FileFilter:
    """智能文件过滤——忽略锁文件/图片/生成代码/二进制"""
    def filter(self, files: list[FilePatchInfo]) -> list[FilePatchInfo]: ...
    def is_ignored(self, filename: str) -> bool: ...
    # 支持 glob 和 regex 自定义规则

class LanguageDetector:
    """自动语言检测与主语言优先排序"""
    def detect(self, filename: str) -> str: ...
    def group_by_language(self, files) -> dict[str, list]: ...
    def sort_by_priority(self, files, main_language="") -> list: ...
    # 支持 Python/JS/TS/Go/Java/Rust 等

class TokenEstimator:
    """Token 估算——优先使用 tiktoken，fallback 到系数估算"""
    def count(self, text: str, model: str = "gpt-4o") -> int: ...
    def estimate_quick(self, text: str) -> int: ...
    # DeepSeek 等非 OpenAI 模型使用系数估算 (×1.5)

class DiffCompressor:
    """渐进压缩——Level 0→3 逐步减少 token"""
    def __init__(self, max_tokens: int = 8000, patch_extra_lines: int = 3): ...
    def compress(self, files, depth) -> CompressResult: ...
    # Level 0: 完整 diff → Level 1: 删减 hunk → Level 2: 截断文件 → Level 3: 仅签名

class CacheManager:
    """PR 结果缓存——(PR_URL + SHA) 索引，支持增量审查"""
    def get(self, pr_url, sha) -> ReviewResult | None: ...
    def put(self, pr_url, sha, result) -> Path: ...
    def get_latest(self, pr_url) -> ReviewResult | None: ...
    def get_base_for_incremental(self, pr_url, current_sha) -> tuple[str, ReviewResult] | None: ...
    def list_reviews(self, pr_url) -> list[dict]: ...
```

**实际实现文件**：
```
insightor/processing/
├── file_filter.py        # FileFilter
├── language_detector.py  # LanguageDetector
├── token_estimator.py    # TokenEstimator
├── diff_compressor.py    # DiffCompressor
└── cache_manager.py      # CacheManager
```

**测试方式**：
- FileFilter: 锁文件/图片/node_modules/vendor/自定义规则 过滤测试
- LanguageDetector: 语言检测、分组、优先级排序测试
- TokenEstimator: tiktoken 精确 + fallback 估算测试
- DiffCompressor: 渐进压缩 + budget 裁剪测试
- CacheManager: put/get/latest/base 测试

---

#### PR #4：AI 客户端抽象层（已实现 — 双路径架构）

**标题**：实现多模型 LLM 调用抽象层，Anthropic 原生直连 + LiteLLM 兜底，支持流式输出与 Fallback 链

**关键新增（vs V2）**：
- **双路径架构**：`anthropic/` 前缀时使用原生 Anthropic SDK + raw HTTP 直连（绕开第三方 API 网关的 CLI 来源限制），其他供应商走 LiteLLM 统一接口
- `chat_completion_stream()` 方法：流式调用 LLM，yield token 增量
- `_get_api_base()`：自动根据模型前缀查找对应供应商的 API Base URL，同时兼容 `*_API_BASE` 和 `*_BASE_URL` 两种命名
- `_get_extra_headers()`：支持 `{PROVIDER}_EXTRA_HEADERS` 环境变量注入自定义 HTTP 头（JSON 格式）
- `ANTHROPIC_AUTH_TOKEN` 兼容：除 `ANTHROPIC_API_KEY` 外也识别 Claude Code 的 `ANTHROPIC_AUTH_TOKEN`
- `load_dotenv(override=True)`：确保 .env 值覆盖 Shell 中已有的同名环境变量

**双路径路由逻辑**：
```
model.startswith("anthropic/")?
  ├── YES → raw HTTP (httpx) → POST {base_url}/v1/messages
  │         完全控制 Headers → 绕过网关 CLI 检测
  └── NO  → LiteLLM.acompletion()
             openai/, deepseek/, 其他供应商
```

**涉及接口**：

```python
class LLMHandler:                         # ★ v3: 重命名自 LiteLLMHandler
    async def chat_completion(self, ...) -> AIResponse: ...
    async def chat_completion_stream(self, ...) -> AsyncIterator[str]: ...
    async def _call_anthropic(self, ...)  # raw HTTP 直连 Anthropic API
    async def _call_litellm(self, ...)    # LiteLLM 统一接口
    @staticmethod _get_api_base(model)    # 供应商 → API Base URL 查找
    @staticmethod _get_extra_headers(model) # 自定义请求头注入
    @staticmethod _get_anthropic_api_key()  # 兼容 ANTHROPIC_AUTH_TOKEN

# 向后兼容
LiteLLMHandler = LLMHandler
```

**涉及的供应商配置环境变量**：
```
_PROVIDER_API_BASE_ENV = {
    "openai":    ["OPENAI_API_BASE", "OPENAI_BASE_URL"],
    "anthropic": ["ANTHROPIC_API_BASE", "ANTHROPIC_BASE_URL"],
    "deepseek":  ["DEEPSEEK_API_BASE", "DEEPSEEK_BASE_URL"],
}
```

---

### Day 2 — 核心引擎

---

#### PR #5：Prompt 模板系统 + Response Parser + 流式解析

**标题**：实现 Prompt 模板引擎、Response Parser 适配器与流式增量解析

**功能描述**：
Jinja2 Prompt 模板（TOML 存储），支持从 `.insightor.yml` 注入 custom_rules/conventions/safe_patterns。Response Parser 适配器将 AI 响应 → URF。**新增**：StreamParser——从流式 AI 输出中增量解析 Finding，逐条 yield。

**关键新增（vs V2）**：
- PromptBuilder 注入 `{{ custom_rules }}`、`{{ conventions }}`、`{{ safe_patterns }}`、`{{ context_chunks }}`
- StreamParser：监听流式输出 → 检测 JSON 对象边界 → 每解析完一个 Finding 就 yield

**涉及接口**：

```python
class PromptBuilder:
    def __init__(self, template_dir: str | None = None): ...
    def build(self, tool: str, vars: dict | None = None) -> tuple[str, str]
    # vars 当前使用: title, description, branch, base_branch, author,
    #   additions, deletions, files_changed, diff, commit_messages,
    #   file_list, custom_rules, focus_categories
    # ★ 计划中（PR #14-16 注入）: conventions, safe_patterns, context_chunks

class ResponseParser:
    @staticmethod
    def parse(raw: str, meta: ReviewMeta) -> ReviewResult: ...
    @staticmethod
    def from_dict(data: dict, meta: ReviewMeta) -> ReviewResult: ...

# ★ v3 新增（计划中，Web UI PR #17 前实现）
class StreamParser:
    """流式增量解析器：边接收 token 边 yield Finding（计划中，待 Web UI 时实现）"""
    def __init__(self, meta: ReviewMeta)
    def feed(self, chunk: str) -> list[Finding]: ...  # 返回新解析出的 findings
    def flush(self) -> list[Finding]: ...             # 流结束后处理剩余 buffer
    def finalize(self) -> ReviewResult: ...            # 组装完整的 ReviewResult
```

---

#### PR #6：核心 Review 管线（含流式 + 增量 + 上下文）

**标题**：实现核心 Review 管线，集成上下文管线、流式输出与增量审查

**功能描述**：
将 PR #2-#5 组件串联为完整管线。支持 quick/standard/deep 分析深度，自动选择上下文层。支持流式模式（逐条 yield Finding）、增量模式（仅分析新 commit）。

**管线的 8 步流程**：

```
1. 环境检测: BuildInfo + 增量检测 → 决定全量/增量模式
2. 获取数据: PR info + files + commits
3. 构建上下文: ContextPipeline.gather(pr_info, files, depth) → AssembledContext
4. Diff 处理: 过滤 + 排序 + 压缩 (budget = remaining_budget from context)
5. 构建 Prompt: PromptBuilder.build(tool, vars + context_chunks + rules)
6. AI 分析: streaming or batch LLM call
7. 解析结果: StreamParser → incrementally parse → yield findings
8. 后处理: 计算 MergeReadiness + 组装 ReviewResult
```

**涉及接口**：

```python
class ReviewPipeline:
    def __init__(self, model: str | None = None,
                 fallback_models: list[str] | None = None,
                 cache_dir: str | None = None): ...
    async def run(
        self, pr_url: str, tool: str = "review", depth: str = "standard",
        incremental: bool = False,
        on_progress: Callable[[str], None] | None = None,
        # ★ PR #14-16 新增（可选，有默认值）:
        # context_layers: list[str] | None = None,
    ) -> ReviewResult: ...

    async def run_streaming(  # ★ 计划中（Web UI PR #17 前实现）
        self, pr_url: str, tool: str, depth: str,
    ) -> AsyncIterator[StreamEvent]: ...
```

---

#### PR #7：PR 变更总结工具 (/describe)

**标题**：实现 PR 变更总结功能——自动生成 PR 描述与文件变更走览

**功能描述**：
自动分析 PR 代码变更，生成结构化总结：PR 类型分类、一句话概述、逐文件变更说明、可选 Mermaid 组件交互流程图。管线根据 `tool` 参数自动分发对应的解析器。

**涉及接口**：

```python
# ===== 新增 Schema 字段 =====
class PRSummary(BaseModel):
    pr_type: str
    overview: str
    files_changed: int
    additions: int
    deletions: int
    diagram: str = Field(default="", description="Mermaid 流程图代码")  # ★ 新增

# ===== 新增 DescribeParser =====
class DescribeParser:
    """将 describe 工具的 AI 响应解析为 ReviewResult。"""
    @staticmethod
    def parse(raw: str, meta: ReviewMeta) -> ReviewResult: ...
        # 调用 _extract_json(raw) → from_dict(data, meta)

    @staticmethod
    def from_dict(data: dict, meta: ReviewMeta) -> ReviewResult:
        # pr_type, overview, diagram → PRSummary
        # files[{path, change}] → list[FileWalkthrough]
        # 复用 _str_to_edit_type() 从 change 文本推断 EditType

# ===== Pipeline 工具感知改造 =====
class ReviewPipeline:
    async def run(self, pr_url, tool="review", depth="standard", ...) -> ReviewResult:
        # Step 4: 注入 file_list 到 prompt vars (describe/risks 模板使用)
        # Step 6: DescribeParser.parse() when tool=="describe" else ResponseParser.parse()
        # 进度消息按工具区分 (describe 显示文件数，review 显示发现数)
```

**关键新增**：
- `DescribeParser`：解析 describe 输出 JSON（`pr_type`、`overview`、`files[{path, change}]`、`diagram`）→ `ReviewResult`
- `PRSummary.diagram`：存储 Mermaid 流程图代码（无则空字符串）
- Pipeline 工具感知：根据 `tool` 分发 DescribeParser/ResponseParser
- Pipeline 新增 `file_list` 变量注入（所有模板可用）
- `scripts/describe.py`：CLI 入口，支持 `--debug`/`--depth`
- `insightor/config/prompts/describe.toml`：完善 prompt，含 PR 类型分类规则、文件说明要求、Mermaid 生成规则

**测试方式**：
- 7 个 DescribeParser 单元测试（basic、full_with_diagram、empty、files、edit_type、parse_raw、returns_review_result）
- 1 个 pipeline 分发测试
- 端到端：`python scripts/describe.py <PR_URL>` 对比 AI 输出与预期

---

### Day 3 — 特性完善与产品化

---

#### PR #8：风险代码识别工具 (/risks) + Merge Readiness

**标题**：实现风险代码识别与合并就绪评估——自动计算阻断问题与审查优先级

**功能描述**：
AI 聚焦安全/并发/性能/逻辑/数据丢失风险进行审查。**新增**：`MergeReadinessCalc` 自动从 findings 计算 MergeReadiness；`RisksParser` 解析 risks 工具输出，AI 未提供 overall 评分时采用 fallback 计算。

**涉及接口**：

```python
# ===== 新增 MergeReadinessCalc =====
class MergeReadinessCalc:
    """独立工具：从 findings 计算 MergeReadiness。AI 未提供 overall 时的 fallback。"""
    @staticmethod
    def calculate(
        findings: list[Finding],
        files_changed: int = 0,
    ) -> MergeReadiness:
        # score = clamp(100 - Σ(sev*weight), 0, 100)
        #   critical:-30, high:-10, medium:-3, low:-1
        # blocking_issues = 所有 critical + (h>=3 ? 所有 high : 无)
        # review_priority = critical→high, high|files>10→medium, else→low
        # estimated_review_time_min = len(findings) * 2
        # summary 自动生成中文描述

# ===== 新增 RisksParser =====
class RisksParser:
    """解析 risks AI 响应 JSON → ReviewResult。"""
    @staticmethod
    def parse(raw: str, meta: ReviewMeta) -> ReviewResult: ...
    @staticmethod
    def from_dict(data: dict, meta: ReviewMeta) -> ReviewResult:
        # findings → _parse_finding()
        # overall 存在 → AI 提供值
        # overall 缺失 → MergeReadinessCalc.calculate() fallback
```

**关键新增**：
- `MergeReadinessCalc`：独立工具类，从 findings 计算 MergeReadiness（score、blocking_issues、review_priority、estimated_review_time_min）
- `RisksParser`：处理 risks 输出，AI 提供 overall 时直接使用，否则 fallback 到 MergeReadinessCalc
- `_parse_priority()`：字符串 → ReviewPriority 枚举
- Pipeline 增加 `tool=="risks"` 分支分发到 RisksParser
- `scripts/risks.py`：CLI 入口，支持 `--debug`/`--depth`/`--focus`
- `insightor/config/prompts/risks.toml`：增强 prompt，增加 overall 评分输出和评分规则

**测试方式**：
- 12 个 MergeReadinessCalc 单元测试（no_findings、critical_only、blocks、high_threshold、score_clamping、review_priority、estimated_time）
- 8 个 RisksParser 单元测试（with_overall、missing_overall、empty、findings_mapped、parse_raw）
- 1 个 pipeline risks 路由测试
- 端到端：`python scripts/risks.py <PR_URL> --focus security`

---

#### PR #9：Review 建议生成工具 (/improve) — 已合并到 review

**状态**：已于 PR #12 后合并到 review 工具。`insightor improve` 命令、`ImproveParser`、`scripts/improve.py`、`improve.toml` 均已移除。代码改进建议能力由 `insightor full` 的 review 部分统一提供，含 feedback checkbox。

---

#### PR #10：Composite Output Service — 多路输出基础设施

**标题**：实现组合输出层——多路发布（终端/Markdown/GitHub/JSON）与去重指纹

**功能描述**：
建立 Insightor 输出层基础设施。CompositeOutputService 将 ReviewResult 同时发布到终端（Rich 美化）、Markdown 报告文件、GitHub PR 评论、JSON 持久化。FingerprintGenerator 基于 SHA256 对 findings 去重。

**涉及接口**：

```python
# ===== OutputService 协议 =====
class OutputService(Protocol):
    def post(self, result: ReviewResult) -> None: ...
    def flush(self) -> None: ...

class CompositeOutput:
    def __init__(self, services: list[OutputService])
    def post(self, result: ReviewResult) -> None  # 遍历调用
    def flush(self) -> None
    def add(self, service: OutputService) -> None

# ===== 四路输出实现 =====
class ConsoleOutput:           # Rich Panel + Table 美化终端
class MarkdownFileOutput:      # 结构化 insightor-review-{pr}.md
class GitHubCommentOutput:     # PyGithub 发布 PR 评论，支持更新已有评论
class JSONOutput:              # ReviewResult JSON 持久化到 .insightor/reviews/

# ===== 去重 =====
class FingerprintGenerator:
    @staticmethod
    def generate(finding) -> str: ...       # SHA256(path|title|category)
    @staticmethod
    def deduplicate(findings) -> list: ...  # 按指纹去重
```

**关键新增**：
- `OutputService` Protocol + `CompositeOutput` 组合模式
- `ConsoleOutput`：Rich Panel/Table 美化，severity 颜色分级
- `MarkdownFileOutput`：生成结构化审查报告（PR 总结 + findings + 合并就绪）
- `GitHubCommentOutput`：发布/更新 PR 评论，带 bot 签名识别
- `JSONOutput`：JSON 持久化到 `.insightor/reviews/`
- `FingerprintGenerator`：SHA256 指纹去重
- Pipeline 审查完成后自动调用 CompositeOutput（默认 Console + Markdown + JSON）
- `insightor/output/` 包结构：base.py, console.py, markdown.py, github_comment.py, json_output.py, fingerprint.py

**测试方式**：
- 18 个单元测试（FingerprintGenerator 5 + CompositeOutput 4 + ConsoleOutput 3 + Markdown 3 + JSON 3）
- 端到端：`python scripts/review.py <PR_URL>` 验证终端输出 + .md 文件 + .json 文件生成

---

#### PR #11：人机协同审查 + 反馈闭环

**标题**：实现人机协同审查工作流——草稿解析、人工确认、反馈收集与质量追踪

**功能描述**：
在 PR #10 输出层基础上加入人类确认环节。AI 生成 Markdown 审查草稿（含 finding-id HTML 注释和 checkbox 状态标记），人类程序员编辑确认后通过 publish 脚本一键发布到 GitHub（PR URL 自动从 Markdown 检测）。GitHub 评论格式与 Markdown 保持一致，含完整发现详情。QualityTracker 统计每 category 历史准确率，持久化到 `.insightor/quality/`。

**工作流程**：

```
python scripts/review.py <PR_URL>        # AI 生成审查 → Markdown（含 checkbox + PR URL）
  → 人类编辑 .md 文件，勾选反馈状态
  → python scripts/publish.py draft.md   # 一键发布到 GitHub（PR URL 自动检测）
```

**涉及接口**：

```python
# ==== DraftParser ====
class DraftParser:
    """解析人类编辑后的 Markdown 草稿 → 更新 ReviewResult 的 finding.feedback。
    通过 HTML 注释 <!-- finding-id: UUID --> 匹配 finding，扫描 checkbox 状态。"""
    @staticmethod
    def parse(md_path: str, original_result: ReviewResult) -> tuple[ReviewResult, int]: ...
    @staticmethod
    def _extract_feedback_map(md_text: str) -> dict[UUID, FindingFeedback]: ...

# ==== QualityTracker ====
class QualityTracker:
    """按 category 追踪历史精确度，持久化到 .insightor/quality/。
    history.json 记录累积反馈计数（total/confirmed/false_positive/addressed/ignored），
    metrics.json 存储预计算的 QualityMetrics。"""
    def __init__(self, storage_dir: str = ".insightor/quality"): ...
    def track(self, result: ReviewResult) -> None: ...
    def get_precision(self, category: str) -> float: ...
    def export_metrics(self) -> QualityMetrics: ...

# ==== FeedbackCollector (stub) ====
class FeedbackCollector:
    """预留 GitHub Reactions 反馈收集接口，等 PR 评论发布流程稳定后实现。"""
    async def collect(self, result: ReviewResult) -> ReviewResult: ...    # no-op
    async def read_comment_reactions(self, comment_url: str) -> dict: ... # NotImplementedError
```

**关键新增**：
- `insightor/feedback/` 包：DraftParser、QualityTracker、FeedbackCollector
- DraftParser：正则匹配 HTML 注释中的 finding-id，扫描 checkbox 状态（第一个 `[x]` 生效），提取审查者和备注
- DraftParser 扫描窗口：原 `i+30` 行硬限制改为从 finding-id 扫描到下一个 finding-id（无上限），修复代码块过长时 checkbox 在窗口外导致反馈丢失的 bug
- `MarkdownFileOutput` 增强：每个 finding 标题嵌入 `<!-- finding-id: UUID -->`，追加 feedback checkbox 区域（confirmed/false_positive/addressed/ignored），footer 嵌入 `<!-- insightor-pr-url: URL -->` 供 publish 脚本自动检测
- `GitHubCommentOutput` 重构：`_build_comment()` 输出与 Markdown 完全一致的结构（总结 + 合并就绪 + 变更文件表 + 完整发现详情含代码建议），不再只是简化表格
- `scripts/publish.py`：从 markdown 自动检测 PR URL，支持 `--dry-run`（仅预览变更）和 `--json`（指定 companion JSON），流程：加载原始 JSON → DraftParser 解析反馈 → GitHub 发布 → JSON 保存 → QualityTracker 追踪
- 人类编辑流程：Markdown 中 checkbox 格式 `- [x] confirmed`、`- [ ] false_positive` 等，审查者通过 `**审查者:**` 字段填写，备注通过 `**备注:**` 字段填写

**实际实现文件**：
```
insightor/feedback/
├── __init__.py          # 导出 DraftParser / QualityTracker / FeedbackCollector
├── draft_parser.py       # DraftParser
├── quality_tracker.py    # QualityTracker
└── collector.py          # FeedbackCollector (stub)
scripts/
└── publish.py            # CLI 发布脚本
```

**测试方式**：
- 17 个反馈层单元测试（TestDraftParser 7 + TestQualityTracker 8 + TestFeedbackCollector 2）
- 2 个 Markdown 输出测试（finding-id HTML 注释存在、checkbox 和 footer 存在）
- DraftParser 测试覆盖：无反馈、确认反馈、多发现、无 checkbox、未知 ID、空发现、只有备注无 checkbox
- QualityTracker 测试覆盖：confirmed、混合反馈、无数据、多类别、导出指标、持久化、跳过无反馈、累积追踪

---

#### PR #12：CLI 界面与端到端集成

**标题**：实现命令行交互界面，完成全系统端到端集成

**功能描述**：
基于 click 实现统一的 `insightor` CLI 命令，支持 full/review/describe/risks/publish 五个子命令。`full` 命令一次串联全部三个分析工具，生成三段式组合 Markdown（describe/risks/review），各段内容不重复，review 段含 feedback checkbox。publish 自动检测 full 报告并发布有 feedback 的 finding。集成 Rich `Console().status()` 实时进度展示，`--debug` 模式打印完整中间数据。`pyproject.toml` 已注册 `insightor = "insightor.cli:main"` 入口点。

**CLI 命令一览**：

```bash
# 一键全部分析（推荐）
insightor full <url> --depth deep
insightor full <url> --skip review --skip risks       # 跳过指定工具

# 完整审查
insightor review https://github.com/owner/repo/pull/123

# 快速/深度模式
insightor review <url> --depth quick
insightor review <url> --depth deep

# 增量审查
insightor review <url> --incremental

# 子命令
insightor describe <url>               # PR 总结
insightor risks <url> --focus security # 风险分析

# 发布已确认审查
insightor publish <md_path> --dry-run
```

**`insightor full` 工作流程**：

```
insightor full <url>
  ├── describe  → PR 总结 + 变更文件表
  ├── risks     → 安全/性能/并发风险发现
  └── review    → 代码审查发现（含 feedback checkbox）
       ↓
  FingerprintGenerator 跨工具去重
       ↓
  合并 Markdown: insightor-full-review-{pr}.md
  ├── ## 1. PR 总结 (describe)          — 无 checkbox
  ├── ## 2. 风险分析 (risks)            — 无 checkbox
  ├── ## 3. 代码审查 (review)           — 有 checkbox ← 人机协同段
  └── ## 反馈说明                        — 指向第3节
       ↓
  人类编辑第3节 checkbox → insightor publish
       ↓
  GitHub 评论含所有有 feedback 的 finding
```

**涉及接口**：

```python
# ==== CLI 入口 (click group) ====
@click.group()
def main(): ...

# ==== 子命令（5 个）====
@main.command(); def full(pr_url, depth, skip, debug): ...       # ★ 新增
@main.command(); def review(pr_url, depth, incremental, model, debug): ...
@main.command(); def describe(pr_url, depth, debug): ...
@main.command(); def risks(pr_url, depth, focus, debug): ...
@main.command(); def publish(md_path, dry_run, json_path): ...

# ==== 异步实现 ====
async def _full(pr_url, depth, skip, debug): ...
async def _review(pr_url, depth, incremental, model, debug): ...
async def _describe(pr_url, depth, debug): ...
async def _risks(pr_url, depth, focus, debug): ...
async def _publish(md_path, dry_run, json_path): ...

# ==== Full 辅助 ====
def _build_full_markdown(merged, results, pr_url, pr_num): ...   # 组装三段式 Markdown
def _extract_pr_num_from_url(pr_url): ...

# ==== Debug 辅助 ====
async def _debug_review(pr_url, depth): ...
async def _debug_tool(pr_url, tool, depth): ...
```

**关键新增**：
- `insightor full`：依次运行 describe → risks → review，`FingerprintGenerator.deduplicate()` 跨工具去重，生成 `insightor-full-review-{pr}.md`（三段式结构，含 `<!-- insightor-full-review -->` 标记）
- 所有子命令均支持 `--model` 参数覆盖默认模型
- `_pick_model()`：CLI `--model` 优先级最高，standard 深度从 `config.get("models.primary")` 读取（不再硬编码）
- `_render_code_block()`：渲染前剥离 LLM 输出中已有的 code fence，再统一包裹，避免嵌套围栏导致格式错乱
- 三段式 Markdown：各段内容独立不重复，第3节（review）含 feedback checkbox 和 `<!-- finding-id: UUID -->` 注释，前2节（describe/risks）不含 checkbox
- publish 增强：检测 `<!-- insightor-full-review -->` 标记 → 自动过滤只保留有 feedback 的 finding
- `--skip` 选项：可跳过指定工具，如 `--skip risks`
- `_load_original_result` 兼容 `insightor-full-review-{pr}.md` 文件名模式

**实际实现文件**：
```
insightor/
└── cli.py               # CLI 入口（6 个子命令 + 2 个 debug 辅助 + markdown 生成）
```

**测试方式**：
- 23 个 CLI 单元测试（click.testing.CliRunner）：full 帮助/参数/--skip/--debug、full-publish 过滤无 feedback 的 finding、以及 review/describe/risks/publish 测试
- full-publish 集成测试：构造三段式 Markdown + JSON，验证 publish 后只输出有 feedback 的 finding、无 feedback 的被过滤
- 手动验证：`python -m insightor.cli --help` 显示 full 子命令

---

### Day 4 — VSCode 插件 + 分层上下文管线 (Context Pipeline)

---

#### PR #13：VSCode 插件 — IDE 集成与可视化

**标题**：实现 Insightor VSCode 扩展——IDE 内一键审查、结果可视化、人机协同

**功能描述**：
将 Insightor 核心能力封装为 VSCode 扩展（TypeScript），在 IDE 内提供完整的 PR 审查工作流。插件通过调用 `insightor` CLI（子进程）或直接 import Python API 与核心通信。**同时**为后续 PR #14-16（分层上下文管线）预留扩展点，确保 Context Pipeline 完成后可直接合并到本分支。

**架构设计**：

```
VSCode Extension (TypeScript)              Insightor Core (Python)
═══════════════════════════                ═══════════════════════
┌─────────────────────────┐               ┌──────────────────────┐
│  Command Palette         │               │  CLI (click)         │
│  ├── insightor.full      │──subprocess──▶│  insightor full ...  │
│  ├── insightor.review    │               │  insightor review .. │
│  ├── insightor.describe  │               │  insightor publish . │
│  ├── insightor.risks     │               └──────────┬───────────┘
│  ├── insightor.publish   │               ┌──────────▼───────────┐
├─────────────────────────┤               │  ReviewPipeline       │
│  Webview Panel           │               │  .run(pr_url, tool,   │
│  ├── 四段式结果展示       │◀──JSON/UDP───│   depth, ...)         │
│  ├── 代码 diff 高亮       │               │   → ReviewResult     │
│  ├── Feedback checkbox   │               └──────────┬───────────┘
│  └── 一键 publish 按钮    │                          │
├─────────────────────────┤               ┌──────────▼───────────┐
│  Status Bar              │               │  URF (ReviewResult)   │
│  └── 审查进度/评分        │               │  .insightor/reviews/  │
├─────────────────────────┤               │  insightor-*.md       │
│  Diagnostics Integration │               └──────────────────────┘
│  └── Finding → Problem   │
└─────────────────────────┘
```

**稳定核心 API 契约（PR #14-16 必须保持兼容）**：

```python
# ===== 契约 1: CLI 接口（不变）=====
# insightor full <url> [--depth] [--skip] [--debug]
# insightor review <url> [--depth] [--incremental] [--debug]
# insightor describe <url> [--depth] [--debug]
# insightor risks <url> [--depth] [--focus] [--debug]
# insightor publish <md_path> [--dry-run] [--json]

# ===== 契约 2: Python API（向后兼容扩展）=====
class ReviewPipeline:
    async def run(
        self,
        pr_url: str,
        tool: str = "review",           # "review"|"describe"|"risks"
        depth: str = "standard",         # "quick"|"standard"|"deep"
        incremental: bool = False,
        on_progress: Callable = None,
        # ★ PR #14-16 新增（可选，有默认值）:
        # context_layers: list[str] | None = None,
        # context_config: ContextConfig | None = None,
    ) -> ReviewResult: ...

# ===== 契约 3: URF 数据格式（仅允许增量字段）=====
# ReviewResult / Finding / ReviewMeta — 现有字段不变
# PR #14-16 可新增: context_summary: ContextSummary | None
# 不可删除或重命名现有字段

# ===== 契约 4: 文件路径约定（不变）=====
# 审查结果 JSON:  .insightor/reviews/insightor-review-{pr_num}-{sha}-{ts}.json
# 审查报告 MD:    insightor-review-{pr_num}.md
# Full 报告 MD:   insightor-full-review-{pr_num}.md
# 质量数据:       .insightor/quality/
```

**VSCode 扩展涉及接口**：

```typescript
// ===== 扩展入口 =====
// package.json: contributes.commands, contributes.menus, contributes.views
export function activate(context: vscode.ExtensionContext): void;

// ===== Insightor Bridge（Python 通信层）=====
class InsightorBridge {
    constructor(pythonPath: string, cwd: string);
    // 子进程方式调用 CLI
    async runCommand(args: string[], onProgress?: (msg: string) => void): Promise<CommandResult>;
    // 读取已生成的 JSON 结果
    async loadResult(prNum: string): Promise<ReviewResult | null>;
    // 获取质量指标
    async getQualityMetrics(): Promise<QualityMetrics | null>;
}

// ===== Webview Provider =====
class InsightorReviewPanel {
    constructor(context: vscode.ExtensionContext);
    // 显示四段式审查结果
    showFullReview(markdownPath: string, reviewResult: ReviewResult): void;
    // 显示单工具结果
    showToolResult(tool: string, result: ReviewResult): void;
    // 处理 feedback checkbox 交互
    onFeedbackChanged(findingId: string, status: string): void;
    // 一键 publish
    publishReview(markdownPath: string): void;
}

// ===== Status Bar =====
class InsightorStatusBar {
    showProgress(tool: string, message: string): void;
    showScore(score: number, recommendation: string): void;
    hide(): void;
}

// ===== Diagnostics Integration =====
class FindingDiagnostics {
    // 将 Finding 映射为 VSCode Diagnostic (Problem tab)
    static toDiagnostic(finding: Finding): vscode.Diagnostic;
    static updateCollection(uri: vscode.Uri, findings: Finding[]): void;
}
```

**目录结构（仅新增文件，不修改 insightor/）**：

```
vscode/
├── package.json              # VSCode 扩展清单
├── tsconfig.json
├── src/
│   ├── extension.ts          # 入口：activate/deactivate
│   ├── bridge/
│   │   └── insightorBridge.ts # Python 通信层
│   ├── panels/
│   │   └── reviewPanel.ts    # Webview 面板
│   ├── providers/
│   │   ├── statusBar.ts      # 状态栏
│   │   └── diagnostics.ts    # Problem tab 集成
│   ├── commands/
│   │   ├── fullCommand.ts
│   │   ├── reviewCommand.ts
│   │   ├── describeCommand.ts
│   │   ├── risksCommand.ts
│   │   └── publishCommand.ts
│   └── utils/
│       ├── urfTypes.ts        # TypeScript URF 类型定义
│       └── config.ts          # VSCode 配置读取
└── .vscodeignore
```

**并行开发策略（PR #13 ↔ PR #14-16）**：

```
                    main (feature/fetch_pr)
                         │
                    ┌────┴────┐
                    │         │
              feature/    feature/
              pr13-vscode pr14-context  ← 用户从这里开始
                    │         │
                    │    feature/pr15-context
                    │         │
                    │    feature/pr16-context
                    │         │
                    └────┬────┘
                         │  PR #16 合并到 PR #13
                         ▼
                  feature/pr13-vscode
                  (含完整 Context Pipeline)
                         │
                         ▼
                       main
```

**关键原则**：
- PR #13 只新增 `vscode/` 目录，不修改 `insightor/` 中任何文件
- PR #14-16 修改 `insightor/` 但遵守稳定 API 契约
- 最终 PR #16 → PR #13 合并时，两边修改的是不同文件 → 零冲突
- 若需修改契约，先在 `docs/architecture-final.md` 更新，双方同步

**测试方式**：
- VSCode 扩展单元测试（TypeScript — mocha/chai）
- Python Bridge 子进程调用测试
- Webview 渲染测试
- 端到端：VSCode 内 `insightor.full` → Webview 展示 → 编辑 feedback → publish

---

#### PR #14：Context Pipeline 框架 + Layer 1-2

**标题**：实现分层上下文管线框架——Diff 上下文与文件上下文扩展

**功能描述**：
建立分层上下文管线基础框架。实现 Layer 1（Diff 上下文源）和 Layer 2（文件上下文扩展——import 解析、hunk ±N 行扩展）。定义 ContextSource 协议、ContextChunk、AssembledContext 数据结构。**注意**：本 PR 以 PR #13（VSCode 插件）分支为合入目标。

**涉及接口**：

```python
# ===== 协议与数据结构 =====
class ContextSource(Protocol):
    name: str; layer: int
    async def fetch(self, pr_info, files) -> ContextChunk: ...

@dataclass
class ContextChunk:
    source_name: str
    content: str
    metadata: dict  # {tokens, related_files, issues, ...}

@dataclass
class AssembledContext:
    chunks: list[ContextChunk]
    total_tokens: int
    remaining_budget: int
    summary: ContextSummary

# ===== Layer 1: Diff 上下文 =====
class DiffContextSource:
    name = "diff"; layer = 1
    async def fetch(self, pr_info, files) -> ContextChunk: ...

# ===== Layer 2: 文件上下文扩展 =====
class FileContextSource:
    name = "file_context"; layer = 2
    async def fetch(self, pr_info, files) -> ContextChunk: ...
    # 每个 hunk ±N 行上下文 + import 语句解析

# ===== ContextPipeline 框架 =====
class ContextPipeline:
    def __init__(self, sources: list[ContextSource], token_budget: int)
    async def gather(self, pr_info, files, depth) -> AssembledContext: ...
    def allocate_budget(self, depth) -> dict[str, int]: ...
```

**实际实现文件**：
```
insightor/processing/
├── context/
│   ├── __init__.py        # 导出 ContextPipeline, ContextSource 等
│   ├── protocol.py         # ContextSource, ContextChunk, AssembledContext
│   ├── pipeline.py         # ContextPipeline
│   ├── sources/
│   │   ├── diff.py         # DiffContextSource (Layer 1)
│   │   └── file_context.py # FileContextSource (Layer 2)
```

**对 PR #13 契约的影响**：零影响。仅新增 `insightor/processing/context/` 包，不修改现有接口。

**测试方式**：
- Layer 1: diff 上下文正确组装
- Layer 2: import 解析准确性；hunk 扩展行数正确
- ContextPipeline: budget 分配逻辑验证

---

#### PR #15：Layer 3-4 — Issue 关联 + 关联文件发现 (Aider PageRank)

**标题**：实现 Issue 上下文与 Aider 启发式关联文件发现

**功能描述**：
Layer 3 从 PR 描述提取 Issue 引用 → GitHub Issues API 拉取。Layer 4 使用 tree-sitter 符号提取 + 依赖图 + PageRank 排序发现关联文件，二分搜索 Token 适配，Tree View 骨架渲染。

**涉及接口**：

```python
# ===== Layer 3: Issue 上下文 =====
class IssueContextSource:
    name = "issues"; layer = 3
    async def fetch(self, pr_info, files) -> ContextChunk: ...

# ===== ★ Aider 启发：符号提取与缓存 =====
@dataclass
class SymbolTag:
    fname: str; rel_fname: str; line: int; name: str
    kind: str  # "def" | "ref"

class SymbolExtractor:
    """tree-sitter 符号提取器"""
    def extract_file(self, fname: str) -> list[SymbolTag]: ...
    def extract_from_diff(self, files) -> list[SymbolTag]: ...
    def get_modified_symbols(self, diff_files) -> set[str]: ...

class TagCache:
    """mtime 驱动的增量符号缓存 (diskcache)"""
    def get(self, fname: str) -> list[SymbolTag] | None: ...
    def put(self, fname: str, tags: list[SymbolTag]) -> None: ...

# ===== ★ Aider 启发：依赖图与排序 =====
class DependencyGraph:
    """文件级符号依赖图 (nx.MultiDiGraph)"""
    def add_tags(self, tags: list[SymbolTag]) -> None: ...
    def build_edges(self) -> None:
        """权重乘数: PR引用=50x, 复合名=10x, 私有=0.1x, 泛用=0.1x"""

class RelevanceRanker:
    """个性化 PageRank 文件相关性排序"""
    def rank(self, pr_files, mentioned_idents, dependency_map) -> list[tuple[str, str, float]]: ...

class BudgetFitter:
    """二分搜索 Token 预算内最优符号集合"""
    def fit(self, ranked: list, budget: int, renderer) -> str: ...

class CompactCodeRenderer:
    """紧凑 Tree View 渲染"""
    def render(self, items, context_lines=3) -> str: ...

# ===== Layer 4: 关联文件 =====
class RelatedFileSource:
    name = "related_files"; layer = 4
    # 使用 PageRank 算法发现关联文件
    async def fetch(self, pr_info, files) -> ContextChunk: ...
```

**测试方式**：
- tree-sitter 符号提取准确性（Python/JS/TS）
- TagCache mtime 失效和 diskcache 持久化
- PageRank 排序结果（PR 文件排前、泛用符号降权）
- BudgetFitter 二分搜索选择数量
- CompactCodeRenderer token 数偏差

---

#### PR #16：Layer 5 + Context Pipeline 集成

**标题**：实现仓库结构分析层，并将分层上下文管线完整接入 Review Pipeline

**功能描述**：
Layer 5 对全仓库进行 AST 分析，生成仓库地图。将 PR #14-15 的 Context Pipeline 集成到 ReviewPipeline.run() 中。按 AnalysisDepth 控制启用层（quick: L1/L2, standard: L1-L4, deep: L1-L5）。context_summary 填充到 ReviewResult。Token 预算自动分配。**本 PR 最终合并到 PR #13（VSCode 插件）分支**，使 VSCode 插件获得完整 Context Pipeline 能力。

**涉及接口**：

```python
# ===== Layer 5: 仓库分析 =====
class RepoAnalysisSource:
    name = "repo_analysis"; layer = 5
    async def fetch(self, pr_info, files) -> ContextChunk: ...
    # 1. Git clone / 本地仓库访问
    # 2. tree-sitter 全仓库符号提取
    # 3. 仓库地图生成
    # 4. 影响范围分析
    # 5. 项目约定检测

# ===== ReviewPipeline 增强 =====
class ReviewPipeline:
    async def run(
        self, pr_url, tool, depth, ...,
        context_layers: list[str] | None = None,   # ★ 新增（可选）
        context_config: ContextConfig | None = None, # ★ 新增（可选）
    ) -> ReviewResult:
        # Step 2.5: 构建上下文（仅当 context_layers 非空）
        ctx_pipeline = ContextPipeline(sources=[...], token_budget=...)
        assembled = await ctx_pipeline.gather(pr_info, files, depth)
        # assembled.chunks → 注入 prompt
        # assembled.summary → context_summary 字段
```

**由 AnalysisDepth 控制启用层**：

```
            L1  L2  L3  L4  L5
quick       ✅  ✅
standard    ✅  ✅  ✅  ✅
deep        ✅  ✅  ✅  ✅  ✅
```

**合并到 PR #13 的保证**：
- `ReviewPipeline.run()` 新增参数均有默认值 → 现有调用无需修改
- `ReviewResult` 新增 `context_summary` 字段为可选 → 反序列化兼容
- 所有新增文件在 `insightor/processing/context/` 下 → 不与 `vscode/` 冲突

**测试方式**：
- quick/standard/deep 三层上下文正确启用
- context_summary 字段完整填充
- Token 预算不超限
- 端到端：`insightor full <PR_URL> --depth deep` 验证多层上下文效果
- 合并验证：PR #16 合并到 PR #13 后，VSCode 插件仍正常运行

---

### Day 5 — 产品化与文档

---

#### PR #17：Web UI（可选增强）

**标题**：实现基于 FastAPI + SSE 的 Web 界面，支持流式实时展示

**关键新增（vs V2）**：
- SSE 流式推送分析进度和增量结果
- 结果页面带实时更新的 Tab（总结 / 风险 / 建议 / 合并就绪）

---

#### PR #18：文档与集成测试

**标题**：编写项目文档、架构设计说明、模型/上下文/质量设计思路与端到端测试

**文档必须覆盖**：

| 章节 | 核心问题 |
|------|----------|
| **模型选择设计思路** | 三层模型体系 (primary/fallback/weak)；不同任务的模型推荐；准确性 vs 速度 vs 成本的决策矩阵；未来模型扩展 |
| **上下文获取方式** | 五层上下文管线详解；每层的获取方式与成本；Token 预算分配策略；已知局限性（无运行时分析、无法验证业务逻辑） |
| **误报与漏报控制** | 置信度阈值 + 自反思评分 + safe_patterns 预过滤 + 反馈闭环 + 依赖映射防漏报；持续改善机制 |
| **响应速度设计** | 深度策略 (quick 15s / standard 30s / deep 60s)；流式输出感知优化；并行分片 (大 PR)；缓存策略；增量审查 |
| **质量度量框架** | 每 category 历史准确率；自反思评分分布；测试覆盖变化；用户反馈闭环 |
| **未来扩展方向** | 短期：AST 深度上下文、自定义规则引擎、IDE 插件；中期：RAG + 代码知识图谱、Issue 自动关联；长期：自学习策略、团队编码风格建模 |

---

## 七、PR 依赖关系图

```
PR #1 (工程 + 配置 + URF v3)  ← 基础，所有 PR 依赖
    │
    ├── PR #2 (GitHub Provider)
    │     │
    │     └── PR #3 (Diff Processing)
    │           │
    │           └── PR #6 (核心管线)
    │                 │
    │     ┌───────────┼───────────┐
    │     │           │           │
    │  PR #7      PR #8       PR #9
    │ (总结)     (风险+MR)   (建议)
    │     │           │           │
    │     └───────────┼───────────┘
    │                 │
    │           PR #10 (Output 基础)
    │                 │
    │           PR #11 (人机协同 + 反馈)
    │                 │
    │           PR #12 (CLI + full 命令)
    │                 │
    │     ┌───────────┴───────────┐
    │     │  ★ 并行开发（不同文件）  │
    │     │                       │
    │  PR #13 (VSCode 插件)    PR #14 (Ctx L1-2)
    │  只新增 vscode/         新增 processing/context/
    │     │                       │
    │     │                  PR #15 (Ctx L3-4)
    │     │                  新增 tree-sitter 等
    │     │                       │
    │     │                  PR #16 (Ctx L5 + 集成)
    │     │                  修改 pipeline.py
    │     │                       │
    │     └───────────┬───────────┘
    │                 │  PR #16 合并到 PR #13
    │                 ▼
    │           PR #13 + PR #16
    │           (VSCode 插件 + 完整 Ctx Pipeline)
    │                 │
    │           PR #17 (Web UI, 可选)
    │                 │
    │           PR #18 (文档 + 集成测试)
    │
    └── PR #4 (AI 客户端 + 流式)
          │
          └── PR #5 (Prompt + StreamParser 计划)
```

**并行开发说明**：

- **PR #13（VSCode 插件）** 只新增 `vscode/` 目录，不修改 `insightor/`
- **PR #14-16（Context Pipeline）** 新增 `insightor/processing/context/`，修改 `pipeline.py`（向后兼容）
- 两分支修改的文件互不重叠 → 最终 PR #16 可直接合并到 PR #13 分支
- 稳定 API 契约：CLI 参数不变、ReviewResult 字段只增不删、ReviewPipeline.run() 新参数有默认值

---

## 八、版本演进总结

| 版本 | 核心改进 | 来源 |
|------|----------|------|
| V1 | 基础 5 层架构 (12 PR) | PR-Agent |
| V2 | URF、CompositeOutput、Parser 适配器、分析深度、指纹去重、CI 抽象 (13 PR) | Reviewdog |
| V3 | 分层上下文管线、反馈闭环、增量审查、Merge Readiness、流式输出、自定义规则、质量度量 (18 PR, scope 增强) | 需求审计 + Aider + Sourcegraph (待补充) |

---

## 九、时间安排

| 天数 | PR | 内容 | 预估耗时 |
|------|-----|------|---------|
| **Day 1** | #1, #2, #3, #4 | 基础层：工程+URF+Provider+Diff处理+AI | 7-9h |
| **Day 2** | #5, #6, #7, #8 | 核心引擎：Prompt+Parser+管线+总结+风险+MR | 7-9h |
| **Day 3** | #9, #10, #11, #12 | 特性完善：建议+Output+人机协同+CLI | 7-9h |
| **Day 4** | #13 + #14-16 (并行) | VSCode 插件 ∥ Context Pipeline (并行开发) | 10-14h (2人) |
| **Day 5** | #17(可选), #18 | 产品化：Web+文档+集成测试 | 4-6h |
