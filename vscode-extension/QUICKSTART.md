# Insightor VSCode 插件 - 快速开始

## 📦 安装

### 方法 1: 从源码安装（推荐用于开发）

1. **克隆仓库**
   ```bash
   git clone https://github.com/SCU-GuGuGaGa/Insightor.git
   cd Insightor/vscode-extension
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **编译**
   ```bash
   npm run compile
   ```

4. **在 VSCode 中打开并按 F5 调试**
   - 或者打包为 VSIX：`npm run package`
   - 然后在 VSCode 中安装 VSIX 文件

### 方法 2: 从 VSIX 安装

1. 下载 `insightor-vscode-0.1.0.vsix`
2. 打开 VSCode
3. 按 `Ctrl+Shift+P` 打开命令面板
4. 输入 "Install from VSIX"
5. 选择下载的 VSIX 文件

## ⚙️ 配置

### 1. 安装 Insightor CLI

```bash
# 克隆主仓库
git clone https://github.com/SCU-GuGuGaGa/Insightor.git
cd Insightor

# 安装
pip install -e .

# 验证安装
python -m insightor --version
```

### 2. 配置 API Key

在项目根目录创建 `.env` 文件：

```bash
# OpenAI
OPENAI_API_KEY=sk-xxx

# 或 DeepSeek
DEEPSEEK_API_KEY=sk-xxx

# 或 Claude
ANTHROPIC_API_KEY=sk-xxx
```

### 3. 配置 VSCode 插件

打开 VSCode 设置（`Ctrl+,`），搜索 "insightor"：

- **Python Path**: 设置 Python 可执行文件路径（默认: `python`）
- **Default Depth**: 选择默认分析深度（`quick` / `standard` / `deep`）
- **Model**: 可选，覆盖默认 LLM 模型
- **Auto Open Results**: 分析完成后自动打开结果
- **Show Notifications**: 显示通知消息

## 🚀 使用

### 基本工作流

1. **打开命令面板** (`Ctrl+Shift+P`)

2. **选择命令**:
   - `Insightor: Full Review` - 完整审查（推荐）
   - `Insightor: Review PR` - 代码审查
   - `Insightor: Describe PR` - PR 描述
   - `Insightor: Analyze Risks` - 风险分析

3. **输入 PR URL**:
   ```
   https://github.com/owner/repo/pull/123
   ```

4. **选择分析深度**:
   - `quick` - 快速扫描 (~15s, ~3K tokens)
   - `standard` - 标准审查 (~30s, ~8K tokens) ⭐
   - `deep` - 深度分析 (~60s, ~16K tokens)

5. **查看结果**:
   - 侧边栏显示审查结果树
   - 自动打开 Markdown 报告
   - 点击发现跳转到代码位置

### 发布审查

1. **编辑生成的 Markdown 文件**:
   - 勾选 checkbox 确认/拒绝发现
   - 填写审查者和备注

2. **发布到 GitHub**:
   - 命令面板 → `Insightor: Publish Review`
   - 选择要发布的 Markdown 文件
   - 选择是否 dry-run（预览）

## 📊 侧边栏视图

点击活动栏的 Insightor 图标查看：

- **📋 PR Summary** - PR 类型和概述
- **✅/⚠️/🔴 Score** - 合并就绪评分
- **🔴 CRITICAL** - 严重问题
- **🟡 HIGH** - 高优先级问题
- **🔵 MEDIUM** - 中等问题
- **⚪ LOW** - 低优先级问题
- **ℹ️ INFO** - 信息提示
- **📁 Files Changed** - 变更文件列表

### 交互操作

- **点击发现** → 跳转到代码位置并显示详情
- **Apply Fix 按钮** → 应用建议的代码修复
- **刷新按钮** → 重新加载结果
- **设置按钮** → 打开插件设置

## 🎯 示例

### 示例 1: 快速审查小 PR

```
1. Ctrl+Shift+P → "Insightor: Review PR"
2. 输入: https://github.com/myorg/myrepo/pull/42
3. 选择: quick
4. 等待 15 秒
5. 查看侧边栏结果
```

### 示例 2: 完整审查并发布

```
1. Ctrl+Shift+P → "Insightor: Full Review"
2. 输入: https://github.com/myorg/myrepo/pull/123
3. 选择: standard
4. 等待 30 秒
5. 编辑生成的 insightor-full-review-123.md
6. Ctrl+Shift+P → "Insightor: Publish Review"
7. 选择文件并确认发布
```

### 示例 3: 聚焦安全风险

```
1. Ctrl+Shift+P → "Insightor: Analyze Risks"
2. 输入 PR URL
3. 选择: standard
4. Focus: security
5. 查看安全相关发现
```

## 🔧 故障排除

### "Insightor CLI not found"

**原因**: Python 或 Insightor CLI 未正确安装

**解决**:
```bash
# 验证 Python
python --version

# 验证 Insightor
python -m insightor --version

# 如果失败，重新安装
cd Insightor
pip install -e .
```

### "Review failed"

**原因**: API Key 未配置或网络问题

**解决**:
1. 检查 `.env` 文件中的 API Key
2. 查看输出面板（View → Output → Insightor）
3. 验证网络连接

### 结果不显示

**原因**: 工作区未打开或结果文件未生成

**解决**:
1. 确保打开了工作区文件夹
2. 检查 `.insightor/reviews/` 目录
3. 查看输出面板的错误信息

### Python 路径错误

**解决**:
1. 打开设置 → 搜索 "insightor.pythonPath"
2. 设置完整路径，例如:
   - Windows: `C:\Python311\python.exe`
   - Linux/Mac: `/usr/bin/python3`

## 📝 配置文件示例

### VSCode settings.json

```json
{
  "insightor.pythonPath": "python",
  "insightor.defaultDepth": "standard",
  "insightor.model": "deepseek-v4-flash",
  "insightor.autoOpenResults": true,
  "insightor.showNotifications": true
}
```

### .insightor.yml (项目级配置)

```yaml
review:
  custom_rules: |
    1. 所有 API 路由必须有认证
    2. 禁止使用字符串拼接 SQL
  
  conventions: |
    - 使用 async/await
    - 错误消息使用中文
  
  focus_categories: ["security", "performance"]
  min_severity: medium
  max_suggestions: 15
```

## 🎨 自定义键盘快捷键

在 VSCode 中添加快捷键（File → Preferences → Keyboard Shortcuts）：

```json
[
  {
    "key": "ctrl+alt+r",
    "command": "insightor.reviewPR"
  },
  {
    "key": "ctrl+alt+f",
    "command": "insightor.fullReview"
  },
  {
    "key": "ctrl+alt+p",
    "command": "insightor.publishReview"
  }
]
```

## 📚 更多资源

- [Insightor 主仓库](https://github.com/SCU-GuGuGaGa/Insightor)
- [CLI 文档](https://github.com/SCU-GuGuGaGa/Insightor/blob/main/README.md)
- [提交问题](https://github.com/SCU-GuGuGaGa/Insightor/issues)

## 💡 提示

- 使用 `standard` 深度适合大多数场景
- `deep` 模式适合关键 PR 或复杂变更
- 定期查看输出面板了解详细日志
- 编辑 Markdown 报告时可以添加自己的评论
- 使用 dry-run 模式预览发布内容

## 🤝 贡献

欢迎贡献代码！请查看 [DEVELOPMENT.md](DEVELOPMENT.md) 了解开发指南。

## 📄 许可证

MIT
