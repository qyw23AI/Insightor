# Reviewdog 架构分析报告

> 分析 Reviewdog 的架构设计，提炼可复用模式以改进 Insightor 架构。

---

## 一、Reviewdog 架构总览

Reviewdog 是一个**代码审查诊断聚合器**——它不生成新的诊断，而是将各种 Linter 工具的输出**标准化**后，**过滤**到 PR diff 范围内，再**发布**到代码托管平台。

### 核心设计哲学：“只评论你改过的行”

```
Linter 输出 (stdin)
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  Layer 1: 解析层 (Parser)                              │
│  · 适配器模式：多输入格式 → 统一的 RDF Diagnostic       │
│  · errorformat / rdjson / sarif / checkstyle / diff   │
│  · Parser 接口：Parse(r io.Reader) → []*Diagnostic     │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  Layer 2: 过滤层 (Filter)                              │
│  · Diff 解析 → FileDiff → Hunk → Line                  │
│  · 策略模式：added / diff_context / file / nofilter     │
│  · 核心查询：ShouldReport(path, lnum) → bool           │
│  · 哈希表索引 O(1) 查找                                │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  Layer 3: 发布层 (Service / Reporter)                   │
│  · 策略模式：多平台 CommentService + DiffService         │
│  · 组合模式：multiCommentService (多路输出)             │
│  · 去重：指纹嵌入 (MetaComment protobuf)                 │
│  · 降级：API 失败 → 本地 fallback                       │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  Layer 4: 配置 & CI 环境                                │
│  · .reviewdog.yml 项目配置                             │
│  · cienv 包：统一 CI 环境抽象                           │
│  · project.Run()：并发执行多 Linter                     │
└──────────────────────────────────────────────────────┘
```

---

## 二、Reviewdog 的关键架构模式

### 模式 1：通用中间格式 (Universal Intermediate Format)

Reviewdog 的核心洞察：**所有 Linter 输出互不兼容，先统一成一个中间格式**。

Reviewdog Diagnostic Format (RDF) 是 protobuf 定义的结构化 Diagnostic：

```protobuf
message Diagnostic {
  string message = 1;
  Location location = 2;    // {path, range{start{line,col}, end{line,col}}}
  Severity severity = 3;    // ERROR | WARNING | INFO
  Source source = 4;        // {name, url}
  Code code = 5;            // {value, url}
  repeated Suggestion suggestions = 6;  // code fixes
  string original_output = 7;
  repeated RelatedLocation related_locations = 8;
}
```

**对 Insightor 的启发**：
- 定义 **Universal Review Format (URF)**——所有 AI 分析结果（总结/风险/建议）都输出到这个统一 Schema
- 不同 AI 模型的原始响应经过 Parser 层转换为 URF
- 后续的所有处理（格式化、过滤、输出）都基于 URF

### 模式 2：Parser 适配器模式

```
输入格式                  Parser                      内部格式
┌──────────┐     ┌──────────────────┐
│ Checkstyle│ ──→ │CheckStyleParser  │          ┌────────────┐
│ SARIF    │ ──→ │SarifParser      │ ──────→  │ Diagnostic │
│ errorfmt │ ──→ │ErrorformatParser│          └────────────┘
│ rdjson   │ ──→ │RDJSONParser     │
│ diff     │ ──→ │DiffParser       │
└──────────┘     └──────────────────┘
```

**对 Insightor 的启发**：
不仅仅是 Linter 输出的解析，对 Insightor 而言是 **AI 模型响应的解析**：

```
AI 模型                   Parser                      内部格式
┌──────────┐     ┌──────────────────┐
│ OpenAI   │ ──→ │OpenAIResponse    │
│ Claude   │ ──→ │ClaudeResponse   │ ──────→  URF
│ DeepSeek │ ──→ │DeepSeekResponse │
└──────────┘     └──────────────────┘
```

### 模式 3：策略模式 + 组合模式的输出层

