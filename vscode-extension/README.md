# Insightor VSCode Extension

<div align="center">

![Insightor Logo](resources/icon.png)

**AI-powered GitHub PR review assistant for Visual Studio Code**

[![VSCode](https://img.shields.io/badge/VSCode-1.85+-blue.svg)](https://code.visualstudio.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[Quick Start](#-quick-start-3-steps) • [Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Configuration](#-configuration)

</div>

---

## 🚀 Quick Start (3 Steps)

### Step 1: Install Insightor CLI

```bash
pip install git+https://github.com/SCU-GuGuGaGa/Insightor.git
```

### Step 2: Configure API Key

Create `.env` file in your project root:

```bash
# Choose one:
OPENAI_API_KEY=sk-xxx
# or
DEEPSEEK_API_KEY=sk-xxx
# or
ANTHROPIC_API_KEY=sk-xxx
```

### Step 3: Install Extension & Use

1. Install `insightor-vscode-0.1.0.vsix` in VSCode
2. Press `Ctrl+Shift+P` → Type `Insightor: Full Review`
3. Enter PR URL: `https://github.com/owner/repo/pull/123`
4. View results in sidebar! 🎉

---

## 🎯 Overview

Insightor VSCode Extension brings the power of AI-driven code review directly into your editor. Analyze GitHub Pull Requests, identify risks, generate descriptions, and publish reviews—all without leaving VSCode.

### Why Insightor?

- 🤖 **AI-Powered Analysis** - Leverages LLMs (OpenAI, DeepSeek, Claude) for intelligent code review
- 🔍 **Multi-Dimensional Review** - Code quality, security risks, performance issues, and more
- 🌳 **Visual Tree View** - Browse findings organized by severity in the sidebar
- 💡 **Quick Fixes** - Apply suggested code changes with one click
- 📊 **Merge Readiness Score** - Get a confidence score for PR approval
- 🚀 **Human-in-the-Loop** - Review and confirm AI findings before publishing

## ✨ Features

### Core Commands

| Command | Description | Shortcut |
|---------|-------------|----------|
| **Full Review** | Complete analysis (describe + risks + review) | - |
| **Review PR** | Detailed code review with suggestions | - |
| **Describe PR** | Generate PR description and file walkthrough | - |
| **Analyze Risks** | Identify security, performance, concurrency risks | - |
| **Publish Review** | Post human-confirmed reviews to GitHub | - |

### Sidebar View

- **Findings by Severity**: Critical, High, Medium, Low, Info
- **Merge Readiness Score**: 0-100 confidence rating
- **File Walkthrough**: See all changed files with summaries
- **Click to Navigate**: Jump directly to code locations
- **Apply Fixes**: One-click code suggestions

### Analysis Depths

| Depth | Time | Tokens | Use Case |
|-------|------|--------|----------|
| **Quick** | ~15s | ~3K | Small PRs, quick checks |
| **Standard** | ~30s | ~8K | Most PRs (default) |
| **Deep** | ~60s | ~16K | Critical changes, complex logic |

## 📦 Detailed Installation

### Prerequisites

✅ **Python 3.11+** with Insightor CLI installed  
✅ **LLM API Key** (OpenAI, DeepSeek, or Claude)  
✅ **VSCode 1.85+**

### Install Insightor CLI

**Option A: From PyPI (Recommended)**
```bash
pip install git+https://github.com/SCU-GuGuGaGa/Insightor.git
```

**Option B: From Source**
```bash
git clone https://github.com/SCU-GuGuGaGa/Insightor.git
cd Insightor
pip install -e .
```

**Verify Installation:**
```bash
python -m insightor --version
# Should output: insightor 0.1.0
```

### Configure API Key

Create `.env` file in your **project root** (where you'll review PRs):

```bash
# Choose ONE provider:
OPENAI_API_KEY=sk-proj-xxxxx           # OpenAI GPT-4
DEEPSEEK_API_KEY=sk-xxxxx              # DeepSeek (cheaper)
ANTHROPIC_API_KEY=sk-ant-xxxxx         # Claude
```

💡 **Tip**: You can also set environment variables globally or use `.insightor.yml` for per-project config.

### Install VSCode Extension

**Option A: From VSIX (Recommended)**

1. Download `insightor-vscode-0.1.0.vsix`
2. Open VSCode → Extensions (`Ctrl+Shift+X`)
3. Click `...` menu → `Install from VSIX...`
4. Select the downloaded file

**Option B: From Source (Developers)**

```bash
cd vscode-extension
npm install
npm run compile
# Press F5 to launch Extension Development Host
```

## 🚀 How to Use

### Basic Usage

**1️⃣ Open Command Palette**
- Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)

**2️⃣ Choose a Command**
- `Insightor: Full Review` - Complete analysis (recommended for first use)
- `Insightor: Review PR` - Code review only
- `Insightor: Describe PR` - Generate PR description
- `Insightor: Analyze Risks` - Security & performance risks
- `Insightor: Publish Review` - Post results to GitHub

**3️⃣ Enter PR URL**
```
https://github.com/owner/repo/pull/123
```

**4️⃣ Select Analysis Depth**
- `quick` - 15 seconds, small PRs
- `standard` - 30 seconds, most PRs (default)
- `deep` - 60 seconds, critical changes

**5️⃣ View Results**
- **Sidebar**: Click Insightor icon in Activity Bar (left side)
- **Markdown**: Auto-opens in editor with full report
- **Click findings**: Jump directly to code locations

### Workflow Example

```
┌─────────────────────────────────────┐
│ 1. Run Full Review                  │
│    Input: PR URL                    │
│    Depth: standard                  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. AI Analysis                      │
│    - Describe PR                    │
│    - Identify Risks                 │
│    - Review Code                    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Review Results                   │
│    - Sidebar tree view              │
│    - Markdown report                │
│    - Click findings → jump to code  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. Human Review                     │
│    - Edit markdown                  │
│    - Check/uncheck findings         │
│    - Add comments                   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. Publish to GitHub                │
│    Command: Publish Review          │
│    Option: Dry-run or Live          │
└─────────────────────────────────────┘
```

### Sidebar Navigation

```
Insightor
├── 📋 PR Summary
│   └── Overview text
├── ✅ Score: 85/100
├── 🔴 CRITICAL (2)
│   ├── SQL Injection vulnerability
│   └── Unvalidated user input
├── 🟡 HIGH (5)
│   ├── Race condition in cache
│   └── ...
├── 🔵 MEDIUM (8)
├── ⚪ LOW (3)
└── 📁 Files Changed (12)
    ├── [modified] src/api/users.py
    └── ...
```

## ⚙️ Configuration

### VSCode Settings

Open Settings (`Ctrl+,`) and search for "insightor":

```json
{
  "insightor.pythonPath": "python",
  "insightor.defaultDepth": "standard",
  "insightor.model": "",
  "insightor.autoOpenResults": true,
  "insightor.showNotifications": true
}
```

### Project Configuration

Create `.insightor.yml` in your repo:

```yaml
review:
  custom_rules: |
    1. All API routes must have authentication
    2. Use parameterized queries, not string concatenation
  
  conventions: |
    - Use async/await instead of callbacks
    - Error messages in Chinese
  
  focus_categories: ["security", "performance"]
  min_severity: medium
  max_suggestions: 15
```

### Custom Keyboard Shortcuts

Add to `keybindings.json`:

```json
[
  { "key": "ctrl+alt+r", "command": "insightor.reviewPR" },
  { "key": "ctrl+alt+f", "command": "insightor.fullReview" },
  { "key": "ctrl+alt+p", "command": "insightor.publishReview" }
]
```

## 🎨 Screenshots

### Command Palette
![Command Palette](docs/screenshots/command-palette.png)

### Sidebar View
![Sidebar View](docs/screenshots/sidebar-view.png)

### Finding Details
![Finding Details](docs/screenshots/finding-details.png)

### Markdown Report
![Markdown Report](docs/screenshots/markdown-report.png)

## 🔧 Troubleshooting

### ❌ "Insightor CLI not found"

**Check CLI installation:**
```bash
python -m insightor --version
```

**If command fails:**
```bash
pip install git+https://github.com/SCU-GuGuGaGa/Insightor.git
```

**If using virtual environment:**
- Set `insightor.pythonPath` in VSCode settings to your venv Python path
- Example: `/path/to/venv/bin/python` or `C:\path\to\venv\Scripts\python.exe`

### ❌ "Review failed" or API errors

**Check API key:**
1. Verify `.env` file exists in project root
2. Check key format: `OPENAI_API_KEY=sk-proj-xxxxx` (no quotes, no spaces)
3. Test manually:
   ```bash
   cd your-project
   python -m insightor review https://github.com/owner/repo/pull/123
   ```

**Check network:**
- Ensure you can access OpenAI/DeepSeek/Anthropic APIs
- Check firewall/proxy settings

### ❌ No results showing

1. **Ensure workspace folder is open** (File → Open Folder)
2. **Check Output panel**: View → Output → Select "Insightor"
3. **Verify command completed**: Look for "Analysis complete" notification

### 🐛 Debug Mode

**View detailed logs:**
1. View → Output (`Ctrl+Shift+U`)
2. Select "Insightor" from dropdown
3. Check for error messages

**Test CLI directly:**
```bash
cd your-project
python -m insightor --help
python -m insightor review https://github.com/owner/repo/pull/123 --depth quick
```

## 🛠️ Development

### Setup

```bash
cd vscode-extension
npm install
npm run watch  # Auto-compile on changes
```

### Debug

1. Open `vscode-extension` in VSCode
2. Press `F5` to launch Extension Development Host
3. Test commands in the new window

### Build

```bash
npm run compile  # Compile TypeScript
npm run lint     # Check code style
npm run package  # Create VSIX
```

### Project Structure

```
vscode-extension/
├── src/
│   ├── extension.ts              # Entry point
│   ├── commands/
│   │   └── commandHandler.ts     # Command implementations
│   ├── services/
│   │   └── insightorService.ts   # CLI integration
│   └── views/
│       └── reviewTreeProvider.ts # Sidebar tree view
├── resources/                    # Icons and assets
├── package.json                  # Extension manifest
└── tsconfig.json                 # TypeScript config
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development guide.

## 📚 Documentation

- [Quick Start Guide](QUICKSTART.md) - Get started in 5 minutes
- [Development Guide](DEVELOPMENT.md) - Contributing and building
- [Changelog](CHANGELOG.md) - Version history
- [Main Insightor Repo](https://github.com/SCU-GuGuGaGa/Insightor) - CLI documentation

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `npm run lint` and `npm run compile`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](../LICENSE) for details

## 🙏 Acknowledgments

- Built on top of [Insightor CLI](https://github.com/SCU-GuGuGaGa/Insightor)
- Powered by LLMs (OpenAI, DeepSeek, Claude)
- Inspired by the VSCode extension ecosystem

## 📞 Support

- [Report Issues](https://github.com/SCU-GuGuGaGa/Insightor/issues)
- [Discussions](https://github.com/SCU-GuGuGaGa/Insightor/discussions)
- [Documentation](https://github.com/SCU-GuGuGaGa/Insightor)

---

<div align="center">

Made with ❤️ by the Insightor Team

[⬆ Back to Top](#insightor-vscode-extension)

</div>
