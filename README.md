# Insightor

<div align="center">

![Insightor Logo](resources/icon.png)

**AI 驱动的 GitHub PR 审查助手 **

[![VSCode](https://img.shields.io/badge/VSCode-1.85+-blue.svg)](https://code.visualstudio.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[快速开始](#-快速开始三步搞定) • [功能特性](#-功能特性) • [安装指南](#-详细安装) • [使用方法](#-使用方法) • [配置说明](#️-配置说明)

</div>

---

## 🚀 快速开始
待补充：快速开始内容
<!-- 待补充：快速开始内容 -->

---

## 🎯 产品概述

Insightor将 AI 驱动的代码审查能力直接集成到网页或是您的vscode编辑器中。分析 GitHub Pull Request、识别风险、生成描述、发布审查——全部自动化。

### Insightor 提供三种使用方式


- **Web 控制台** — 可视化界面，支持多用户、实时进度、Diff 审查
- **VSCode 扩展**（本扩展）— IDE 内审查，侧边栏展示结果，一键应用建议
- **CLI 工具** — 命令行一键审查，生成 Markdown 报告


### 为什么选择 Insightor？

- **AI 智能分析** — 利用大语言模型（OpenAI、DeepSeek、Claude）进行智能代码审查
- **多维度审查** — 代码质量、安全风险、性能问题等全方位分析
- **可视化树状视图** — 侧边栏按严重程度组织发现，一目了然
- **快速修复** — 一键应用 AI 建议的代码修改
- **合并就绪评分** — 0-100 分置信度评分，辅助决策
- **人机协同** — 审查并确认 AI 发现后再发布


## ✨ 功能特性

### 核心命令

| 命令 | 功能说明 | 快捷键 |
|------|----------|--------|
| **Full Review** | 完整分析（总结 + 风险 + 审查） | - |
| **Review PR** | 详细代码审查和建议 | - |
| **Describe PR** | 生成 PR 描述和文件走览 | - |
| **Analyze Risks** | 识别安全、性能、并发风险 | - |
| **Publish Review** | 发布人工确认的审查到 GitHub | - |

### 侧边栏视图

- **按严重程度分类** — Critical、High、Medium、Low、Info
- **合并就绪评分** — 0-100 分置信度评分
- **文件走览** — 查看所有变更文件及摘要
- **点击跳转** — 直接跳转到代码位置
- **应用修复** — 一键应用代码建议

### 分析深度

| 深度 | 耗时 | Token | 适用场景 |
|------|------|-------|----------|
| **Quick** | ~15s | ~3K | 小型 PR，快速检查 |
| **Standard** | ~30s | ~8K | 大多数 PR（默认） |
| **Deep** | ~60s | ~16K | 关键变更，复杂逻辑 |

## 📦 详细安装



### 方式一：安装 Insightor CLI

**方式 A：从 PyPI 安装（推荐）**
```bash
pip install git+https://github.com/SCU-GuGuGaGa/Insightor.git
```

**方式 B：从源码安装**
```bash
git clone https://github.com/SCU-GuGuGaGa/Insightor.git
cd Insightor
pip install -e .
```

**验证安装：**
```bash
python -m insightor --version
# 应输出：insightor 0.1.0
```

### 配置 API Key

在**项目根目录**创建 `.env` 文件（审查 PR 的项目目录）：

```bash
# 选择一个提供商：
OPENAI_API_KEY=sk-proj-xxxxx           # OpenAI GPT-4
DEEPSEEK_API_KEY=sk-xxxxx              # DeepSeek（更便宜）
ANTHROPIC_API_KEY=sk-ant-xxxxx         # Claude
```

💡 **提示**：也可以全局设置环境变量，或使用 `.insightor.yml` 进行项目级配置。

### 方式二：安装 VSCode 扩展

**方式 A：从 VSIX 安装（推荐）**

1. 下载 `insightor-vscode-0.1.1.vsix`
2. 打开 VSCode → 扩展（`Ctrl+Shift+X`）
3. 点击 `...` 菜单 → `从 VSIX 安装...`
4. 选择下载的文件

**方式 B：从VSCode扩展市场安装**  
1. 打开 VSCode → 扩展（`Ctrl+Shift+X`）
2. 搜索 Insightor，选择并下载



## 🚀 使用方法

### Web 控制台使用

如果你需要团队协作、多用户管理或可视化界面，推荐使用 Web 控制台：

**安装和启动：**

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

**使用流程：**

1. **登录** — 使用管理员账户或注册新用户
2. **配置** — 在配置页面填入 GitHub Token 和 LLM API Key（每个用户独立配置）
3. **添加 PR** — 输入 PR URL，支持批量添加
4. **发起分析** — 选择分析深度，实时查看 SSE 推送的进度
5. **查看结果** — 分文件审查 Diff，支持语法高亮，导出或发布到 GitHub

**Web 控制台特性：**

- **多用户系统** — 每个用户独立配置 API Key，加密存储
- **实时进度** — SSE 推送分析进度，无需刷新页面
- **可视化 Diff** — 分文件展示代码变更，支持语法高亮
- **结果持久化** — 审查结果存储在数据库，支持导出 JSON
- **PR 管理** — 查看历史审查记录，批量管理 PR

详细文档：[Web 控制台文档](../web/README.md)

### VSCode 扩展使用

**1️⃣ 打开命令面板**
- 按 `Ctrl+Shift+P`（Windows/Linux）或 `Cmd+Shift+P`（Mac）

**2️⃣ 选择命令**
- `Insightor: Full Review` - 完整分析（首次使用推荐）
- `Insightor: Review PR` - 仅代码审查
- `Insightor: Describe PR` - 生成 PR 描述
- `Insightor: Analyze Risks` - 安全和性能风险
- `Insightor: Publish Review` - 发布结果到 GitHub

**3️⃣ 输入 PR URL**
```
https://github.com/owner/repo/pull/123
```

**4️⃣ 选择分析深度**
- `quick` - 15 秒，小型 PR
- `standard` - 30 秒，大多数 PR（默认）
- `deep` - 60 秒，关键变更

**5️⃣ 查看结果**
- **侧边栏**：点击活动栏（左侧）的 Insightor 图标
- **Markdown**：自动在编辑器中打开完整报告
- **点击发现**：直接跳转到代码位置

### CLI 工具使用

如果你更喜欢命令行，也可以直接使用 CLI：

```bash
# 一键完整审查
insightor full https://github.com/owner/repo/pull/123

# 生成 Markdown 报告后编辑并发布
insightor publish insightor-full-review-123.md
```

### 工作流示例（VSCode 扩展）

```
┌─────────────────────────────────────┐
│ 1. 运行完整审查                      │
│    输入：PR URL                      │
│    深度：standard                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. AI 分析                          │
│    - 描述 PR                        │
│    - 识别风险                        │
│    - 审查代码                        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. 查看结果                          │
│    - 侧边栏树状视图                  │
│    - Markdown 报告                   │
│    - 点击发现 → 跳转到代码           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. 人工审查                          │
│    - 编辑 Markdown                   │
│    - 勾选/取消勾选发现               │
│    - 添加评论                        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. 发布到 GitHub                     │
│    命令：Publish Review              │
│    选项：预览或正式发布              │
└─────────────────────────────────────┘
```

### 侧边栏导航

```
Insightor
├── 📋 PR 总结
│   └── 概述文本
├── ✅ 评分：85/100
├── 🔴 CRITICAL (2)
│   ├── SQL 注入漏洞
│   └── 未验证的用户输入
├── 🟡 HIGH (5)
│   ├── 缓存中的竞态条件
│   └── ...
├── 🔵 MEDIUM (8)
├── ⚪ LOW (3)
└── 📁 变更文件 (12)
    ├── [modified] src/api/users.py
    └── ...
```

## ⚙️ 配置说明

### VSCode 设置

打开设置（`Ctrl+,`）并搜索 "insightor"：

```json
{
  "insightor.pythonPath": "python",
  "insightor.defaultDepth": "standard",
  "insightor.model": "",
  "insightor.autoOpenResults": true,
  "insightor.showNotifications": true
}
```

### 项目配置

在仓库根目录创建 `.insightor.yml`：

```yaml
review:
  custom_rules: |
    1. 所有 API 路由必须有身份验证
    2. 使用参数化查询，禁止字符串拼接 SQL
  
  conventions: |
    - 使用 async/await 而非回调
    - 错误消息使用中文
  
  focus_categories: ["security", "performance"]
  min_severity: medium
  max_suggestions: 15
```

### 自定义快捷键

添加到 `keybindings.json`：

```json
[
  { "key": "ctrl+alt+r", "command": "insightor.reviewPR" },
  { "key": "ctrl+alt+f", "command": "insightor.fullReview" },
  { "key": "ctrl+alt+p", "command": "insightor.publishReview" }
]
```

## 🔧 故障排查

### ❌ "Insightor CLI not found"（找不到 Insightor CLI）

**检查 CLI 安装：**
```bash
python -m insightor --version
```

**如果命令失败：**
```bash
pip install git+https://github.com/SCU-GuGuGaGa/Insightor.git
```

**如果使用虚拟环境：**
- 在 VSCode 设置中设置 `insightor.pythonPath` 为虚拟环境的 Python 路径
- 示例：`/path/to/venv/bin/python` 或 `C:\path\to\venv\Scripts\python.exe`

### ❌ "Review failed"（审查失败）或 API 错误

**检查 API Key：**
1. 确认 `.env` 文件存在于项目根目录
2. 检查 Key 格式：`OPENAI_API_KEY=sk-proj-xxxxx`（无引号，无空格）
3. 手动测试：
   ```bash
   cd your-project
   python -m insightor review https://github.com/owner/repo/pull/123
   ```

**检查网络：**
- 确保可以访问 OpenAI/DeepSeek/Anthropic API
- 检查防火墙/代理设置

### ❌ 没有显示结果

1. **确保工作区文件夹已打开**（文件 → 打开文件夹）
2. **检查输出面板**：视图 → 输出 → 选择 "Insightor"
3. **确认命令已完成**：查找 "Analysis complete" 通知

### 🐛 调试模式

**查看详细日志：**
1. 视图 → 输出（`Ctrl+Shift+U`）
2. 从下拉菜单选择 "Insightor"
3. 检查错误消息

**直接测试 CLI：**
```bash
cd your-project
python -m insightor --help
python -m insightor review https://github.com/owner/repo/pull/123 --depth quick
```

## 🛠️ 开发

### 设置开发环境

```bash
cd vscode-extension
npm install
npm run watch  # 自动编译变更
```

### 调试

1. 在 VSCode 中打开 `vscode-extension` 目录
2. 按 `F5` 启动扩展开发主机
3. 在新窗口中测试命令

### 构建

```bash
npm run compile  # 编译 TypeScript
npm run lint     # 检查代码风格
npm run package  # 创建 VSIX
```

### 项目结构

```
vscode-extension/
├── src/
│   ├── extension.ts              # 入口点
│   ├── commands/
│   │   └── commandHandler.ts     # 命令实现
│   ├── services/
│   │   └── insightorService.ts   # CLI 集成
│   └── views/
│       └── reviewTreeProvider.ts # 侧边栏树状视图
├── resources/                    # 图标和资源
├── package.json                  # 扩展清单
└── tsconfig.json                 # TypeScript 配置
```

详细开发指南请参阅 [DEVELOPMENT.md](DEVELOPMENT.md)。

## 📚 文档

- [快速开始指南](QUICKSTART.md) - 5 分钟上手
- [开发指南](DEVELOPMENT.md) - 贡献和构建
- [更新日志](CHANGELOG.md) - 版本历史
- [Insightor 主仓库](https://github.com/SCU-GuGuGaGa/Insightor) - CLI 文档

## 🤝 贡献

欢迎贡献！请：

1. Fork 仓库
2. 创建功能分支
3. 进行修改
4. 运行 `npm run lint` 和 `npm run compile`
5. 提交 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](../LICENSE)



## 📞 支持

- [报告问题](https://github.com/SCU-GuGuGaGa/Insightor/issues)
- [讨论区](https://github.com/SCU-GuGuGaGa/Insightor/discussions)
- [文档](https://github.com/SCU-GuGuGaGa/Insightor)

---

<div align="center">

Made with ❤️ by Insightor Team

[⬆ 返回顶部](#insightor-vscode-扩展)

</div>
