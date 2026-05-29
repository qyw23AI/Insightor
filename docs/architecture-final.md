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
│  │ · IncrementalDetector: 检测是否为新 push，加载上次 ReviewResult      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│  Layer 1: 入口层 (Entry)                                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ · CLI (click): insightor review/describe/risks/improve            │   │
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
| LLM 调用 | `litellm` + streaming | 统一接口 + 流式输出 |
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

## 六、PR 拆分计划（共 13 个 PR，3 天）

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
    def load(self) -> dict
    def load_project_config(self, repo_root: str) -> dict | None
    def get_rules(self) -> list[str]        # custom_rules
    def get_conventions(self) -> list[str]  # coding conventions
    def get_safe_patterns(self) -> list[str]
    def get_dependency_map(self) -> dict[str, list[str]]

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
└── tools/                  # review/describe/risks/improve
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
└── tools/                  # review/describe/risks/improve
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
    def get_issue_context(self, issue_refs: list[str]) -> list[IssueInfo]: ...  # ★ Layer 3 用

class DiffService(Protocol):
    def get_diff(self, ctx) -> bytes: ...
    def get_strip(self) -> int: ...

@dataclass
class IssueInfo:  # ★ v3 新增
    number: int; title: str; body: str; labels: list[str]
```

---

#### PR #3：Diff 处理管线 + 分层上下文管线 (Aider 增强)

**标题**：实现 PR Diff 处理与 Aider 启发式分层上下文获取管线

**功能描述**：
对获取的 diff 数据进行多阶段处理（过滤、语言检测、Token 管理、渐进压缩）。**核心新增**：基于 Aider 架构的分层上下文管线——使用 tree-sitter 提取符号、构建依赖图、PageRank 排序关联文件、二分搜索 Token 适配。

**关键新增（vs V2）**：

1. **Aider 启发的 6 个核心模块** (新增 `processing/context/` 子包)：
   - `SymbolExtractor` — 使用 tree-sitter + `.scm` query 从源码提取符号定义/引用
   - `TagCache` — diskcache + mtime 驱动，只重新解析变更文件
   - `DependencyGraph` — networkx.MultiDiGraph，文件级符号依赖图
   - `RelevanceRanker` — 个性化 PageRank (PR 文件 50x 权重 → 降权噪音)
   - `BudgetFitter` — 二分搜索，在 token 预算内选最优符号集合
   - `CompactCodeRenderer` — Tree View 骨架渲染，节省 80% token

2. **五个 ContextSource 实现**：DiffSource、FileContextSource、IssueSource、RelatedFileSource (Aider PageRank)、RepoAnalysisSource

3. **IncrementalDiffer** 完善增量 diff + 结果合并

**涉及接口**：

```python
# ===== 文件处理 (保留 V2) =====
class FileFilter: ...
class LanguageDetector: ...
class TokenEstimator: ...
class DiffCompressor: ...

# ===== ★ Aider 启发：符号提取与缓存 =====
@dataclass
class SymbolTag:
    fname: str; rel_fname: str; line: int; name: str
    kind: str  # "def" | "ref"

class SymbolExtractor:
    """tree-sitter 符号提取器"""
    def __init__(self, query_dir: str = "config/queries")
    def extract_file(self, fname: str) -> list[SymbolTag]: ...
    def extract_from_diff(self, files: list[FilePatchInfo]) -> list[SymbolTag]: ...
    def get_modified_symbols(self, diff_files) -> set[str]: ...  # {symbol_name, ...}

class TagCache:
    """mtime 驱动的增量符号缓存"""
    def __init__(self, repo_path: str, cache_dir: str = ".insightor/tags")
    def get(self, fname: str) -> list[SymbolTag] | None: ...
    def put(self, fname: str, tags: list[SymbolTag]) -> None: ...
    def invalidate(self, fname: str) -> None: ...

# ===== ★ Aider 启发：依赖图与排序 =====
class DependencyGraph:
    """文件级符号依赖图 (nx.MultiDiGraph)"""
    def __init__(self)
    def add_tags(self, tags: list[SymbolTag]) -> None: ...
    def build_edges(self) -> None:
        """构建有向边: 引用方文件 → 定义方文件
           权重乘数: PR引用=50x, 复合名=10x, 私有=0.1x, 泛用(>5文件)=0.1x"""
    def get_callers(self, symbol: str) -> list[str]: ...
    def get_callees(self, symbol: str) -> list[str]: ...

