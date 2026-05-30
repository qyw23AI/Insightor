# Insightor

AI-powered PR review assistant — 一键审查 GitHub Pull Request，自动发现风险、生成改进建议、人机协同发布。

## 快速开始

```bash
# 1. 安装
git clone https://github.com/SCU-GuGuGaGa/Insightor.git
cd Insightor
pip install -e .

# 2. 配置 LLM API Key
cp .env.example .env
# 编辑 .env，填写 API Key

# 3. 一键审查
insightor full https://github.com/owner/repo/pull/123 --depth standard
```

## 环境要求

- Python 3.11+
- Git
- LLM API Key（支持 OpenAI / DeepSeek / Claude 等兼容 litellm 的模型）

## 配置

### 环境变量 (.env)

```bash
OPENAI_API_KEY=sk-xxx        # OpenAI API Key
DEEPSEEK_API_KEY=sk-xxx      # DeepSeek API Key（可选）
ANTHROPIC_API_KEY=sk-xxx     # Claude API Key（可选）
```

### 项目配置 (.insightor.yml)

在仓库根目录创建 `.insightor.yml` 进行项目级定制：

```yaml
review:
  custom_rules: |
    1. 所有 /api/ 路由处理器必须有 @require_auth 装饰器
    2. 数据库查询必须使用参数化查询，禁止字符串拼接 SQL

  conventions: |
    - 使用 async/await 而非回调
    - 错误消息使用中文

  safe_patterns:
    - "logger\\.debug\\(.*password.*\\)"

  focus_categories: ["security", "performance"]
  min_severity: medium
  max_suggestions: 15

context:
  dependency_map:
    "src/models/": ["src/services/", "src/api/", "tests/"]
    "src/middleware/": ["src/api/", "tests/"]
```

## CLI 命令

### `insightor full` — 一键全部分析

```bash
insightor full https://github.com/owner/repo/pull/123
insightor full <url> --depth deep           # 深度分析
insightor full <url> --skip review          # 跳过代码审查
insightor full <url> --debug                # 调试模式：打印中间数据
```

生成 `insightor-full-review-{pr}.md` 四段式报告：

1. **PR 总结** — 变更概述 + 文件走览表
2. **风险分析** — 安全/性能/并发风险发现
3. **代码审查** — 详细的代码层面发现
4. **代码建议** — 可勾选的改进建议 + 代码 diff

### `insightor review` — 代码审查

```bash
insightor review https://github.com/owner/repo/pull/123
insightor review <url> --depth quick        # 快速模式
insightor review <url> --depth deep         # 深度模式
insightor review <url> --incremental        # 增量审查（仅分析新 commit）
insightor review <url> --debug              # 调试模式
```

### `insightor describe` — PR 总结

```bash
insightor describe https://github.com/owner/repo/pull/123
insightor describe <url> --depth quick
```

自动生成：PR 类型分类、一句话概述、逐文件变更说明、可选 Mermaid 组件交互图。

### `insightor risks` — 风险分析

```bash
insightor risks https://github.com/owner/repo/pull/123
insightor risks <url> --focus security      # 聚焦安全风险
insightor risks <url> --focus performance   # 聚焦性能风险
```

自动识别：安全漏洞、并发问题、性能瓶颈、逻辑错误、数据丢失风险。附带合并就绪评分（0-100）。

### `insightor improve` — 代码建议

```bash
insightor improve https://github.com/owner/repo/pull/123
insightor improve <url> --committable-only  # 仅显示可直接应用的建议
```

每个建议提供：当前代码 vs 建议代码对比、置信度评分、是否可直接提交。

### `insightor publish` — 发布审查

```bash
# 编辑 Markdown 报告中的 checkbox 后发布
insightor publish insightor-review-123.md

# 预览（不实际发布）
insightor publish insightor-review-123.md --dry-run
```

自动从 Markdown 检测 PR URL，仅发布带反馈的发现。Full 报告只发布代码建议部分。

## 人机协同工作流

```
insightor full <url>           # AI 生成四段式审查报告
       ↓
编辑 insightor-full-review-{pr}.md
  - 勾选 checkbox 确认/拒绝建议
  - 填写审查者和备注
       ↓
insightor publish <md> --dry-run  # 预览将要发布的内容
insightor publish <md>            # 发布到 GitHub PR
```

## 分析深度

| 深度 | 耗时 | Token | 说明 |
|------|------|-------|------|
| `quick` | ~15s | ~3K | 快速扫描，适合小改动 |
| `standard` | ~30s | ~8K | 标准审查（默认） |
| `deep` | ~60s | ~16K | 深度分析，适合关键 PR |

## 项目结构

```
insightor/
├── cli.py              # CLI 入口（click）
├── pipeline.py          # 核心审查管线
├── schemas/urf.py       # Universal Review Format 数据模型
├── config/              # 配置加载（四级覆盖）
├── environment/         # CI 环境检测
├── providers/           # GitHub API 客户端
├── processing/          # Diff 过滤/压缩/缓存
├── ai/                  # LLM 调用 + Prompt 构建 + Response 解析
├── output/              # 终端/Markdown/GitHub/JSON 多路输出
└── feedback/            # 反馈解析 + 质量追踪
```

## 质量追踪

Insightor 自动追踪反馈准确率，数据存储在 `.insightor/quality/`：

- `history.json` — 按类别累积的反馈计数
- `metrics.json` — 预计算的质量指标

## 开发

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
