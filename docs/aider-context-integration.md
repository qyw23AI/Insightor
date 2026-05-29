# Aider 上下文处理系统深度分析与 Insightor 集成方案

> 分析 Aider 的 Repo Map、PageRank 排序、Tree-sitter 符号提取、Token 预算管理等核心机制，将其融入 Insightor 的分层上下文管线。

---

## 一、Aider 上下文系统的 5 个核心创新

### 创新 1：基于 Tree-sitter 的符号级代码图谱

Aider 不依赖语言服务器或编译——仅用 tree-sitter 的 `.scm` query 文件就能从 50+ 语言的源码中提取符号定义和引用关系。

```
源码文件 → tree-sitter parse → AST → .scm query → Tags
                                                    │
                                          ┌─────────┴─────────┐
                                          │ kind="def"  (定义) │
                                          │ kind="ref"  (引用) │
                                          └───────────────────┘
```

每个 Tag 仅 5 个字段：
```python
Tag(rel_fname="src/auth.py", fname="/abs/path/src/auth.py", line=23, name="login", kind="def")
```

**对 Insightor 的启发**：
- Layer 4 (RelatedFileSource)：从 PR diff 中提取被修改的符号 → 在整个仓库中查找引用者 → 找到真正的关联文件
- Layer 5 (RepoAnalysisSource)：对整个仓库构建符号图谱 → 识别变更的影响范围

---

### 创新 2：带个性化加权的 PageRank 排序

这是 Aider 上下文系统的核心算法：

```
Step 1: 构建依赖图
  · 节点 = 文件
  · 有向边 A→B = 文件 A 引用了文件 B 中定义的符号
  · 边权重 = 引用频率 + 加权乘数

Step 2: 个性化 PageRank
  · personalization = {chat_files: 高权重, mentioned_files: 中权重, others: 低权重}
  · PageRank 算法在图中传播权重
  · 结果：与 PR 变更最相关的文件获得最高分

Step 3: 权重乘数
  · 被 PR 文件引用的符号 → 50x
  · 复合名称 (snake/camel/kebab, ≥8字符) → 10x
  · 私有符号 (_开头) → 0.1x  (降低噪音)
  · 泛用符号 (>5文件定义) → 0.1x  (如 get/set/init)
```

**对 Insightor 的启发**：
这是 **Layer 4 的核心算法**。相比我们之前简单的 "git grep 查找调用方"，PageRank 能给出**全局相关性排序**，并自动降权噪音符号。

---

### 创新 3：Token 预算约束的二分搜索选择

Aider 不是简单地截断排名列表——它使用二分搜索找到能放入 token 预算的**最大符号集合**：

```python
lower_bound = 0
upper_bound = num_tags
middle = min(int(max_map_tokens // 25), num_tags)  # 初始猜测：每个 tag ~25 tokens

while lower_bound <= upper_bound:
    text = render_tags(tags[:middle])
    tokens = token_count(text)
    if abs(tokens - max_tokens) / max_tokens < 0.15:  # 15% 误差内接受
        return text
    elif tokens > max_tokens:
        upper_bound = middle - 1
    else:
        lower_bound = middle + 1
    middle = (lower_bound + upper_bound) // 2
```

**对 Insightor 的启发**：
直接用于 `ContextAssembler`——在 diff 压缩后剩余多少 token 预算，就用二分搜索决定能放入多少关联文件/符号。

---

### 创新 4：紧凑的 Tree View 渲染

Aider 不把整个关联文件放入上下文——它使用 `grep_ast.TreeContext` 只显示符号周围的骨架代码：

```
# 传统方式（浪费 token）：
Related file: src/services/user_service.py
[整个文件 200 行代码...]

# Aider 的 Tree View（紧凑）：
src/services/user_service.py:
│class UserService:
│    def create_user(self, username, password):
│        ...
│    def validate_credentials(self, token):
│        ...
│    def find_by_email(self, email):
        ...
```

每个符号只展开周围几行上下文，用 `...` 省略不相关的代码。truncate 长行（>100 字符）。

**对 Insightor 的启发**：
Layer 4/5 的关联文件不应该发完整内容给 LLM——用 Tree View 只展示相关的符号骨架，大幅节省 token。

---

### 创新 5：mtime 驱动的增量标签缓存