class RelevanceRanker:
    """个性化 PageRank 文件相关性排序"""
    def __init__(self, graph: DependencyGraph)
    def rank(
        self,
        pr_files: set[str],                  # PR diff 文件 (personalization)
        mentioned_idents: set[str] = set(),   # PR 描述/Issue 中的标识符
        dependency_map: dict[str, list[str]] = {},  # .insightor.yml
    ) -> list[tuple[str, str, float]]:       # [(fname, symbol, score), ...]

class BudgetFitter:
    """二分搜索 Token 预算内最优符号集合"""
    def fit(self, ranked: list, budget: int, renderer) -> str: ...
    # 初始猜测: budget // 25 tokens_per_symbol
    # 接受条件: abs(actual - budget) / budget < 0.15

class CompactCodeRenderer:
    """紧凑 Tree View 渲染 (Aider grep_ast.TreeContext 风格)"""
    def render(self, items: list[tuple[str, str, float]], context_lines: int = 3) -> str:
        """输出格式:
        src/services/user.py:
        │class UserService:
        │    def authenticate(self, token):
        │        ...
        │    def find_by_email(self, email):
            ..."""

# ===== ★ 分层上下文管线 =====
class ContextSource(Protocol):
    name: str; layer: int
    async def fetch(self, pr_info, files) -> ContextChunk: ...

class RelatedFileSource(ContextSource):  # Layer 4 (Aider 增强)
    """★ 使用 PageRank 算法替代简单 git grep"""
    def __init__(self, provider, tag_cache, extractor):
        self.graph = DependencyGraph()
        self.ranker = RelevanceRanker(self.graph)
        self.fitter = BudgetFitter()
        self.renderer = CompactCodeRenderer()

    async def fetch(self, pr_info, files) -> ContextChunk:
        # 1. tree-sitter 提取 PR 中被修改的符号
        modified = self.extractor.get_modified_symbols(files)
        # 2. 获取/缓存仓库其余文件的 Tag
        all_tags = self._get_all_tags_with_cache(files)
        # 3. 构建依赖图 + PageRank 排序
        self.graph.add_tags(all_tags); self.graph.build_edges()
        ranked = self.ranker.rank(pr_files={f.filename for f in files})
        # 4. 二分搜索 + Tree View 渲染
        rendered = self.fitter.fit(ranked, self.token_budget, self.renderer)
        return ContextChunk(source_name="related_files", content=rendered, ...)

class ContextPipeline:
    async def gather(self, pr_info, files, depth) -> AssembledContext: ...
    def allocate_budget(self, depth) -> dict[str, int]: ...

# ===== 增量与缓存 =====
class IncrementalDiffer: ...
class CacheManager:
    def get(self, pr_url, sha) -> ReviewResult | None: ...
    def put(self, pr_url, sha, result) -> None: ...
    def get_incremental_base(self, pr_url, current_sha) -> tuple[str, ReviewResult] | None: ...
```

**目录结构**：
```
insightor/processing/context/
├── __init__.py
├── pipeline.py          # ContextPipeline
├── sources/
│   ├── __init__.py
│   ├── diff.py          # Layer 1
│   ├── file_context.py  # Layer 2
│   ├── issues.py        # Layer 3
│   ├── related_files.py # Layer 4 (★ Aider PageRank)
│   └── repo_analysis.py # Layer 5 (★ Aider Repo Map)
├── symbols.py           # ★ SymbolTag, SymbolExtractor
├── depgraph.py          # ★ DependencyGraph
├── ranker.py            # ★ RelevanceRanker
├── budget.py            # ★ BudgetFitter
├── renderer.py          # ★ CompactCodeRenderer
└── tag_cache.py         # ★ TagCache (diskcache + mtime)