```go
// 策略接口
type CommentService interface {
    Post(ctx context.Context, c *Comment) error
}

// 组合模式：一份输入，多路输出
type multiCommentService struct {
    services []CommentService
}
func (m *multiCommentService) Post(ctx context.Context, c *Comment) error {
    for _, s := range m.services {
        s.Post(ctx, c)  // 同时输出到 GitHub + 终端 + 文件
    }
}
```

**对 Insightor 的启发**：
一份 AI Review 结果可以同时输出到：
- 终端（Rich 美化）
- Markdown 文件
- GitHub PR Comment
- JSON API 响应

### 模式 4：过滤模式策略

```
filterMode:
  added:       只报告新增/修改行的诊断
  diff_context: 报告 diff 上下文范围内的诊断（变更行 ±N 行）
  file:        报告任何变更文件内的诊断
  nofilter:    不过滤，报告所有诊断
```

**对 Insightor 的启发**：
AI Review 的**分析深度策略**可以设计成类似的分层：

```
analysisDepth:
  quick:    仅 PR 总结 + CRITICAL 风险（~15s，适合高频触发）
  standard: PR 总结 + 全部风险 + 关键建议（~30s，默认）
  deep:     PR 总结 + 全部风险 + 全量建议 + 自反思校验（~60s，合并前）
```

### 模式 5：评论去重 (Comment Deduplication)

每次发布评论时，嵌入一个指纹（`MetaComment` protobuf 的 base64），下次发布前先拉取已有评论 → 提取指纹 → 跳过已有 / 删除过时的。

```
发布流程:
  1. 获取已有评论列表
  2. 从评论 HTML 中提取 MetaComment 指纹
  3. 新诊断 vs 已有指纹：
     - 指纹已存在 → 跳过（去重）
     - 指纹不存在 → 发布新评论
     - 旧指纹在新诊断中不存在 → 删除旧评论（过时结果清理）
```

**对 Insightor 的启发**：
当 Insightor 多次审查同一个 PR 时（如 push 新 commit 后），可以：
- **缓存上次审查结果**，与本次 diff 对比
- **增量审查**：只审查变更的部分
- **评论管理**：更新已有 comment 而非重复发布

### 模式 6：优雅降级 (Graceful Degradation)

```
GitHub API 权限充分 → 使用 Review API 发布行内评论
GitHub API 权限不足 → 使用 Actions Logging Commands 发布注解
无 GitHub 环境     → 降级为本地终端输出
```

**对 Insightor 的启发**：

```
主模型可用   → 使用主模型分析（最佳质量）
主模型不可用 → Fallback 到备用模型
所有模型不可用 → 使用本地缓存的规则引擎
```

### 模式 7：CI 环境抽象层

```go
type BuildInfo struct {
    Owner, Repo, SHA string
    PullRequest      int
    Branch           string
}
// 从 GITHUB_ACTIONS / TRAVIS / CIRCLE / GITLAB / BITBUCKET / ... 统一提取
```

**对 Insightor 的启发**：
不只是支持 GitHub，也要为未来的 GitLab / Gitee / 自托管 Git 预留接口。

### 模式 8：项目级配置文件

```yaml
# .reviewdog.yml
runner:
  golint:
    cmd: golint ./...
    errorformat: ["%f:%l:%c: %m"]
  eslint:
    cmd: eslint -f rdjson .
    format: rdjson
```

**对 Insightor 的启发**：

```yaml
# .insightor.yml
review:
  ignore_files: ["*.lock", "*.min.js", "vendor/**"]
  extra_instructions: "请特别关注 SQL 注入和 XSS 风险"
  risk_severity_min: medium
  max_suggestions: 15

models:
  primary: "claude-sonnet-4-6"
  fallback: "deepseek-v3"
  weak: "gpt-4o-mini"  # 简单任务用便宜模型
```

---

## 三、PR-Agent vs Reviewdog 架构对比

