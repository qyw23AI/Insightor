# AI 代码评审工具

基于 Claude AI 的智能代码评审系统，用于自动分析 GitHub Pull Request 并生成详细的评审报告。

## 项目概述

本工具通过调用 Claude API 对 GitHub PR 的代码变更进行智能分析，支持多种评审类型：
- **安全审查**：识别潜在的安全漏洞和风险代码
- **性能分析**：检测性能瓶颈和优化建议
- **代码风格**：检查代码规范和最佳实践
- **Bug 检测**：发现潜在的逻辑错误和边界情况
- **综合评审**：全方位的代码质量分析

## 架构设计

```
ai_reviewer/
├── prompts.py          # AI 提示词模板
├── context_builder.py  # 代码上下文构建器
├── ai_engine.py        # AI 分析引擎
├── reviewer.py         # 主评审逻辑
├── test_api.py         # API 测试工具
└── __init__.py         # 包初始化
```

### 工作流程

1. **获取 PR 信息** → 从 GitHub API 获取 PR 的文件变更和 diff
2. **构建上下文** → 解析代码变更，提取关键信息，构建评审上下文
3. **AI 分析** → 调用 Claude API，使用专业提示词进行代码分析
4. **生成报告** → 整合分析结果，生成结构化的评审报告

---

## 模块说明

### 1. prompts.py - 提示词模板

定义了所有 AI 评审使用的提示词模板，确保评审的专业性和一致性。

#### 主要内容

- **SYSTEM_PROMPT**：系统角色定义，设定 AI 为资深代码评审专家
- **PR_SUMMARY_PROMPT**：PR 变更总结提示词
- **SECURITY_REVIEW_PROMPT**：安全审查提示词
  - 检查 SQL 注入、XSS、CSRF 等常见漏洞
  - 识别敏感信息泄露风险
  - 验证权限控制和数据验证
- **PERFORMANCE_REVIEW_PROMPT**：性能审查提示词
  - 分析算法复杂度
  - 检测资源泄漏和内存问题
  - 识别数据库查询优化机会
- **STYLE_REVIEW_PROMPT**：代码风格审查提示词
  - 检查命名规范
  - 验证代码结构和可读性
  - 评估注释和文档质量
- **BUG_DETECTION_PROMPT**：Bug 检测提示词
  - 发现逻辑错误
  - 检查边界条件处理
  - 识别异常处理问题
- **COMPREHENSIVE_REVIEW_PROMPT**：综合评审提示词
  - 整合所有评审维度
  - 提供全面的代码质量分析

#### 特点

- 结构化输出格式（JSON）
- 中文评审报告
- 包含风险等级评估（高/中/低）
- 提供具体的修改建议和代码示例

---

### 2. context_builder.py - 上下文构建器

负责解析 PR 文件变更，提取代码信息，构建适合 AI 分析的上下文。

#### 主要类和方法

**`ContextBuilder` 类**

- **`__init__(repo_path=None)`**
  - 初始化构建器
  - `repo_path`：本地仓库路径（可选）

- **`build_context(pr_files)`**
  - 构建完整的评审上下文
  - 参数：`pr_files` - PR 文件变更列表（从 GitHub API 获取）
  - 返回：包含文件变更、统计信息、语言分布的字典

- **`_parse_file_changes(pr_files)`**
  - 解析文件变更详情
  - 提取文件名、状态（added/modified/deleted）、变更行数、patch 内容

- **`_extract_language(filename)`**
  - 根据文件扩展名识别编程语言
  - 支持常见语言：Python, JavaScript, Java, Go, Rust 等

- **`_read_full_file(filepath)`**
  - 读取本地仓库的完整文件内容
  - 用于提供更多上下文信息

#### 输出格式

```python
{
    "files": [
        {
            "filename": "src/main.py",
            "status": "modified",
            "additions": 10,
            "deletions": 5,
            "changes": 15,
            "language": "Python",
            "patch": "diff内容",
            "full_content": "完整文件内容（如果可用）"
        }
    ],
    "summary": {
        "total_files": 3,
        "total_additions": 50,
        "total_deletions": 20,
        "languages": ["Python", "JavaScript"]
    }
}
```

---

### 3. ai_engine.py - AI 分析引擎

封装 Claude API 调用，提供统一的 AI 分析接口。

#### 主要类和方法

**`AIEngine` 类**

- **`__init__(api_key=None, base_url=None, model="claude-opus-4-8")`**
  - 初始化 AI 引擎
  - `api_key`：Claude API 密钥（默认从环境变量读取）
  - `base_url`：API 代理地址（支持第三方代理）
  - `model`：使用的 Claude 模型

- **`analyze_code(context, review_type="comprehensive")`**
  - 执行代码分析
  - 参数：
    - `context`：代码上下文（由 ContextBuilder 生成）
    - `review_type`：评审类型（security/performance/style/bugs/comprehensive）
  - 返回：AI 分析结果（JSON 格式）

- **`_get_prompt_for_type(review_type)`**
  - 根据评审类型选择对应的提示词模板

- **`_format_context(context)`**
  - 将上下文格式化为适合 AI 分析的文本

- **`_call_claude_api(messages)`**
  - 调用 Claude API
  - 处理错误和重试逻辑
  - 返回 API 响应

- **`get_token_usage()`**
  - 获取 Token 使用统计
  - 返回输入和输出 Token 数量

#### 特点

- 支持自定义 API base_url（适配第三方代理）
- 自动选择合适的提示词模板
- Token 使用统计
- 错误处理和日志记录
- JSON 格式输出解析

