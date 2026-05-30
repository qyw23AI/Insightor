# Insightor VSCode 插件 - 完整安装指南

## 🎯 目标

将 Insightor AI 代码审查工具集成到 VSCode 中，实现：
- 在编辑器内直接审查 GitHub PR
- 可视化查看审查结果
- 一键应用代码修复建议
- 人机协同的审查工作流

---

## 📋 前置要求

### 1. 系统要求

- **操作系统**: Windows 10+, macOS 10.15+, Linux
- **VSCode**: 1.85.0 或更高版本
- **Python**: 3.11 或更高版本
- **Node.js**: 16.x 或更高版本（仅开发时需要）
- **Git**: 任意版本

### 2. 账号要求

- GitHub 账号（用于访问 PR）
- LLM API Key（以下任选其一）：
  - OpenAI API Key
  - DeepSeek API Key
  - Anthropic (Claude) API Key

---

## 🚀 安装步骤

### 步骤 1: 安装 Insightor CLI

#### 1.1 克隆仓库

```bash
# 克隆主仓库
git clone https://github.com/SCU-GuGuGaGa/Insightor.git
cd Insightor
```

#### 1.2 安装 Python 包

```bash
# 使用 pip 安装
pip install -e .

# 或使用虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

#### 1.3 验证安装

```bash
# 检查版本
python -m insightor --version

# 应该输出类似: insightor, version 0.x.x
```

### 步骤 2: 配置 API Key

#### 2.1 创建 .env 文件

在你的项目根目录（或 Insightor 目录）创建 `.env` 文件：

```bash
# 方式 1: OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx

# 方式 2: DeepSeek（推荐，性价比高）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# 方式 3: Claude
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxx
```

#### 2.2 测试 API 连接

```bash
# 测试 AI 功能
cd Insightor
python scripts/test_ai.py
```

### 步骤 3: 安装 VSCode 插件

#### 方式 A: 从源码安装（推荐）

```bash
# 进入插件目录
cd vscode-extension

# 安装依赖
npm install

# 编译 TypeScript
npm run compile

# 打包为 VSIX
npm run package
```

这会生成 `insightor-vscode-0.1.0.vsix` 文件。

#### 方式 B: 直接在 VSCode 中安装 VSIX

1. 打开 VSCode
2. 按 `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`)
3. 输入 "Install from VSIX"
4. 选择 `insightor-vscode-0.1.0.vsix` 文件
5. 重启 VSCode

#### 方式 C: 开发模式（用于调试）

```bash
# 在 VSCode 中打开 vscode-extension 目录
cd vscode-extension
code .

# 按 F5 启动扩展开发主机
# 在新窗口中测试插件
```

### 步骤 4: 配置 VSCode 插件

#### 4.1 打开设置

- 按 `Ctrl+,` (Mac: `Cmd+,`)
- 搜索 "insightor"

#### 4.2 配置 Python 路径

```json
{
  "insightor.pythonPath": "python"
}
```

如果使用虚拟环境，设置完整路径：

**Windows**:
```json
{
  "insightor.pythonPath": "C:\\Users\\YourName\\Insightor\\venv\\Scripts\\python.exe"
}
```

**macOS/Linux**:
```json
{
  "insightor.pythonPath": "/Users/yourname/Insightor/venv/bin/python"
}
```

#### 4.3 其他配置（可选）

```json
{
  "insightor.defaultDepth": "standard",
  "insightor.model": "deepseek-v4-flash",
  "insightor.autoOpenResults": true,
  "insightor.showNotifications": true
}
```

---

## ✅ 验证安装

### 测试 1: 检查插件激活

1. 打开 VSCode
2. 查看活动栏（左侧），应该看到 Insightor 图标
3. 按 `Ctrl+Shift+P`，输入 "Insightor"
4. 应该看到 5 个命令：
   - Insightor: Review PR
   - Insightor: Describe PR
   - Insightor: Analyze Risks
   - Insightor: Full Review
   - Insightor: Publish Review

### 测试 2: 运行简单审查

```bash
# 1. 打开命令面板 (Ctrl+Shift+P)
# 2. 选择 "Insightor: Describe PR"
# 3. 输入测试 PR URL:
https://github.com/SCU-GuGuGaGa/Insightor/pull/21

# 4. 选择深度: quick
# 5. 等待 10-20 秒
# 6. 查看侧边栏结果
```

如果成功显示结果，说明安装完成！

---

## 🎓 快速上手教程

### 教程 1: 第一次审查

**目标**: 审查一个真实的 GitHub PR

1. **打开工作区**
   ```bash
   # 打开任意包含 .git 的项目
   code /path/to/your/project
   ```

2. **运行完整审查**
   - 按 `Ctrl+Shift+P`
   - 输入 "Insightor: Full Review"
   - 输入 PR URL（例如你自己项目的 PR）
   - 选择 `standard` 深度
   - 等待 30-60 秒

3. **查看结果**
   - 侧边栏显示审查树
   - 自动打开 `insightor-full-review-{pr}.md`
   - 点击发现跳转到代码

4. **应用修复**
   - 在侧边栏点击发现
   - 查看详情面板
   - 点击 "Apply Fix" 按钮
   - 代码自动更新

### 教程 2: 发布审查到 GitHub

**目标**: 将审查结果发布为 PR 评论

1. **编辑 Markdown 报告**
   ```markdown
   #### 1. 🔴 [critical] SQL Injection vulnerability
   
   - [x] confirmed        # 勾选确认
   - [ ] false_positive
   - [ ] addressed
   - [ ] ignored
   - **审查者:** @yourname
   - **备注:** 需要立即修复
   ```

2. **预览发布**
   - 按 `Ctrl+Shift+P`
   - 选择 "Insightor: Publish Review"
   - 选择编辑的 Markdown 文件
   - 选择 "Yes - Dry run"
   - 查看输出面板预览

3. **正式发布**
   - 再次运行 "Insightor: Publish Review"
   - 选择 "No - Publish to GitHub"
   - 等待完成
   - 在 GitHub PR 页面查看评论

### 教程 3: 自定义规则

**目标**: 为项目添加自定义审查规则

1. **创建配置文件**
   ```bash
   # 在项目根目录创建
   touch .insightor.yml
   ```

2. **添加规则**
   ```yaml
   review:
     custom_rules: |
       1. 所有 API 端点必须有 @require_auth 装饰器
       2. 数据库查询必须使用参数化查询
       3. 敏感数据不能记录到日志
     
     conventions: |
       - 使用 async/await 而非回调
       - 错误消息使用中文
       - 函数名使用 snake_case
     
     focus_categories: ["security", "performance"]
     min_severity: medium
   ```

3. **测试规则**
   - 运行 "Insightor: Review PR"
   - 检查是否应用了自定义规则

---

## 🔧 常见问题排查

### 问题 1: "Insightor CLI not found"

**症状**: 插件提示找不到 Insightor CLI

**解决方案**:

```bash
# 1. 验证 Python 可用
python --version