config/queries/           # ★ tree-sitter .scm 查询文件
├── python-tags.scm
├── javascript-tags.scm
├── typescript-tags.scm
└── ...  (从 Aider 的 queries/ 目录复用)
```

**测试方式**：
- 测试 tree-sitter 对主要语言（Python/JS/TS/Go/Java）的符号提取准确性
- 测试 TagCache 的 mtime 失效和 diskcache 持久化
- 测试 PageRank 排序结果（PR 文件的相关文件是否排前，get/set 等泛用符号是否降权）
- 测试 BudgetFitter 二分搜索在不同预算下的选择数量
- 测试 CompactCodeRenderer 输出的 token 数与实际 token 数的偏差

---

#### PR #4：AI 客户端抽象层

*(与 V2 基本一致，新增流式调用支持)*

**标题**：实现多模型 LLM 调用抽象层，支持流式输出与 Fallback 链

**关键新增（vs V2）**：
- `chat_completion_stream()` 方法：流式调用 LLM，yield token 增量

**涉及接口**：

```python
class AIHandler(Protocol):
    async def chat_completion(self, model, system_prompt, user_prompt, ...) -> AIResponse: ...
    async def chat_completion_stream(self, model, system_prompt, user_prompt, ...) -> AsyncIterator[str]: ...  # ★ 新增

class LiteLLMHandler:
    async def chat_completion(self, ...) -> AIResponse: ...
    async def chat_completion_stream(self, ...) -> AsyncIterator[str]: ...  # ★ 新增
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
    def build(self, tool: str, vars: dict) -> tuple[str, str]
    # vars 新增: custom_rules, conventions, safe_patterns, context_chunks

class ResponseParser(Protocol):
    def parse(self, raw: str, meta: ReviewMeta) -> ReviewResult: ...
    def can_parse(self, raw: str) -> bool: ...

# ★ v3 新增
class StreamParser:
    """流式增量解析器：边接收 token 边 yield Finding"""
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
    async def run(
        self, pr_url: str, tool: str, depth: AnalysisDepth,
        incremental: bool = False, stream: bool = False,
    ) -> ReviewResult: ...

    async def run_streaming(
        self, pr_url: str, tool: str, depth: AnalysisDepth,
    ) -> AsyncIterator[StreamEvent]: ...  # ★ v3 新增：流式模式
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

**标题**：实现风险代码识别与合并就绪评估

**功能描述**：
AI 识别安全/并发/性能/逻辑/数据丢失风险。**新增**：自动计算 MergeReadiness——综合风险评分、阻断问题列表、审查优先级、预估人工审查时间。

**关键新增（vs V2）**：
- `MergeReadinessCalc.calculate(findings, stats)` → MergeReadiness
- 阻断规则：critical risk = blocked；3+ high risks = blocked
- 审查优先级：critical presence → high；>10 files → medium；else → low

**涉及接口**：

```python
class RiskTool:
    async def run(self, pr_url, depth, min_severity, focus_categories) -> ReviewResult: ...

class MergeReadinessCalc:  # ★ v3 新增
    def calculate(self, findings: list[Finding], stats: ReviewStats) -> MergeReadiness:
        score = 100
        score -= sum({critical:30, high:10, medium:3, low:1}[f.severity] for f in findings)
        score += (stats.quality.test_files_in_diff > 0) * 15
        score -= stats.file_walkthrough.__len__() * 0.5
        return MergeReadiness(score=max(0, min(100, score)), ...)
```

---

#### PR #9：Review 建议生成工具 (/improve)

*(与 V2 一致，deep 模式增加自反思校验)*

**标题**：实现 Review 建议智能生成——代码质量、最佳实践与可应用代码修补建议

---

#### PR #10：Composite Output Service + 反馈闭环

**标题**：实现组合输出层——多路发布、去重、反馈收集与质量追踪

**功能描述**：
CompositeOutputService 将 ReviewResult 同时发布到终端/Markdown/GitHub/JSON。**新增**：FeedbackCollector 从 GitHub Reaction 回读反馈信号，QualityTracker 统计每 category 的历史准确率。

**关键新增（vs V2）**：
- `FeedbackCollector`：回读 GitHub comment reaction → 更新 Finding.feedback
- `QualityTracker`：从反馈历史计算每 category 的 precision；将确认的误报模式反馈给 ConfigLoader.safe_patterns
- `StreamOutput`：流式输出到终端（Rich Live 实时更新）

**涉及接口**：