```python
# 缓存结构
TAGS_CACHE = {
    "/abs/path/src/auth.py": {
        "mtime": 1717000000,
        "data": [Tag(...), Tag(...), ...]
    }
}

# 查询时
def get_tags(fname):
    cached = TAGS_CACHE.get(fname)
    if cached and cached["mtime"] == os.path.getmtime(fname):
        return cached["data"]  # 缓存命中
    tags = parse_with_tree_sitter(fname)
    TAGS_CACHE[fname] = {"mtime": current_mtime, "data": tags}
    return tags
```

使用 `diskcache`（SQLite-backed）持久化到 `.aider.tags.cache.v{version}/`。

**对 Insightor 的启发**：
- PR 文件每次 push 都变 → 总是重新解析（mtime 已变）
- 仓库其他文件不变 → 缓存命中，无需重新解析
- 跨 PR 审查共享缓存（同一仓库的不同 PR）

---

## 二、Aider → Insightor 架构映射

```
Aider 概念                  →  Insightor 组件                    →  所在层
─────────────────────────────────────────────────────────────────────────
Tag (符号标签)               →  SymbolTag dataclass              →  Layer 4/5
Tag 提取 (tree-sitter)       →  SymbolExtractor                 →  Layer 4/5
依赖图 (MultiDiGraph)        →  DependencyGraph                 →  Layer 4/5
个性化 PageRank              →  RelevanceRanker                 →  Layer 4
Token 二分搜索                →  BudgetFitter                    →  ContextAssembler
Tree View 渲染               →  CompactCodeRenderer             →  ContextAssembler
mtime 缓存                   →  TagCache                        →  Layer 4/5
ChatChunks 分层消息           →  AssembledContext (已有)          →  ContextPipeline
Map tokens 预算               →  ContextPipeline.allocate_budget  →  ContextPipeline
```

---

## 三、Insightor 上下文管线的新架构

### 改进后的 ContextSource 体系

```
ContextPipeline
    │
    ├── Layer 1: DiffContextSource (已有，不变)
    │   内容: PR diff + description + commits
    │   成本: 0 API 调用
    │
    ├── Layer 2: FileContextSource (已有，不变)
    │   内容: patch ±N 行 + import 解析
    │   成本: 0 API 调用
    │
    ├── Layer 3: IssueContextSource (已有，不变)
    │   内容: GitHub Issues API → issue 标题/描述
    │   成本: 1 API 调用
    │
    ├── Layer 4: RelatedFileSource (★ Aider 启发，重写)
    │   ┌─────────────────────────────────────────────────┐
    │   │ ★ SymbolExtractor (tree-sitter)                  │
    │   │   从 PR diff 文件中提取所有被修改的符号 (Tag)     │
    │   │                                                   │
    │   │ ★ GlobalTagCache (mtime 驱动)                     │
    │   │   缓存仓库其余文件的 Tag，只重新解析变更的文件     │
    │   │                                                   │
    │   │ ★ DependencyGraph (networkx.MultiDiGraph)         │
    │   │   文件→文件的有向边：引用方 → 定义方               │
    │   │                                                   │
    │   │ ★ RelevanceRanker (个性化 PageRank)               │
    │   │   personalization = PR diff 文件高权重            │
    │   │   权重乘数: PR 引用 50x, 复合名 10x, 私有 0.1x    │
    │   │                                                   │
    │   │ ★ BudgetFitter (二分搜索)                         │
    │   │   在剩余 token 预算内选择最大排名符号集合          │
    │   │                                                   │
    │   │ ★ CompactCodeRenderer (Tree View)                 │
    │   │   将选中的符号渲染为紧凑骨架视图                   │
    │   └─────────────────────────────────────────────────┘
    │   内容: 排名 top-N 的关联文件骨架
    │   成本: 0 API 调用 (纯本地计算)
    │
    └── Layer 5: RepoAnalysisSource (★ Aider 启发，重写)
        ┌─────────────────────────────────────────────────┐
        │ ★ 全仓库 Tag 提取 (tree-sitter)                  │
        │   对仓库所有文件 (非 diff) 提取符号              │
        │                                                   │
        │ ★ 全局依赖图构建                                  │
        │   包含所有文件的符号引用关系                      │
        │                                                   │
        │ ★ 影响范围分析                                    │
        │   从 PR 变更的符号出发，沿依赖图传播              │
        │   识别所有直接/间接受影响的文件                   │
        │                                                   │
        │ ★ 仓库结构摘要                                    │
        │   按目录/包聚合，给 LLM 一个仓库全景视图          │
        └─────────────────────────────────────────────────┘
        内容: 仓库结构地图 + 变更影响范围报告
        成本: git clone (已有) + tree-sitter parse (首次~30s，后续缓存命中~1s)
```