# 2. 验证 Insightor 安装
python -m insightor --version

# 3. 如果失败，重新安装
cd Insightor
pip install -e . --force-reinstall

# 4. 在 VSCode 中配置正确的 Python 路径
# Settings → insightor.pythonPath
```

### 问题 2: "Review failed: API error"

**症状**: 审查失败，提示 API 错误

**解决方案**:

```bash
# 1. 检查 .env 文件
cat .env
# 确保 API Key 正确

# 2. 测试 API 连接
cd Insightor
python scripts/test_ai.py

# 3. 检查网络连接
curl https://api.openai.com/v1/models
# 或
curl https://api.deepseek.com/v1/models

# 4. 查看详细日志
# VSCode → View → Output → 选择 "Insightor"
```

### 问题 3: 结果不显示

**症状**: 审查完成但侧边栏无结果

**解决方案**:

```bash
# 1. 确保打开了工作区文件夹
# File → Open Folder

# 2. 检查结果文件
ls -la .insightor/reviews/

# 3. 手动刷新
# 点击侧边栏的刷新按钮

# 4. 查看输出日志
# View → Output → Insightor
```

### 问题 4: 编译错误

**症状**: npm run compile 失败

**解决方案**:

```bash
# 1. 清理并重新安装
cd vscode-extension
rm -rf node_modules package-lock.json
npm install

# 2. 检查 Node.js 版本
node --version  # 应该 >= 16.x

# 3. 更新 TypeScript
npm install typescript@latest --save-dev

# 4. 重新编译
npm run compile
```

### 问题 5: Python 路径问题

**症状**: Windows 上找不到 Python

**解决方案**:

```powershell
# 1. 查找 Python 路径
where python

# 2. 或使用 py launcher
where py

# 3. 在 VSCode 设置中使用完整路径
{
  "insightor.pythonPath": "C:\\Python311\\python.exe"
}

# 4. 或使用虚拟环境
{
  "insightor.pythonPath": "C:\\Users\\YourName\\Insightor\\venv\\Scripts\\python.exe"
}
```

---

## 📚 进阶使用

### 技巧 1: 设置键盘快捷键

**文件**: `keybindings.json`

```json
[
  {
    "key": "ctrl+alt+r",
    "command": "insightor.reviewPR",
    "when": "editorTextFocus"
  },
  {
    "key": "ctrl+alt+f",
    "command": "insightor.fullReview"
  },
  {
    "key": "ctrl+alt+d",
    "command": "insightor.describePR"
  },
  {
    "key": "ctrl+alt+p",
    "command": "insightor.publishReview"
  }
]
```

### 技巧 2: 工作区配置

**文件**: `.vscode/settings.json`

```json
{
  "insightor.pythonPath": "${workspaceFolder}/venv/bin/python",
  "insightor.defaultDepth": "deep",
  "insightor.model": "deepseek-v4-flash"
}
```

### 技巧 3: 批量审查

```bash
# 创建脚本审查多个 PR
#!/bin/bash

PRS=(
  "https://github.com/owner/repo/pull/1"
  "https://github.com/owner/repo/pull/2"
  "https://github.com/owner/repo/pull/3"
)

for pr in "${PRS[@]}"; do
  python -m insightor full "$pr" --depth quick
done
```

### 技巧 4: CI/CD 集成

```yaml
# .github/workflows/insightor.yml
name: Insightor Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install Insightor
        run: |
          git clone https://github.com/SCU-GuGuGaGa/Insightor.git
          cd Insightor
          pip install -e .
      
      - name: Run Review
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -m insightor full ${{ github.event.pull_request.html_url }} --depth standard
```

---

## 🎉 完成！

恭喜！你已经成功安装并配置了 Insightor VSCode 插件。

### 下一步

1. ⭐ **Star 项目**: https://github.com/SCU-GuGuGaGa/Insightor
2. 📖 **阅读文档**: [README.md](README.md)
3. 💬 **加入讨论**: [GitHub Discussions](https://github.com/SCU-GuGuGaGa/Insightor/discussions)
4. 🐛 **报告问题**: [GitHub Issues](https://github.com/SCU-GuGuGaGa/Insightor/issues)

### 获取帮助

- **文档**: [QUICKSTART.md](QUICKSTART.md)
- **开发指南**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **变更日志**: [CHANGELOG.md](CHANGELOG.md)
- **项目总结**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

---

**Happy Reviewing! 🚀**