| 维度 | PR-Agent | Reviewdog | Insightor 应采用 |
|------|----------|-----------|-----------------|
| **核心功能** | AI 生成 Review | 聚合 Linter 结果 | AI 生成 Review（主） + Linter 聚合（辅） |
| **数据模型** | 隐式（TOML/YAML） | 显式（protobuf RDF） | **显式 URF JSON Schema** |
| **解析层** | Jinja2 模板渲染 | Parser 适配器 | **两者结合**：Prompt 模板 + Response Parser 适配器 |
| **过滤策略** | Token 压缩 | 行级 diff 过滤 | **两者结合**：Token 预算 + 分析深度策略 |
| **输出层** | 单一输出 | Composite 多路输出 | **Composite 多路输出** |
| **去重/缓存** | 无 | 指纹去重 + 过时清理 | **指纹去重 + Diff 缓存** |
| **配置系统** | Dynaconf 三级覆盖 | YAML 项目文件 | **TOML 全局 + YAML 项目覆盖** |
| **CI 集成** | GitHub Actions 为主 | 多 CI 环境抽象 | **多 CI 支持 + 优雅降级** |
| **错误处理** | Fallback 模型链 | 降级 posting | **双重降级**：模型 fallback + 输出 fallback |
| **扩展性** | 策略模式 (ABC) | 接口模式 (interface) | **接口模式**：更轻量、更 Pythonic |

---

## 四、Reviewdog 模式对 Insightor 的改进点

### 改进 1：引入 Universal Review Format (URF)

**从 reviewdog 学习**：定义明确的中间数据模型是所有可扩展性的基础。

Insightor 的 URF——所有 AI 分析工具输出到此格式：
```json
{
  "meta": {
    "pr_url": "...", "commit_sha": "...", "timestamp": "...",
    "model": "claude-sonnet-4-6", "analysis_depth": "standard"
  },
  "summary": { "pr_type": "feature", "overview": "..." },
  "files": [{"path": "...", "edit_type": "modified", "summary": "...", "risks": 2, "suggestions": 3}],
  "findings": [
    {
      "id": "uuid",
      "type": "risk | suggestion | observation",
      "severity": "critical | high | medium | low | info",
      "category": "security | performance | logic | style | ...",
      "location": {"path": "...", "range": {"start": {"line": 10}, "end": {"line": 15}}},
      "title": "一句话标题",
      "description": "详细描述",
      "suggestion": {"current_code": "...", "suggested_code": "..."},
      "confidence": 0.85,
      "fingerprint": "hash of (type + path + line + title)"
    }
  ],
  "stats": {"total_findings": 10, "risks": 3, "suggestions": 7, "tokens_used": 8000, "duration_ms": 25000}
}
```

**好处**：
- 所有工具（review/describe/risks/improve）输出统一格式
- 方便缓存、去重、增量比较
- 输出格式化与业务逻辑解耦

### 改进 2：Composite Output Service

```python
class OutputService(Protocol):
    def post(self, result: ReviewResult) -> None: ...
    def flush(self) -> None: ...

class CompositeOutput:
    def __init__(self, services: list[OutputService]):
        self.services = services
    def post(self, result):
        for s in self.services:
            s.post(result)  # 同时输出到 CLI + Markdown + GitHub + JSON

# 具体实现
class ConsoleOutput(OutputService): ...      # Rich 美化终端输出
class MarkdownFileOutput(OutputService): ...  # 写入 .md 文件
class GitHubCommentOutput(OutputService): ... # 发布 PR Comment
class JSONOutput(OutputService): ...          # JSON API 响应
```

### 改进 3：Review 结果去重与增量审查

```
首次审查 PR #123 (commit abc123):
  → 完整分析 → 保存结果 + 指纹到缓存

第二次审查同一 PR (commit def456):
  → 获取增量 diff (abc123..def456)
  → 仅分析新变更的文件
  → 保留未变更文件的旧结果
  → 合并为完整 ReviewResult
```

### 改进 4：分析深度策略 (替代简单的 on/off 开关)