### 新的数据结构

```python
# ===== SymbolTag — 来自 Aider 的 Tag namedtuple =====
@dataclass 
class SymbolTag:
    fname: str          # 文件绝对路径
    rel_fname: str      # 相对路径
    line: int           # 行号
    name: str           # 符号名
    kind: str           # "def" (定义) | "ref" (引用)

# ===== DependencyGraph — 来自 Aider 的 MultiDiGraph =====
class DependencyGraph:
    """文件级符号依赖图"""
    def __init__(self):
        self.graph = nx.MultiDiGraph()  # 节点=文件, 边=符号引用
        self.defines: dict[str, set[str]]     # 符号名 → {定义它的文件}
        self.references: dict[str, list[tuple[str, int]]]  # 符号名 → [(引用文件, 引用次数)]

    def add_tags(self, tags: list[SymbolTag]) -> None: ...
    def build_edges(self) -> None: ...
    def get_callers(self, symbol: str) -> list[str]: ...
    def get_callees(self, symbol: str) -> list[str]: ...

# ===== RelevanceRanker — 来自 Aider 的 PageRank =====
class RelevanceRanker:
    """基于个性化 PageRank 的文件相关性排序"""
    def __init__(self, graph: DependencyGraph):
        self.graph = graph

    def rank(
        self,
        pr_files: set[str],                    # PR diff 中的文件 (personalization)
        mentioned_idents: set[str] = set(),    # 用户/PR 描述中提到的标识符
        mentioned_fnames: set[str] = set(),    # 用户/PR 描述中提到的文件名
        dependency_map: dict[str, list[str]] = {},  # .insightor.yml 的依赖映射
    ) -> list[tuple[str, str, float]]:         # [(fname, symbol, score), ...]
        """
        权重乘数：
        - PR 文件引用的符号 → 50x
        - mentioned_idents → 10x
        - 复合名称 (snake/camel, ≥8字符) → 10x
        - 私有符号 (_开头) → 0.1x
        - 泛用符号 (>5文件定义) → 0.1x
        - dependency_map 中的关联 → 20x
        """

# ===== BudgetFitter — 来自 Aider 的二分搜索 =====
class BudgetFitter:
    """在 token 预算内选择最优符号集合"""
    def fit(
        self,
        ranked_items: list[tuple[str, str, float]],  # (fname, symbol, score)
        token_budget: int,
        renderer: "CompactCodeRenderer",
    ) -> str:  # 返回紧凑渲染后的文本
        """二分搜索找到恰好 fit 进 budget 的最大集合"""
        ...

# ===== CompactCodeRenderer — 来自 Aider 的 Tree View =====
class CompactCodeRenderer:
    """将符号列表渲染为紧凑骨架视图"""
    def render(self, items: list[tuple[str, str, float]]) -> str:
        """
        输出格式:
        src/services/user_service.py:
        │class UserService:
        │    def create_user(self, username, password):
        │        ...
        │    def validate_credentials(self, token):
            ...
        """
    def render_symbol(self, fname: str, symbol: str, context_lines: int = 3) -> str: ...

# ===== TagCache — 来自 Aider 的 diskcache =====
class TagCache:
    """mtime 驱动的标签缓存"""
    def __init__(self, repo_path: str):
        self.cache_dir = Path(repo_path) / ".insightor" / "tags_cache"
        self.memory_cache: dict[str, dict] = {}  # {fname: {mtime, tags}}

    def get(self, fname: str) -> list[SymbolTag] | None: ...
    def put(self, fname: str, tags: list[SymbolTag]) -> None: ...
    def invalidate(self, fname: str) -> None: ...

# ===== 改进后的 RelatedFileSource =====
class RelatedFileSource(ContextSource):
    name = "related_files"
    layer = 4

    def __init__(self, provider: GitProvider, tag_cache: TagCache):
        self.provider = provider
        self.tag_cache = tag_cache
        self.extractor = SymbolExtractor()          # tree-sitter
        self.graph = DependencyGraph()
        self.ranker = RelevanceRanker(self.graph)
        self.fitter = BudgetFitter()
        self.renderer = CompactCodeRenderer()

    async def fetch(self, pr_info: PRInfo, pr_files: list[FilePatchInfo]) -> ContextChunk:
        # Step 1: 从 PR diff 文件提取修改的符号
        modified_symbols = self.extractor.extract_from_diff(pr_files)

        # Step 2: 对仓库其他文件获取/更新 Tag 缓存
        all_tags = []
        for fname in self._get_repo_files():
            tags = self.tag_cache.get(fname)
            if tags is None:
                tags = self.extractor.extract_file(fname)
                self.tag_cache.put(fname, tags)
            all_tags.extend(tags)

        # Step 3: 构建依赖图
        self.graph.clear()
        self.graph.add_tags(all_tags)

        # Step 4: PageRank 排序
        ranked = self.ranker.rank(
            pr_files={f.filename for f in pr_files},
            mentioned_idents=self._extract_idents(pr_info.description),
            dependency_map=config.get_dependency_map(),
        )

        # Step 5: Token 预算内选择 + 紧凑渲染
        rendered = self.fitter.fit(ranked, self.token_budget, self.renderer)

        return ContextChunk(
            source_name="related_files",
            content=rendered,
            metadata={
                "symbols_extracted": len(all_tags),
                "related_files_ranked": len(ranked),
                "hit_cache": self.tag_cache.hit_rate,
            }
        )
```

