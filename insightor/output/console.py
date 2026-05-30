"""ConsoleOutput — Rich 美化终端输出。"""

from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from insightor.schemas.urf import MergeRecommendation, ReviewResult, Severity

_SEVERITY_STYLE = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "yellow",
    Severity.MEDIUM: "blue",
    Severity.LOW: "dim",
    Severity.INFO: "dim italic",
}


class ConsoleOutput:
    """使用 Rich 库将 ReviewResult 美化输出到终端。"""

    def __init__(self, console: Console | None = None):
        self._console = console or Console()

    def post(self, result: ReviewResult) -> None:
        c = self._console
        s = result.summary
        mr = result.merge_readiness

        # ---- Header ----
        pr_type = s.pr_type.upper() if s.pr_type else "REVIEW"
        c.print()
        c.print(Panel(
            f"[bold]{pr_type}[/bold]  {s.overview or '审查完成'}",
            title="Insightor Review",
            border_style="cyan",
        ))

        # ---- Merge Readiness ----
        if mr:
            score_color = "green" if mr.score >= 80 else "yellow" if mr.score >= 50 else "red"
            c.print(f"  综合评分: [{score_color}]{mr.score:.0f}[/{score_color}]  [{mr.recommendation.value}]")
            if mr.blocking_issues:
                c.print(f"  [red]阻断问题: {len(mr.blocking_issues)}[/red]")
            if mr.summary:
                c.print(f"  {mr.summary}")

        # ---- Files ----
        if result.file_walkthrough:
            c.print()
            ft = Table(title="变更文件", show_header=True, header_style="bold")
            ft.add_column("操作", width=10)
            ft.add_column("文件", width=40)
            ft.add_column("说明", width=40)
            for fw in result.file_walkthrough:
                ft.add_row(fw.edit_type.value, fw.path, fw.summary[:80])
            c.print(ft)

        # ---- Findings ----
        if result.findings:
            c.print()
            ft = Table(title=f"发现 ({len(result.findings)})", show_header=True, header_style="bold")
            ft.add_column("#", width=3)
            ft.add_column("严重", width=10)
            ft.add_column("类别", width=12)
            ft.add_column("标题", width=40)
            ft.add_column("文件:行", width=25)
            for i, f in enumerate(result.findings, 1):
                style = _SEVERITY_STYLE.get(f.severity, "")
                ft.add_row(
                    str(i),
                    f"[{style}]{f.severity.value}[/{style}]",
                    f.category,
                    f.title[:60],
                    f"{f.location.path}:{f.location.range.start.line}",
                )
            c.print(ft)

            # Detail for each finding
            for i, f in enumerate(result.findings, 1):
                c.print(f"  [{i}] [bold]{f.title}[/bold]")
                if f.description:
                    c.print(f"      {f.description[:120]}")
                if f.suggestion and f.suggestion.suggested_code:
                    c.print(f"      建议: {f.suggestion.suggested_code[:100]}")

        c.print()

    def flush(self) -> None:
        pass
