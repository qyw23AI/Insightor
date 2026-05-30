# Changelog

All notable changes to the "insightor-vscode" extension will be documented in this file.

## [0.1.0] - 2026-05-30

### Added
- Initial release of Insightor VSCode extension
- Command: Review PR - Run complete code review
- Command: Describe PR - Generate PR description
- Command: Analyze Risks - Identify security and performance risks
- Command: Full Review - Run all analysis tools
- Command: Publish Review - Publish to GitHub
- Sidebar view with tree structure for review results
- Findings organized by severity (critical, high, medium, low, info)
- Click to jump to code location
- Apply fix button for suggested code changes
- Webview panel for detailed finding information
- Configuration options for Python path, depth, model
- Progress notifications during analysis
- Output channel for detailed logs

### Features
- Integration with Insightor CLI
- Support for quick/standard/deep analysis depths
- Incremental review mode
- Dry-run mode for publish
- Auto-open results after analysis
- Merge readiness score display
- File walkthrough view
- Syntax highlighting in code suggestions

### Configuration
- `insightor.pythonPath` - Python executable path
- `insightor.defaultDepth` - Default analysis depth
- `insightor.model` - LLM model override
- `insightor.autoOpenResults` - Auto-open results
- `insightor.showNotifications` - Show notifications

## [Unreleased]

### Planned
- Inline code decorations for findings
- Quick fix code actions
- Diff view for suggested changes
- History of past reviews
- Custom rule configuration UI
- Multi-PR batch review
- Integration with GitHub Pull Requests extension
- Code lens for review status
- Diagnostic integration