---

## 四、Insightor 上下文管线的新工作流

```
PR URL → Pipeline.start()
    │
    ▼
Step 1: 获取 PR diff (Layer 1)
    │  输出: diff_text, pr_info, files
    │
    ▼
Step 2: 文件级上下文扩展 (Layer 2)
    │  输出: extended_diff (with ±N lines, imports)
    │
    ▼
Step 3: Token 估算
    │  diff_tokens = estimate(extended_diff)
    │  available_budget = model_max_tokens - diff_tokens - output_buffer
    │
    ▼
Step 4: Issue 上下文 (Layer 3, 如果 budget > 2000)
    │  issue_text = fetch_issues(pr_info.description)
    │  budget -= tokens(issue_text)
    │
    ▼
Step 5: 关联文件发现 (Layer 4, ★ Aider 算法, 如果 budget > 3000)
    │  5a. tree-sitter 提取 PR diff 中的被修改符号
    │  5b. 从缓存/解析获取仓库其余文件的符号
    │  5c. 构建依赖图 (nx.MultiDiGraph)
    │  5d. PageRank with personalization (PR files=高权重)
    │  5e. 二分搜索 → 在 budget 内选 top-N 符号
    │  5f. Compact Tree View 渲染
    │  budget -= tokens(related_files_text)
    │
    ▼
Step 6: 仓库结构摘要 (Layer 5, ★ Aider 启发, deep only, 如果 budget > 4000)
    │  6a. 全仓库 Tag 汇总 (从缓存读取, ~1s)
    │  6b. 按目录聚合 → "src/auth/ 定义了 12 个类, 被 src/api/ 和 tests/ 引用"
    │  6c. 影响范围: "修改 login() 将影响 src/api/handlers.py 的 authenticate()"
    │  budget -= tokens(repo_summary)
    │
    ▼
Step 7: Diff 压缩 (如果仍有 token 压力)
    │  compressed_diff = compress(extended_diff, remaining_budget)
    │
    ▼
Step 8: Prompt 组装
    │  system_prompt + context_section + diff_section + user_prompt
    │
    ▼
Step 9: AI 调用 → 流式解析 → URF
```

### Token 预算分配策略

```
模型上下文窗口 128K tokens (e.g., Claude Sonnet 4):

┌──────────────────────────────────────────────────────────────┐
│ System Prompt          │  1.5K  │ 静态 (prompt 模板)          │
│ Output Buffer          │  4.0K  │ 预留给 AI 响应               │
│ ───────────────────────┼────────┼─────────────────────────── │
│ 可用预算               │122.5K  │                             │
│ ───────────────────────┼────────┼─────────────────────────── │
│ Layer 1: PR Diff       │ 30.0K  │ 动态 (随 PR 大小变化)       │
│ Layer 2: 上下文扩展     │  5.0K  │ (diff 的一部分)             │
│ Layer 3: Issue Context  │  2.0K  │ 有则取                      │
│ Layer 4: Related Files  │ 15.0K  │ ★ Aider 算法 (标准+深度)    │
│ Layer 5: Repo Summary   │ 10.0K  │ ★ Aider 启发 (仅深度)      │
│ ───────────────────────┼────────┼─────────────────────────── │
│ 剩余 (给 AI 分析余量)   │ 60.5K  │ 充足的思考空间               │
└──────────────────────────────────────────────────────────────┘
```

