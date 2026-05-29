"""
AI 代码评审的提示词模板
"""

SYSTEM_PROMPT = """你是一个专业的代码评审助手，专注于提供高质量、可操作的代码审查建议。

你的职责：
1. 识别代码中的潜在问题（bug、安全漏洞、性能问题）
2. 评估代码质量（可读性、可维护性、设计模式）
3. 提供具体的改进建议和最佳实践
4. 保持建设性和友好的语气

评审重点：
- 🐛 Bug 和逻辑错误
- 🔒 安全漏洞
- ⚡ 性能问题
- 📖 代码可读性
- 🏗️ 架构和设计
- ✅ 测试覆盖
- 📝 文档完整性

输出格式：
- 使用清晰的标题和分类
- 提供具体的代码位置
- 给出改进建议和示例代码
- 标注问题严重程度（Critical/High/Medium/Low）
"""

CODE_REVIEW_PROMPT = """请对以下 Pull Request 进行代码评审：

## PR 信息
- 标题：{pr_title}
- 描述：{pr_description}
- 分支：{source_branch} → {target_branch}

## 变更文件
{files_summary}

## 代码变更详情
{code_changes}

请提供详细的评审意见，包括：
1. 整体评价
2. 具体问题和建议（按文件组织）
3. 优点和亮点
4. 改进建议

请使用 Markdown 格式输出，便于在 GitHub 上展示。
"""

FILE_REVIEW_PROMPT = """请评审以下文件的变更：

文件：{file_path}
变更类型：{change_type}
变更行数：+{additions} -{deletions}

## 变更内容
```{language}
{diff_content}
```

请分析：
1. 代码质量
2. 潜在问题
3. 改进建议
4. 最佳实践

输出格式：使用 Markdown，包含代码块和具体行号引用。
"""

SECURITY_REVIEW_PROMPT = """请对以下代码进行安全审查：

文件：{file_path}

```{language}
{code_content}
```

重点检查：
1. SQL 注入风险
2. XSS 漏洞
3. 认证和授权问题
4. 敏感信息泄露
5. 不安全的依赖
6. 输入验证
7. 错误处理

请列出发现的安全问题，标注严重程度，并提供修复建议。
"""

PERFORMANCE_REVIEW_PROMPT = """请对以下代码进行性能分析：

文件：{file_path}

```{language}
{code_content}
```

分析重点：
1. 算法复杂度
2. 数据库查询优化
3. 内存使用
4. 并发处理
5. 缓存策略
6. 资源泄漏

请指出性能瓶颈和优化建议。
"""

SUMMARY_PROMPT = """请总结以下代码评审结果：

{review_results}

生成一个简洁的总结，包括：
1. 主要发现（3-5 条）
2. 关键问题数量统计
3. 总体评分（1-10）
4. 是否建议合并

输出格式：简洁的 Markdown，适合作为 PR 评论。
"""

def format_code_review_prompt(pr_info: dict, files_data: list) -> str:
    """
    格式化代码评审提示词

    Args:
        pr_info: PR 基本信息
        files_data: 文件变更数据列表

    Returns:
        格式化后的提示词
    """
    # 生成文件摘要
    files_summary = "\n".join([
        f"- `{f['filename']}` (+{f['additions']} -{f['deletions']}) - {f['status']}"
        for f in files_data
    ])

    # 生成代码变更详情
    code_changes = []
    for f in files_data:
        code_changes.append(f"""
### {f['filename']}
状态：{f['status']}
变更：+{f['additions']} -{f['deletions']}

```diff
{f.get('patch', '无 diff 内容')}
```
""")

    return CODE_REVIEW_PROMPT.format(
        pr_title=pr_info.get('title', 'N/A'),
        pr_description=pr_info.get('body', '无描述'),
        source_branch=pr_info.get('head', {}).get('ref', 'unknown'),
        target_branch=pr_info.get('base', {}).get('ref', 'unknown'),
        files_summary=files_summary,
        code_changes="\n".join(code_changes)
    )

def format_file_review_prompt(file_data: dict) -> str:
    """
    格式化单文件评审提示词

    Args:
        file_data: 文件变更数据

    Returns:
        格式化后的提示词
    """
    # 推断文件语言
    filename = file_data.get('filename', '')
    language = _infer_language(filename)

    return FILE_REVIEW_PROMPT.format(
        file_path=filename,
        change_type=file_data.get('status', 'modified'),
        additions=file_data.get('additions', 0),
        deletions=file_data.get('deletions', 0),
        language=language,
        diff_content=file_data.get('patch', '无 diff 内容')
    )

def format_security_review_prompt(file_path: str, code_content: str) -> str:
    """
    格式化安全审查提示词

    Args:
        file_path: 文件路径
        code_content: 代码内容

    Returns:
        格式化后的提示词
    """
    language = _infer_language(file_path)

    return SECURITY_REVIEW_PROMPT.format(
        file_path=file_path,
        language=language,
        code_content=code_content
    )

def format_performance_review_prompt(file_path: str, code_content: str) -> str:
    """
    格式化性能分析提示词

    Args:
        file_path: 文件路径
        code_content: 代码内容

    Returns:
        格式化后的提示词
    """
    language = _infer_language(file_path)

    return PERFORMANCE_REVIEW_PROMPT.format(
        file_path=file_path,
        language=language,
        code_content=code_content
    )

def _infer_language(filename: str) -> str:
    """
    根据文件名推断编程语言

    Args:
        filename: 文件名

    Returns:
        语言标识符
    """
    ext_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'jsx',
        '.tsx': 'tsx',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sql': 'sql',
        '.sh': 'bash',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.json': 'json',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.md': 'markdown',
    }

    for ext, lang in ext_map.items():
        if filename.endswith(ext):
            return lang

    return 'text'
