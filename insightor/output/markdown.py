"""MarkdownFileOutput — 生成结构化 Markdown 审查报告。"""

from datetime import datetime, timezone
from pathlib import Path

from insightor.schemas.urf import ReviewResult, Severity

_SEVERITY_ICON = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟡",
    Severity.MEDIUM: "🔵",
    Severity.LOW: "⚪",
    Severity.INFO: "ℹ️",
}


class MarkdownFileOutput:
    """将 ReviewResult 输出为可读 Markdown 报告。"""

    def __init__(self, output_dir: str = "."):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._last_path: Path | None = None

    def post(self, result: ReviewResult) -> None:
        meta = result.meta
        sha_short = meta.commit_sha[:8] if meta.commit_sha else "unknown"
        pr_num = "unknown"
        if meta.pr_url:
            parts = meta.pr_url.rstrip("/").split("/")
            if parts and parts[-1].isdigit():
                pr_num = parts[-1]

        fname = f"insightor-review-{pr_num}.md"
        path = self._output_dir / fname
        self._last_path = path

        lines: list[str] = []
        s = result.summary
        mr = result.merge_readiness
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Header
        lines.append(f"# Insightor Review — PR #{pr_num}")
        lines.append(f"")
        lines.append(f"> 生成时间: {ts} | 模型: {meta.model} | 深度: {meta.analysis_depth.value}")
        lines.append(f"> PR: {meta.pr_url}")

        # Summary
        lines.append(f"")
        lines.append(f"## 总结")
        lines.append(f"")
        lines.append(f"- **类型**: {s.pr_type or 'N/A'}")
        lines.append(f"- **概述**: {s.overview or '无'}")
        lines.append(f"- **文件变更**: {meta.files_analyzed} 个  |  发现: {len(result.findings)} 个")

        # Merge Readiness
        if mr:
            score_icon = "✅" if mr.score >= 80 else "⚠️" if mr.score >= 50 else "🔴"
            lines.append(f"")
            lines.append(f"## 合并就绪评估")
            lines.append(f"")
            lines.append(f"- **评分**: {score_icon} {mr.score:.0f}/100 — {mr.recommendation.value}")
            if mr.blocking_issues:
                lines.append(f"- **阻断问题**: {len(mr.blocking_issues)} 个")
                for bi in mr.blocking_issues:
                    lines.append(f"  - {bi}")
            if mr.summary:
                lines.append(f"- {mr.summary}")

        # File Walkthrough
        if result.file_walkthrough:
            lines.append(f"")
            lines.append(f"## 变更文件 ({len(result.file_walkthrough)})")
            lines.append(f"")
            lines.append(f"| 操作 | 文件 | 说明 |")
            lines.append(f"|------|------|------|")
            for fw in result.file_walkthrough:
                lines.append(f"| {fw.edit_type.value} | `{fw.path}` | {fw.summary[:80]} |")

        # Findings
        if result.findings:
            lines.append(f"")
            lines.append(f"## 发现 ({len(result.findings)})")
            for i, f in enumerate(result.findings, 1):
                icon = _SEVERITY_ICON.get(f.severity, "")
                lines.append(f"")
                lines.append(f"### {i}. {icon} [{f.severity.value}] {f.title}")
                lines.append(f"")
                lines.append(f"- **类别**: {f.category}")
                lines.append(f"- **文件**: `{f.location.path}:{f.location.range.start.line}`")
                if f.description:
                    lines.append(f"- **说明**: {f.description}")
                if f.suggestion:
                    if f.suggestion.current_code:
                        lines.append(f"- **当前代码**:")
                        lines.append(f"  ```")
                        lines.append(f"  {f.suggestion.current_code}")
                        lines.append(f"  ```")
                    if f.suggestion.suggested_code:
                        lines.append(f"- **建议代码**:")
                        lines.append(f"  ```")
                        lines.append(f"  {f.suggestion.suggested_code}")
                        lines.append(f"  ```")
                if f.confidence:
                    lines.append(f"- **置信度**: {f.confidence:.0%}")

        if result.summary.diagram:
            lines.append(f"")
            lines.append(f"## 组件交互图")
            lines.append(f"")
            lines.append(f"```mermaid")
            lines.append(result.summary.diagram)
            lines.append(f"```")

        lines.append(f"")
        path.write_text("\n".join(lines), encoding="utf-8")

    def flush(self) -> None:
        if self._last_path:
            import logging
            logging.getLogger(__name__).info("审查报告已保存: %s", self._last_path)