```python
class AnalysisDepth(str, Enum):
    QUICK = "quick"       # ~15s: PR 总结 + 仅 CRITICAL 风险
    STANDARD = "standard" # ~30s: 总结 + 风险 + 关键建议（默认）
    DEEP = "deep"         # ~60s: 全部 + 自反思校验 + 代码建议
```

### 改进 5：项目配置文件 `.insightor.yml`

```yaml
# .insightor.yml - 放在仓库根目录
review:
  ignore_patterns: ["*.lock", "*.min.js", "vendor/**", "generated/**"]
  focus_categories: ["security", "performance"]  # 重点关注
  min_severity: medium
  max_suggestions: 20
  extra_instructions: |
    这个项目的数据库使用 PostgreSQL，注意 N+1 查询问题。
    所有 API 端点需要认证检查。

models:
  primary: "claude-sonnet-4-6"
  fallback: ["deepseek-v3", "gpt-4o"]

output:
  formats: ["console", "markdown"]  # 默认输出方式
```

### 改进 6：CI 环境自动检测

```python
@dataclass
class BuildInfo:
    owner: str
    repo: str
    pr_number: int
    commit_sha: str
    branch: str
    ci_system: str  # "github_actions" | "gitlab_ci" | "local" | ...

def detect_build_info() -> BuildInfo:
    # 自动从环境变量检测 CI 环境
    if os.environ.get("GITHUB_ACTIONS"):
        return BuildInfo(...)
    elif os.environ.get("GITLAB_CI"):
        return BuildInfo(...)
    else:
        return BuildInfo(ci_system="local")
```

### 改进 7：更完善的双重降级策略

```
┌─────────────────────────────────────────────────────┐
│               AI 调用降级链                           │
│  Primary Model → Fallback Model → Cached Result     │
│  (Claude)       (DeepSeek)        (上次结果)         │
└─────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│               输出发布降级链                           │
│  GitHub API → Actions Annotation → Console Output   │
│  (行内评论)    (注解)               (终端打印)        │
└─────────────────────────────────────────────────────┘
```

---

## 五、总结：改进后的 Insightor 架构概览

```
用户输入 (PR URL + 命令 + 选项)
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  Layer 0: CI 环境检测 (BuildInfo)                      │
│  · 自动检测 GitHub/GitLab/本地                        │
│  · 加载项目 .insightor.yml 配置                        │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  Layer 1: 入口层 (Entry)                               │
│  · CLI (click) / Web (FastAPI)                        │
│  · 命令分发 + 分析深度策略选择                          │
│  · 配置三级覆盖 (default → .insightor.yml → CLI args) │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  Layer 2: 数据获取层 (Provider)                        │
│  · GitHubProvider / GitLabProvider (策略)              │
│  · Diff 解析 (统一为 FileDiff 模型)                    │
│  · 缓存查询 (PR URL + SHA → 上次结果)                  │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  Layer 3: 数据处理层 (Processing)                      │
│  · 文件过滤 + 语言检测 + 排序                          │
│  · Token 预算管理 + 渐进压缩                           │
│  · 增量 Diff 计算 (vs 缓存基准)                        │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  Layer 4: AI 分析层 (AI Engine)                        │
│  · LiteLLMHandler (多模型 + fallback)                  │
│  · Prompt 模板 (Jinja2)                               │
│  · Response Parser → Universal Review Format (URF)    │
│  · 自反思校验 (deep 模式)                              │
└────────────────────┬─────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────┐
│  Layer 5: 输出层 (Output — Composite Pattern)          │
│  ┌─────────────────────────────────────────────┐     │
│  │ CompositeOutputService                       │     │
│  │  ├── ConsoleOutput (Rich 终端美化)           │     │
│  │  ├── MarkdownFileOutput (.md 文件)           │     │
│  │  ├── GitHubCommentOutput (PR 评论)           │     │
│  │  └── JSONOutput (API 响应 / 缓存存储)        │     │
│  └─────────────────────────────────────────────┘     │
│  · 去重指纹生成 + 过时结果清理                         │
│  · 优雅降级 (API 失败 → 终端输出)                     │
└──────────────────────────────────────────────────────┘
```