### 不同分析深度的上下文策略

| | quick | standard | deep |
|---|-------|----------|------|
| Layer 1 (Diff) | ✅ | ✅ | ✅ |
| Layer 2 (File Context) | ✅ (±1行) | ✅ (±3行) | ✅ (±5行) |
| Layer 3 (Issues) | | ✅ | ✅ |
| Layer 4 (Related Files) | | ★ PageRank (10 files max) | ★ PageRank (20 files max) |
| Layer 5 (Repo Summary) | | | ★ 全仓库影响分析 |
| 预估上下文占比 | ~40% 窗口 | ~60% 窗口 | ~80% 窗口 |

---

## 五、对 Insightor 项目的影响

### 新增依赖

```toml
# pyproject.toml 新增
[project]
dependencies = [
    # ... 现有 ...
    "tree-sitter>=0.23",       # ★ 符号提取
    "networkx>=3.0",           # ★ 依赖图 + PageRank
    "diskcache>=5.0",          # ★ Tag 缓存持久化
]
```

### 新增/修改的模块

```
insightor/
├── processing/
│   ├── context/
│   │   ├── __init__.py
│   │   ├── pipeline.py          # ContextPipeline (已有)
│   │   ├── sources/
│   │   │   ├── diff.py          # Layer 1 (已有)
│   │   │   ├── file_context.py  # Layer 2 (已有)
│   │   │   ├── issues.py        # Layer 3 (已有)
│   │   │   ├── related_files.py # Layer 4 (★ 重写：Aider PageRank)
│   │   │   └── repo_analysis.py # Layer 5 (★ 重写：Aider Repo Map)
│   │   ├── symbols.py           # ★ 新增：SymbolTag, SymbolExtractor
│   │   ├── depgraph.py          # ★ 新增：DependencyGraph
│   │   ├── ranker.py            # ★ 新增：RelevanceRanker (PageRank)
│   │   ├── budget.py            # ★ 新增：BudgetFitter (二分搜索)
│   │   ├── renderer.py          # ★ 新增：CompactCodeRenderer (Tree View)
│   │   └── tag_cache.py         # ★ 新增：TagCache (diskcache + mtime)
│   └── ...
```

### 对 PR 拆分的影响

| PR | 变更类型 | 说明 |
|----|---------|------|
| **PR #3** | **scope 扩展** | Diff 处理管线 → 新增 context/ 子包 (symbols, depgraph, tag_cache) |
| **PR #3** | **新增模块** | SymbolExtractor (tree-sitter tag 提取), TagCache (diskcache) |
| **PR #6** | **scope 扩展** | 核心管线 → 新增 PageRank 排序步骤 (来自 Aider) |
| **PR #6** | **新模块** | RelevanceRanker, BudgetFitter, CompactCodeRenderer |

**不增加 PR 总数**（保持 13 个），但 PR #3 和 PR #6 的实现内容更丰富。

---

## 六、Aider 上下文系统对 Insightor 的核心价值总结

| Aider 创新 | Insightor 直接收益 | 提升维度 |
|-----------|-------------------|---------|
| tree-sitter 符号提取 | 精确识别关联文件（不依赖 git grep 关键词匹配） | **上下文理解准确度** |
| 个性化 PageRank | 全局相关性排序（不只是"引用到了"，而是"有多相关"） | **上下文理解准确度** |
| 权重乘数 (50x/10x/0.1x) | 降低噪音符号干扰（get/set/init 自动降权） | **误报控制** |
| 二分搜索 Token 适配 | 在 budget 内最大化有用上下文 | **响应速度 + 准确度** |
| compact Tree View | 关联文件骨架而非全文，同样 token 能放更多文件 | **上下文广度** |
| mtime 缓存 | 仓库 99% 的文件不需要每次解析（只解析 diff 文件） | **响应速度** |
| diskcache 持久化 | 跨 PR/跨审查共享符号索引 | **响应速度** |