---

### 4. reviewer.py - 主评审逻辑

整合所有模块，提供完整的 PR 评审功能。

#### 主要类和方法

**`PRReviewer` 类**

- **`__init__(github_token=None, api_key=None, base_url=None, model="claude-opus-4-8", repo_path=None)`**
  - 初始化评审器
  - 整合 GitHub API、ContextBuilder 和 AIEngine

- **`review_pr(owner, repo, pr_number, review_type="comprehensive")`**
  - 执行完整的 PR 评审流程
  - 参数：
    - `owner`：仓库所有者
    - `repo`：仓库名称
    - `pr_number`：PR 编号
    - `review_type`：评审类型
  - 返回：评审报告字典

- **`_fetch_pr_files(owner, repo, pr_number)`**
  - 从 GitHub API 获取 PR 文件变更

- **`_generate_report(pr_info, context, analysis, review_type)`**
  - 生成结构化的评审报告
  - 包含 PR 基本信息、代码变更统计、AI 分析结果

- **`save_report(report, output_path)`**
  - 保存评审报告到文件
  - 支持 JSON 和 Markdown 格式

#### 评审报告结构

```python
{
    "pr_info": {
        "number": 1,
        "title": "PR标题",
        "author": "作者",
        "created_at": "创建时间",
        "state": "open/closed"
    },
    "review_type": "comprehensive",
    "code_changes": {
        "total_files": 3,
        "total_additions": 50,
        "total_deletions": 20,
        "languages": ["Python"]
    },
    "analysis": {
        "summary": "总体评价",
        "issues": [
            {
                "severity": "high",
                "category": "security",
                "description": "问题描述",
                "location": "文件:行号",
                "suggestion": "修改建议"
            }
        ],
        "recommendations": ["建议1", "建议2"]
    },
    "metadata": {
        "reviewed_at": "评审时间",
        "model": "claude-opus-4-8",
        "token_usage": {"input": 1000, "output": 500}
    }
}
```

---

### 5. test_api.py - API 测试工具

用于测试 Claude API 连接和功能验证。

#### 主要功能

- **测试 API 连接**：验证 API 密钥和 base_url 配置
- **测试多个模型**：尝试不同的 Claude 模型名称
- **代码分析测试**：使用示例代码验证分析功能
- **错误诊断**：输出详细的错误信息和调试日志

#### 使用方法

```bash
python ai_reviewer/test_api.py
```

#### 测试的模型

- claude-opus-4-8（推荐）
- claude-sonnet-4-6
- claude-3-5-sonnet-20241022

---

## 使用示例

### 命令行使用

```bash
# 综合评审
python main.py --owner qyw23AI --repo insightor --pr 1

# 安全审查
python main.py --owner qyw23AI --repo insightor --pr 1 --type security

# 性能分析
python main.py --owner qyw23AI --repo insightor --pr 1 --type performance

# 保存报告到文件
python main.py --owner qyw23AI --repo insightor --pr 1 --output report.json
```

### Python 代码使用

```python
from ai_reviewer.reviewer import PRReviewer

# 初始化评审器
reviewer = PRReviewer()

# 执行评审
report = reviewer.review_pr(
    owner="qyw23AI",
    repo="insightor",
    pr_number=1,
    review_type="comprehensive"
)

# 保存报告
reviewer.save_report(report, "review_report.json")
```

---

## 配置说明

### 环境变量（.env 文件）

```env
# GitHub API Token
GITHUB_TOKEN=your_github_token

# Claude API 配置
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_BASE_URL=https://cc-vibe.com  # 第三方代理地址

# 默认仓库配置（可选）
OWNER=qyw23AI
REPO=insightor
PR_NUMBER=1
```

### 支持的评审类型

| 类型 | 说明 | 适用场景 |
|------|------|----------|
| `security` | 安全审查 | 涉及用户输入、数据库操作、权限控制的代码 |
| `performance` | 性能分析 | 算法优化、资源密集型操作 |
| `style` | 代码风格 | 代码规范检查、可读性改进 |
| `bugs` | Bug 检测 | 逻辑错误、边界条件问题 |
| `comprehensive` | 综合评审 | 全面的代码质量分析（默认） |

---

## 技术栈

- **Python 3.8+**
- **GitHub API**：获取 PR 信息
- **Claude API (Anthropic)**：AI 代码分析
- **python-dotenv**：环境变量管理
- **requests**：HTTP 请求

---

## 依赖安装

```bash
pip install -r requirements.txt
```

---

## 注意事项

1. **API 配置**：确保 `.env` 文件中配置了正确的 API 密钥和 base_url
2. **Token 使用**：Claude API 按 Token 计费，大型 PR 可能消耗较多 Token
3. **速率限制**：注意 GitHub API 和 Claude API 的速率限制
4. **本地仓库**：如果提供本地仓库路径，可以获取完整文件内容以提供更多上下文
5. **模型选择**：推荐使用 `claude-opus-4-8`，性能和准确度最佳

---

## 未来改进方向

- [ ] 支持批量评审多个 PR
- [ ] 添加评审结果缓存机制
- [ ] 支持自定义评审规则
- [ ] 集成到 GitHub Actions
- [ ] 添加 Web UI 界面
- [ ] 支持更多编程语言的专项规则
- [ ] 生成 Markdown 格式的评审报告
- [ ] 支持增量评审（只评审新增的 commit）

---

## 开发者

- **项目**：insightor
- **分支**：feature/AI-reviewer
- **开发时间**：2024年5月

---

## 许可证

本项目仅供学习和研究使用。