```python
class OutputService(Protocol):
    def post(self, result: ReviewResult) -> None: ...
    def flush(self) -> None: ...

class CompositeOutput:
    def __init__(self, services: list[OutputService])
    def post(self, result: ReviewResult) -> None
    def flush(self) -> None

class ConsoleOutput(OutputService): ...       # Rich 实时更新
class MarkdownFileOutput(OutputService): ...
class GitHubCommentOutput(OutputService): ...  # + reaction 回读
class JSONOutput(OutputService): ...

# ★ v3 新增
class FeedbackCollector:
    async def collect(self, result: ReviewResult) -> ReviewResult: ...
    async def read_comment_reactions(self, comment_url: str) -> dict[str, str]: ...
    # 返回 {finding_id: "confirmed"|"false_positive"}
    def update_safe_patterns(self, false_positives: list[Finding]) -> None: ...

class QualityTracker:
    def track(self, result: ReviewResult) -> None: ...
    def get_precision(self, category: str) -> float: ...
    def export_metrics(self) -> QualityMetrics: ...

class StreamOutput(OutputService):  # ★ v3 新增
    """流式输出：每收到 StreamEvent 就更新终端"""
    def on_event(self, event: StreamEvent) -> None: ...
```

---

#### PR #11：CLI 界面与端到端集成

**标题**：实现命令行交互界面，完成全系统端到端集成

**功能描述**：
`insightor` CLI 命令，支持 review/describe/risks/improve 四个子命令。集成流式进度展示（Rich Live）、增量模式（自动检测缓存）、分析深度选择。

**CLI 命令一览**：

```bash
# 完整审查
insightor review https://github.com/owner/repo/pull/123

# 快速/深度模式
insightor review <url> --depth quick   # ~15s
insightor review <url> --depth deep    # ~60s，含自反思 + 完整上下文

# 增量审查（自动检测上次缓存）
insightor review <url> --incremental

# 子命令
insightor describe <url>               # PR 总结
insightor risks <url> --focus security # 风险分析
insightor improve <url> --committable-only  # 代码建议

# 输出控制
insightor review <url> --output all --output-dir ./reviews
insightor review <url> --model claude-sonnet-4-6
insightor review <url> --config .insightor.yml

# 反馈标记
insightor feedback <url> --finding-id abc123 --status false_positive
```

---

#### PR #12：Web UI（可选增强）

**标题**：实现基于 FastAPI + SSE 的 Web 界面，支持流式实时展示

**关键新增（vs V2）**：
- SSE 流式推送分析进度和增量结果
- 结果页面带实时更新的 Tab（总结 / 风险 / 建议 / 合并就绪）

---

#### PR #13：文档与集成测试

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
    │     └── PR #3 (Diff + ContextPipeline)  ← ★ 增强
    │           │
    │           └── PR #6 (核心管线 + 流式) ← ★ 增强
    │                 │
    │     ┌───────────┼───────────┐
    │     │           │           │
    │  PR #7      PR #8       PR #9
    │ (总结)     (风险+MR)   (建议)
    │     │           │           │
    │     └───────────┼───────────┘
    │                 │
    │           PR #10 (Output + 反馈) ← ★ 增强
    │                 │
    │           PR #11 (CLI)
    │                 │
    │           PR #12 (Web UI, 可选)
    │                 │
    │           PR #13 (文档 + 集成测试)
    │
    └── PR #4 (AI 客户端 + 流式)  ← ★ 增强
          │
          └── PR #5 (Prompt + StreamParser)  ← ★ 增强
```

---

## 八、版本演进总结

| 版本 | 核心改进 | 来源 |
|------|----------|------|
| V1 | 基础 5 层架构 (12 PR) | PR-Agent |
| V2 | URF、CompositeOutput、Parser 适配器、分析深度、指纹去重、CI 抽象 (13 PR) | Reviewdog |
| V3 | 分层上下文管线、反馈闭环、增量审查、Merge Readiness、流式输出、自定义规则、质量度量 (13 PR, scope 增强) | 需求审计 + Aider + Sourcegraph (待补充) |

---

## 九、时间安排

| 天数 | PR | 内容 | 预估耗时 |
|------|-----|------|---------|
| **Day 1** | #1, #2, #3, #4 | 基础层：工程+URF+Provider+Diff+ContextPipeline+AI | 7-9h |
| **Day 2** | #5, #6, #7, #8 | 核心引擎：Prompt+StreamParser+管线+总结+风险+MR | 7-9h |
| **Day 3** | #9, #10, #11, #12(可选), #13 | 特性完善：建议+Output+CLI+Web+文档 | 7-9h |
