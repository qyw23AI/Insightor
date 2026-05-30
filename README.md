# Insightor - AI Code Reviewer

Insightor 是一个用于 GitHub Pull Request 的 AI 评审插件：输入 PR URL，生成评审结果，并可选自动发布到 GitHub 评论区。

## 功能

- 四类评审：`comprehensive` / `security` / `performance` / `quality`
- 支持自动评论发布到 PR
- 支持 VS Code 插件与 CLI

## 快速开始（VS Code 插件）

### 1. 安装

在 VS Code 扩展市场搜索 `Insightor - AI Code Reviewer` 并安装。

### 2. 配置

打开命令面板 `Ctrl+Shift+P`，执行 `Insightor: Configure API Keys`，按提示输入：
- GitHub Token
- Anthropic API Key
- Anthropic Base URL

### 3. 开始评审

执行 `Insightor: Review GitHub PR`，输入：
`https://github.com/owner/repo/pull/123`

评审结果会在新标签页显示。

## 插件命令

- `Insightor: Review GitHub PR`：按 PR URL 评审
- `Insightor: Review Current Repository PR`：评审当前仓库指定 PR 编号
- `Insightor: Configure API Keys`：配置 GitHub Token / API Key / Base URL

## 配置项

```json
{
  "insightor.githubToken": "your_github_token",
  "insightor.anthropicApiKey": "your_anthropic_api_key",
  "insightor.anthropicBaseUrl": "https://cc-vibe.com",
  "insightor.reviewType": "comprehensive",
  "insightor.autoPostComment": true,
  "insightor.commentType": "summary"
}
```

- `insightor.reviewType`：默认评审类型
- `insightor.autoPostComment`：是否自动发布评论
- `insightor.commentType`：评论格式（`summary | full | separate`）

默认配置建议：
- 全局默认放设置下的 User Settings（密钥等信息建议放此处）
- 项目特定配置放 `.vscode/settings.json`

## 常见问题

### 评论没有发布到 GitHub怎么办？
1. 确认 `insightor.autoPostComment=true`
2. 确认 GitHub Token 有效
3. 确认 Token 权限：私有仓库 `repo`，公开仓库 `public_repo`

### 日志在哪里看？
VS Code `Output` 面板，选择 `Insightor` 通道。

## CLI 使用（开发者/高级用户）

### 1. 获取源码

```bash
git clone https://github.com/SCU-GuGuGaGa/Insightor.git
cd Insightor
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 `.env`

```env
GITHUB_TOKEN=your_github_token_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
ANTHROPIC_BASE_URL=https://cc-vibe.com
```

### 4. 运行示例

```bash
# 基础评审
python main.py --owner SCU-GuGuGaGa --repo Insightor --pr 1

# 使用 URL
python main.py --url https://github.com/SCU-GuGuGaGa/Insightor/pull/1

# 输出到文件
python main.py --owner SCU-GuGuGaGa --repo Insightor --pr 1 --output report.md

# 发布评论
python main.py --owner SCU-GuGuGaGa --repo Insightor --pr 1 --post-comment summary
```

## License

MIT
