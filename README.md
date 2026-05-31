<div align="center">

# Insightor

**AI-Powered GitHub PR Review Assistant**

一键审查 Pull Request · 自动发现风险 · 生成改进建议 · 人机协同发布

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)

[快速开始](#-快速开始) • [功能特性](#-功能特性) • [使用方式](#-使用方式) • [部署指南](#-部署指南) • [配置说明](#-配置说明)

</div>

---

## 📖 简介

Insightor 是一个基于大语言模型的 GitHub PR 智能审查工具，提供三种使用方式：

- **🖥️ CLI 工具** — 命令行一键审查，生成 Markdown 报告
- **🌐 Web 控制台** — 可视化界面，支持多用户、实时进度、Diff 审查
- **🔌 VSCode 扩展** — IDE 内审查，侧边栏展示结果，一键应用建议

### 核心能力

- ✅ **PR 总结** — 自动生成变更概述、文件走览表、组件交互图
- 🔍 **风险分析** — 识别安全漏洞、性能瓶颈、并发问题、逻辑错误
- 📝 **代码审查** — 详细的代码层面发现，按严重程度分类
- 💡 **改进建议** — 可直接应用的代码 diff，附带置信度评分
- 🤝 **人机协同** — 勾选 checkbox 确认/拒绝建议后一键发布到 GitHub
- 📊 **质量追踪** — 自动记录反馈准确率，持续优化审查质量

---

## 🚀 快速开始

### 方式 1: CLI 工具（本地使用）

```bash
# 1. 安装
git clone https://github.com/SCU-GuGuGaGa/Insightor.git
cd Insightor
pip install -e .

# 2. 配置 API Key
cp .env.example .env
# 编辑 .env，填写至少一个 LLM API Key

# 3. 一键审查
insightor full https://github.com/owner/repo/pull/123
```

### 方式 2: Web 控制台（团队使用）

```bash
# 1. 安装依赖
pip install -e ".[web]"
cd web/frontend && npm install && npm run build && cd ../..

# 2. 启动服务
uvicorn web.backend.app:app --host 0.0.0.0 --port 8000

# 3. 浏览器访问
# http://localhost:8000
# 默认账户: admin / admin123
```

### 方式 3: VSCode 扩展（开发者使用）

1. 安装 CLI: `pip install -e .`
2. 配置 `.env` 文件
3. 安装 `vscode-extension/insightor-vscode-0.1.0.vsix`
4. 按 `Ctrl+Shift+P` → `Insightor: Full Review`

---

## 🎯 功能特性

### CLI 工具

| 命令 | 功能 | 示例 |
|------|------|------|
| `insightor full` | 一键全部分析（总结+风险+审查+建议） | `insightor full <pr_url>` |
| `insightor review` | 代码审查 | `insightor review <pr_url> --depth deep` |
| `insightor describe` | PR 总结 | `insightor describe <pr_url>` |
| `insightor risks` | 风险分析 | `insightor risks <pr_url> --focus security` |
| `insightor improve` | 改进建议 | `insightor improve <pr_url>` |
| `insightor publish` | 发布审查 | `insightor publish report.md` |

**分析深度选项：**

| 深度 | 耗时 | Token | 适用场景 |
|------|------|-------|----------|
| `quick` | ~15s | ~3K | 小改动快速扫描 |
| `standard` | ~30s | ~8K | 标准审查（默认） |
| `deep` | ~60s | ~16K | 关键 PR 深度分析 |

### Web 控制台

- 🔐 **用户系统** — 多用户支持，每个用户独立配置 API Key
- 📋 **PR 管理** — 批量添加 PR，查看历史审查记录
- 📡 **实时进度** — SSE 推送分析进度，无需刷新页面
- 📄 **Diff 审查** — 分文件展示代码变更，支持语法高亮
- 💾 **结果存储** — 审查结果持久化，支持导出 JSON
- 🔒 **安全加密** — API Key 使用 Fernet 加密存储

### VSCode 扩展

- 🌳 **侧边栏视图** — 按严重程度组织发现，点击跳转代码位置
- 📊 **合并就绪评分** — 0-100 分置信度评分
- 🔧 **一键应用** — 直接应用 AI 建议的代码修改
- 🎯 **快捷命令** — `Ctrl+Shift+P` 快速调用所有功能

---

## 💻 使用方式

### CLI 工作流

```bash
# 1. 生成四段式审查报告
insightor full https://github.com/owner/repo/pull/123

# 2. 编辑生成的 Markdown 文件
#    - 勾选 checkbox 确认/拒绝建议
#    - 填写审查者和备注

# 3. 预览将要发布的内容
insightor publish insightor-full-review-123.md --dry-run

# 4. 发布到 GitHub PR
insightor publish insightor-full-review-123.md
```

**生成的报告结构：**

1. **PR 总结** — 变更概述 + 文件走览表 + 组件交互图（可选）
2. **风险分析** — 安全/性能/并发风险 + 合并就绪评分
3. **代码审查** — 详细的代码层面发现
4. **改进建议** — 可勾选的代码 diff + 置信度评分

### Web 控制台工作流

1. **登录** — 使用管理员账户或注册新用户
2. **配置** — 在配置页面填入 GitHub Token 和 LLM API Key
3. **添加 PR** — 输入 PR URL，支持批量添加
4. **发起分析** — 选择分析深度，实时查看进度
5. **查看结果** — 分文件审查 Diff，导出或发布到 GitHub

### VSCode 扩展工作流

1. **打开命令面板** — `Ctrl+Shift+P`
2. **选择命令** — `Insightor: Full Review` / `Review PR` / `Describe PR` 等
3. **输入 PR URL** — 例如 `https://github.com/owner/repo/pull/123`
4. **查看结果** — 侧边栏展示发现，点击跳转代码位置
5. **应用建议** — 右键点击建议，选择 `Apply Fix`

---

## 🚢 部署指南

### 本地开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 启动 Web 控制台（开发模式）
# 终端 1: 后端
uvicorn web.backend.app:app --reload --port 8000

# 终端 2: 前端
cd web/frontend && npm run dev
```

### 远程部署（一键脚本）

适用于 Ubuntu 22.04+ / Debian 12+ 云主机：

```bash
# 1. SSH 连接到云主机
# 2. 克隆仓库
git clone https://github.com/SCU-GuGuGaGa/Insightor.git /tmp/insightor-deploy

# 3. 执行部署脚本
sudo bash /tmp/insightor-deploy/deploy/setup.sh
```

脚本自动完成：
- 创建 `insightor` 用户
- 安装 Miniconda + 创建 conda 环境
- 安装依赖 + 构建前端
- 初始化 SQLite 数据库
- 配置 systemd 服务

**部署后访问：** `http://<服务器IP>:8000`

**管理命令：**

```bash
# 查看状态
systemctl status insightor-api

# 重启服务
systemctl restart insightor-api

# 查看日志
journalctl -u insightor-api -f
```

**HTTPS 配置（需域名）：**

```bash
sudo bash deploy/setup_https.sh insightor.your-domain.com
```

详细部署文档：[deploy/README.md](deploy/README.md)

---

## ⚙️ 配置说明

### 环境变量 (.env)

```bash
# GitHub API Token
GITHUB_TOKEN=ghp_xxx

# LLM API Keys（至少填一个）
OPENAI_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-xxx

# 第三方 API 地址（可选）
OPENAI_API_BASE=https://api.your-proxy.com
ANTHROPIC_BASE_URL=https://api.your-proxy.com
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# 模型配置（可选，覆盖默认值）
INSIGHTOR_MODELS_PRIMARY=claude-sonnet-4-6      # --depth standard
INSIGHTOR_MODELS_WEAK=deepseek-v4-flash         # --depth quick
INSIGHTOR_MODELS_REASONING=claude-opus-4-8      # --depth deep
```

完整配置说明：[.env.example](.env.example)

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

配置示例：[.insightor.example.yml](.insightor.example.yml)


---

## 📁 项目结构

```
Insightor/
├── insightor/              # 核心 Python 包
│   ├── cli.py              # CLI 入口（click）
│   ├── pipeline.py         # 审查管线
│   ├── schemas/urf.py      # Universal Review Format 数据模型
│   ├── config/             # 配置加载（四级覆盖）
│   ├── providers/          # GitHub API 客户端
│   ├── processing/         # Diff 过滤/压缩/缓存
│   ├── ai/                 # LLM 调用 + Prompt 构建 + Response 解析
│   ├── output/             # 终端/Markdown/GitHub/JSON 多路输出
│   └── feedback/           # 反馈解析 + 质量追踪
├── web/                    # Web 控制台
│   ├── backend/            # FastAPI 后端
│   │   ├── app.py          # 应用工厂
│   │   ├── auth.py         # JWT + bcrypt 认证
│   │   ├── database.py     # SQLAlchemy + SQLite
│   │   ├── models.py       # ORM 模型
│   │   ├── encryption.py   # Fernet 加密
│   │   ├── sse_manager.py  # SSE 实时推送
│   │   └── routes/         # API 路由
│   └── frontend/           # React + Vite + Tailwind
│       └── src/
│           ├── components/ # UI 组件
│           ├── pages/      # 页面组件
│           ├── hooks/      # useSSE 等自定义 Hook
│           └── api/        # API 客户端
├── vscode-extension/       # VSCode 扩展
│   ├── src/                # TypeScript 源码
│   ├── package.json        # 扩展清单
│   └── README.md           # 扩展文档
├── deploy/                 # 部署脚本
│   ├── setup.sh            # 一键部署脚本（conda + systemd）
│   ├── setup_https.sh      # HTTPS 配置脚本
│   └── README.md           # 部署文档
├── docs/                   # 项目文档
├── tests/                  # 单元测试
├── .env.example            # 环境变量模板
├── .insightor.example.yml  # 项目配置模板
└── pyproject.toml          # Python 项目配置
```

---

## 🔧 技术栈

### 后端
- **Python 3.11+** — 核心语言
- **Click** — CLI 框架
- **FastAPI** — Web 框架
- **SQLAlchemy** — ORM
- **LiteLLM** — 统一 LLM 调用接口
- **Anthropic SDK** — Claude 原生调用
- **PyGithub** — GitHub API 客户端

### 前端
- **React 18** — UI 框架
- **Vite** — 构建工具
- **Tailwind CSS** — 样式框架
- **TypeScript** — 类型安全

### VSCode 扩展
- **TypeScript** — 扩展开发语言
- **VSCode Extension API** — 扩展接口

---

## 📊 质量追踪

Insightor 自动追踪反馈准确率，数据存储在 `.insightor/quality/`：

- `history.json` — 按类别累积的反馈计数
- `metrics.json` — 预计算的质量指标

每次使用 `insightor publish` 发布审查时，系统会记录：
- 确认的发现（✅ checkbox）
- 拒绝的发现（❌ checkbox）
- 未勾选的发现（跳过）

这些数据用于持续优化审查质量和 Prompt 策略。

---

## 🤝 人机协同工作流

Insightor 的设计理念是 **AI 辅助，人类决策**：

```
┌─────────────────────────────────────────────────────────────┐
│  1. AI 生成审查报告                                          │
│     insightor full <pr_url>                                 │
│     → 生成 insightor-full-review-{pr}.md                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  2. 人类审查 + 编辑                                          │
│     - 阅读 AI 发现，判断是否准确                             │
│     - 勾选 ✅ 确认有价值的发现                               │
│     - 勾选 ❌ 拒绝误报的发现                                 │
│     - 添加自己的评论和建议                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  3. 预览 + 发布                                              │
│     insightor publish <md> --dry-run  # 预览                │
│     insightor publish <md>            # 发布到 GitHub       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  4. 质量追踪                                                 │
│     - 记录确认/拒绝的发现                                    │
│     - 计算准确率指标                                         │
│     - 用于优化未来审查                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌟 支持的 LLM

Insightor 通过 LiteLLM 和原生 SDK 支持多种大语言模型：

| 提供商 | 模型示例 | 配置方式 |
|--------|----------|----------|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini` | `OPENAI_API_KEY` |
| **Anthropic** | `claude-sonnet-4-6`, `claude-opus-4-8` | `ANTHROPIC_API_KEY` |
| **DeepSeek** | `deepseek-v4-pro`, `deepseek-v4-flash` | `DEEPSEEK_API_KEY` |
| **第三方网关** | 兼容 OpenAI/Anthropic 格式 | `*_API_BASE` |

**模型前缀机制：**

- `anthropic/claude-sonnet-4-6` — 使用原生 Anthropic SDK（绕过 LiteLLM）
- `openai/gpt-4o` — 使用 LiteLLM 调用 OpenAI
- `deepseek/deepseek-v4-pro` — 使用 LiteLLM 调用 DeepSeek
- `claude-sonnet-4-6`（无前缀） — 自动根据模型名判断提供商

---

## 📚 文档

- [部署指南](deploy/README.md) — 远程部署、systemd 配置、HTTPS 设置
- [VSCode 扩展文档](vscode-extension/README.md) — 扩展安装、使用、开发
- [Web 控制台文档](web/README.md) — API 接口、架构说明
- [PR 提交规范](docs/pr-submission-guidelines.zh-CN.md) — 贡献指南
- [架构设计](docs/architecture-final.md) — 系统架构说明

---

## 🛠️ 开发

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/ -v
pytest tests/ -v --cov=insightor  # 带覆盖率
```

### 代码风格

```bash
ruff check insightor/
ruff format insightor/
```

### 构建 VSCode 扩展

```bash
cd vscode-extension
npm install
npm run compile
vsce package  # 生成 .vsix 文件
```

---

## 🐛 常见问题

### Q: 提示 "API Key 认证失败"？

**A:** 检查以下几点：
1. `.env` 文件是否在当前目录或项目根目录
2. API Key 是否正确填写（注意前后空格）
3. 第三方 API 网关是否需要配置 `*_API_BASE`
4. 部分供应商的 "CC"（Claude Code）类型 Key 仅限官方 CLI 使用，需换成 "API" 类型

### Q: Web 控制台如何配置 API Key？

**A:** Web 控制台不需要 `.env` 文件，所有配置在 Web UI 中完成：
1. 登录后进入"配置"页面
2. 填入 GitHub Token 和 LLM API Key
3. 配置会加密存储在数据库中，每个用户独立配置

### Q: 如何切换模型？

**A:** 三种方式：
1. **环境变量**：`INSIGHTOR_MODELS_PRIMARY=claude-sonnet-4-6`
2. **命令行参数**：`insightor review <url> --model anthropic/claude-opus-4-8`
3. **配置文件**：在 `.insightor.yml` 中设置 `models.primary`

### Q: 支持私有仓库吗？

**A:** 支持。需要配置有相应权限的 GitHub Token：
- 公开仓库：不需要 Token（但有 API 限流）
- 私有仓库：需要 `repo` 权限的 Personal Access Token

### Q: 如何自定义审查规则？

**A:** 在项目根目录创建 `.insightor.yml`，添加 `review.custom_rules` 和 `review.conventions`。参考 [.insightor.example.yml](.insightor.example.yml)。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

贡献前请阅读：[PR 提交规范](docs/pr-submission-guidelines.zh-CN.md)

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [LiteLLM](https://github.com/BerriAI/litellm) — 统一 LLM 调用接口
- [FastAPI](https://fastapi.tiangolo.com/) — 现代 Python Web 框架
- [React](https://react.dev/) — 用户界面库
- [PyGithub](https://github.com/PyGithub/PyGithub) — GitHub API 客户端

---

<div align="center">

**Made with ❤️ by Insightor Team**

[GitHub](https://github.com/SCU-GuGuGaGa/Insightor) • [Issues](https://github.com/SCU-GuGuGaGa/Insightor/issues)

</div>
