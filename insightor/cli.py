"""Insightor CLI — Unified command-line interface for AI-powered PR review.

Usage:
  insightor full <pr_url> [--depth quick|standard|deep] [--skip describe|risks|improve|review]
  insightor review <pr_url> [--depth quick|standard|deep] [--incremental] [--debug]
  insightor describe <pr_url> [--depth quick|standard|deep] [--debug]
  insightor risks <pr_url> [--depth quick|standard|deep] [--focus security] [--debug]
  insightor improve <pr_url> [--depth quick|standard|deep] [--committable-only] [--debug]
  insightor publish <md_path> [--dry-run] [--json <path>]
"""

import asyncio
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()


# =============================================================================
# Main group
# =============================================================================

@click.group()
@click.version_option(package_name="insightor")
def main():
    """Insightor — AI-powered PR review assistant.

    Analyze GitHub pull requests with LLM-powered code review,
    risk detection, PR description generation, and improvement suggestions.
    """


# =============================================================================
# review
# =============================================================================

@main.command()
@click.argument("pr_url")
@click.option(
    "--depth", default="standard",
    type=click.Choice(["quick", "standard", "deep"]),
    help="分析深度 (default: standard)"
)
@click.option("--incremental", is_flag=True, help="增量审查模式")
@click.option("--model", default=None, help="覆盖默认模型")
@click.option("--debug", is_flag=True, help="打印中间数据后退出")
def review(pr_url, depth, incremental, model, debug):
    """Run complete code review on a GitHub PR."""
    asyncio.run(_review(pr_url, depth, incremental, model, debug))


async def _review(pr_url, depth, incremental, model, debug):
    if debug:
        await _debug_review(pr_url, depth)
        return

    from insightor.pipeline import ReviewPipeline

    pipeline = ReviewPipeline(model=model) if model else ReviewPipeline()

    with console.status("[bold green]Insightor 分析中...") as status:
        def progress(msg):
            status.update(f"[bold green]{msg}")

        result = await pipeline.run(
            pr_url=pr_url, tool="review", depth=depth,
            incremental=incremental, on_progress=progress,
        )

    mr = result.merge_readiness
    if mr:
        emoji = "✅" if mr.score >= 80 else "⚠️" if mr.score >= 50 else "🔴"
        console.print(
            f"\n{emoji} [bold]完成: {mr.score:.0f}/100 [{mr.recommendation.value}][/bold]  "
            f"{len(result.findings)} 发现  {result.meta.duration_ms}ms  "
            f"model={result.meta.model}"
        )
    else:
        console.print(
            f"\n完成: {result.meta.duration_ms}ms | {result.meta.model}"
        )


# =============================================================================
# describe
# =============================================================================

@main.command()
@click.argument("pr_url")
@click.option(
    "--depth", default="standard",
    type=click.Choice(["quick", "standard", "deep"]),
    help="分析深度"
)
@click.option("--debug", is_flag=True, help="打印中间数据后退出")
def describe(pr_url, depth, debug):
    """Generate a structured PR description with file walkthrough."""
    asyncio.run(_describe(pr_url, depth, debug))


async def _describe(pr_url, depth, debug):
    from insightor.pipeline import ReviewPipeline

    if debug:
        await _debug_tool(pr_url, "describe", depth)
        return

    pipeline = ReviewPipeline()

    with console.status("[bold green]Insightor 分析中...") as status:
        def progress(msg):
            status.update(f"[bold green]{msg}")

        result = await pipeline.run(
            pr_url=pr_url, tool="describe", depth=depth,
            on_progress=progress,
        )

    console.print(
        f"\n✅ [bold]{result.summary.pr_type.upper()}[/bold] — {result.summary.overview}"
    )
    if result.file_walkthrough:
        console.print(f"   {len(result.file_walkthrough)} 个文件  {result.meta.duration_ms}ms")


# =============================================================================
# risks
# =============================================================================

@main.command()
@click.argument("pr_url")
@click.option(
    "--depth", default="standard",
    type=click.Choice(["quick", "standard", "deep"]),
    help="分析深度"
)
@click.option("--focus", default=None, help="关注领域: security, performance, concurrency 等")
@click.option("--debug", is_flag=True, help="打印中间数据后退出")
def risks(pr_url, depth, focus, debug):
    """Identify security, concurrency, and performance risks in a PR."""
    asyncio.run(_risks(pr_url, depth, focus, debug))


async def _risks(pr_url, depth, focus, debug):
    from insightor.pipeline import ReviewPipeline

    if debug:
        await _debug_tool(pr_url, "risks", depth)
        return

    pipeline = ReviewPipeline()

    with console.status("[bold green]Insightor 风险分析中...") as status:
        def progress(msg):
            status.update(f"[bold green]{msg}")

        result = await pipeline.run(
            pr_url=pr_url, tool="risks", depth=depth,
            on_progress=progress,
        )

    mr = result.merge_readiness
    if mr:
        emoji = "✅" if mr.score >= 80 else "⚠️" if mr.score >= 50 else "🔴"
        console.print(
            f"\n{emoji} [bold]风险: {mr.score:.0f}/100[/bold]  "
            f"{len(result.findings)} 发现  {result.meta.duration_ms}ms"
        )
    if focus and result.findings:
        focused = [f for f in result.findings if f.category == focus]
        if focused:
            console.print(f"  --focus {focus}: {len(focused)} 相关发现")


# =============================================================================
# improve — REMOVED (merged into review)
# =============================================================================
# improve 命令已删除。代码改进建议已整合到 review 工具中。
# 使用 insightor full 进行完整审查，review 部分包含可勾选的 feedback checkboxes。

# =============================================================================
# full — run describe + risks + review and produce combined report
# =============================================================================

@main.command()
@click.argument("pr_url")
@click.option(
    "--depth", default="standard",
    type=click.Choice(["quick", "standard", "deep"]),
    help="分析深度 (default: standard)"
)
@click.option("--skip", "-s", multiple=True,
              type=click.Choice(["describe", "risks", "review"]),
              help="跳过指定工具 (可多次使用)")
@click.option("--debug", is_flag=True, help="打印中间数据后退出")
def full(pr_url, depth, skip, debug):
    """Run complete analysis: describe + risks + review.

    Generates a combined Markdown report with clear sections for each tool.
    The review section has feedback checkboxes for human-in-the-loop publishing.
    """
    asyncio.run(_full(pr_url, depth, set(skip), debug))


async def _full(pr_url, depth, skip, debug):
    if debug:
        console.print("[bold yellow]DEBUG MODE — full[/bold yellow]")
        for tool in ["describe", "risks", "review"]:
            if tool in skip:
                continue
            console.print(f"\n{'='*60}")
            console.print(f"  [bold]{tool.upper()}[/bold]")
            console.print("=" * 60)
            await _debug_tool(pr_url, tool, depth)
        return

    from datetime import datetime, timezone
    from pathlib import Path

    from insightor.output.fingerprint import FingerprintGenerator
    from insightor.output.json_output import JSONOutput
    from insightor.pipeline import ReviewPipeline
    from insightor.schemas.urf import ReviewResult

    tools = ["describe", "risks", "review"]
    results: dict[str, ReviewResult] = {}
    total_ms = 0
    pipeline = ReviewPipeline()

    for tool in tools:
        if tool in skip:
            continue

        with console.status(f"[bold green][{tool}] 分析中...") as status:
            def progress(msg):
                status.update(f"[bold green][{tool}] {msg}")

            result = await pipeline.run(
                pr_url=pr_url, tool=tool, depth=depth,
                on_progress=progress, skip_markdown=True,
            )
        results[tool] = result
        total_ms += result.meta.duration_ms

        # Brief per-tool summary
        if tool == "describe":
            console.print(f"  ✅ describe: {result.summary.pr_type} — "
                          f"{len(result.file_walkthrough)} files")
        elif tool == "risks":
            mr = result.merge_readiness
            console.print(f"  ⚠️  risks: {len(result.findings)} findings"
                          f"{f' score={mr.score:.0f}' if mr else ''}")
        elif tool == "review":
            mr = result.merge_readiness
            console.print(f"  📋 review: {len(result.findings)} findings"
                          f"{f' score={mr.score:.0f}' if mr else ''}")

    # Merge: use review's meta as base, combine findings from all tools
    base = results.get("review") or results.get("risks")
    if not base:
        console.print("[red]No tools were run.[/red]")
        return

    # Collect and deduplicate findings
    all_findings = []
    for tool in tools:
        if tool in results:
            all_findings.extend(results[tool].findings)
    deduped = FingerprintGenerator.deduplicate(all_findings)

    # Build merged result
    describe_r = results.get("describe")
    merged = ReviewResult(
        meta=base.meta.model_copy(update={"duration_ms": total_ms}),
        summary=describe_r.summary if describe_r else base.summary,
        file_walkthrough=describe_r.file_walkthrough if describe_r else base.file_walkthrough,
        findings=deduped,
        merge_readiness=base.merge_readiness,
        stats=base.stats.model_copy(update={"total_findings": len(deduped)}),
    )

    # Save combined JSON
    json_out = JSONOutput()
    json_out.post(merged)

    # Build combined markdown
    pr_num = _extract_pr_num_from_url(pr_url)
    fname = f"insightor-full-review-{pr_num}.md"
    md_path = Path(fname)
    md_content = _build_full_markdown(merged, results, pr_url, pr_num)
    md_path.write_text(md_content, encoding="utf-8")

    # Summary
    console.print(f"\n[bold green]Full review complete.[/bold green]")
    console.print(f"  describe: {len(describe_r.file_walkthrough) if describe_r else 0} files")
    console.print(f"  risks:    {len(results.get('risks', ReviewResult(meta=base.meta)).findings)} findings")
    console.print(f"  review:   {len(results.get('review', ReviewResult(meta=base.meta)).findings)} findings")
    console.print(f"  total: {total_ms}ms | {len(deduped)} unique findings (deduplicated)")
    console.print(f"  report: {fname}")
    console.print(f"\n  Edit [bold]{fname}[/bold] to confirm review findings,")
    console.print(f"  then run: [bold]insightor publish {fname}[/bold]")


def _build_full_markdown(merged, results, pr_url, pr_num):
    """Build combined markdown with three sections. Review section has checkboxes."""
    from datetime import datetime, timezone

    from insightor.schemas.urf import Severity

    _SEVERITY_ICON = {
        Severity.CRITICAL: "🔴", Severity.HIGH: "🟡",
        Severity.MEDIUM: "🔵", Severity.LOW: "⚪", Severity.INFO: "ℹ️",
    }

    lines = []
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = merged.meta

    # Header
    lines.append(f"# Insightor Full Review — PR #{pr_num}")
    lines.append("")
    lines.append(f"> 生成时间: {ts} | 模型: {meta.model} | 深度: {meta.analysis_depth.value}")
    lines.append(f"> PR: {pr_url}")
    lines.append("")
    lines.append("---")

    # Section 1: describe
    describe_r = results.get("describe")
    if describe_r:
        s = describe_r.summary
        lines.append("")
        lines.append("## 1. PR 总结 (describe)")
        lines.append("")
        lines.append(f"- **类型**: {s.pr_type or 'N/A'}")
        lines.append(f"- **概述**: {s.overview or '无'}")
        if describe_r.file_walkthrough:
            lines.append("")
            lines.append("### 变更文件")
            lines.append("")
            lines.append("| 操作 | 文件 | 说明 |")
            lines.append("|------|------|------|")
            for fw in describe_r.file_walkthrough:
                lines.append(f"| {fw.edit_type.value} | `{fw.path}` | {fw.summary[:80]} |")
        if s.diagram:
            lines.append("")
            lines.append("### 组件交互图")
            lines.append("")
            lines.append("```mermaid")
            lines.append(s.diagram)
            lines.append("```")
        lines.append("")
        lines.append("---")

    # Helper: safe code fence that won't conflict with backticks in code
    def _fence(text):
        max_run = 0
        cur = 0
        for ch in text:
            if ch == '`':
                cur += 1
                if cur > max_run:
                    max_run = cur
            else:
                cur = 0
        return '`' * max(3, max_run + 1)

    # Section 2: risks
    risks_r = results.get("risks")
    if risks_r:
        mr = risks_r.merge_readiness
        lines.append("")
        lines.append("## 2. 风险分析 (risks)")
        lines.append("")
        if mr:
            score_icon = "✅" if mr.score >= 80 else "⚠️" if mr.score >= 50 else "🔴"
            lines.append(f"- **评分**: {score_icon} {mr.score:.0f}/100 — {mr.recommendation.value}")
            if mr.blocking_issues:
                lines.append(f"- **阻断问题**:")
                for bi in mr.blocking_issues:
                    lines.append(f"  - {bi}")
            if mr.summary:
                lines.append(f"- {mr.summary}")
        if risks_r.findings:
            lines.append("")
            lines.append(f"### 风险发现 ({len(risks_r.findings)})")
            for i, f in enumerate(risks_r.findings, 1):
                icon = _SEVERITY_ICON.get(f.severity, "")
                lines.append("")
                lines.append(f"#### {i}. {icon} [{f.severity.value}] {f.title}")
                lines.append("")
                lines.append(f"- **类别**: {f.category}")
                lines.append(f"- **文件**: `{f.location.path}:{f.location.range.start.line}`")
                if f.description:
                    lines.append(f"- **说明**: {f.description}")
                if f.confidence:
                    lines.append(f"- **置信度**: {f.confidence:.0%}")
        lines.append("")
        lines.append("---")

    # Section 3: review (WITH feedback checkboxes for human-in-the-loop)
    review_r = results.get("review")
    if review_r:
        mr = review_r.merge_readiness
        lines.append("")
        lines.append("## 3. 代码审查 (review)")
        lines.append("")
        if mr:
            score_icon = "✅" if mr.score >= 80 else "⚠️" if mr.score >= 50 else "🔴"
            lines.append(f"- **评分**: {score_icon} {mr.score:.0f}/100 — {mr.recommendation.value}")
            if mr.summary:
                lines.append(f"- {mr.summary}")
        if review_r.findings:
            lines.append("")
            lines.append(f"### 发现 ({len(review_r.findings)})")
            for i, f in enumerate(review_r.findings, 1):
                icon = _SEVERITY_ICON.get(f.severity, "")
                lines.append("")
                lines.append(f"#### {i}. {icon} [{f.severity.value}] {f.title}"
                             f" <!-- finding-id: {f.id} -->")
                lines.append("")
                lines.append(f"- **类别**: {f.category}")
                lines.append(f"- **文件**: `{f.location.path}:{f.location.range.start.line}`")
                if f.description:
                    lines.append(f"- **说明**: {f.description}")
                if f.suggestion:
                    if f.suggestion.current_code:
                        lines.append(f"- **当前代码**:")
                        fc = _fence(f.suggestion.current_code)
                        lines.append(f"  {fc}")
                        lines.append(f"  {f.suggestion.current_code}")
                        lines.append(f"  {fc}")
                    if f.suggestion.suggested_code:
                        lines.append(f"- **建议代码**:")
                        fc = _fence(f.suggestion.suggested_code)
                        lines.append(f"  {fc}")
                        lines.append(f"  {f.suggestion.suggested_code}")
                        lines.append(f"  {fc}")
                if f.confidence:
                    lines.append(f"- **置信度**: {f.confidence:.0%}")
                # Feedback checkboxes
                lines.append("")
                lines.append(f"- [ ] confirmed")
                lines.append(f"- [ ] false_positive")
                lines.append(f"- [ ] addressed")
                lines.append(f"- [ ] ignored")
                lines.append(f"- **审查者:** ")
                lines.append(f"- **备注:** ")
        else:
            lines.append("")
            lines.append("无审查发现。")
        lines.append("")
        lines.append("---")

    # Footer
    pr_num_str = str(pr_num)
    lines.append("")
    lines.append("## 反馈说明")
    lines.append("")
    lines.append("请根据实际情况勾选以上 **代码审查 (第3节)** 的反馈。确认后运行发布脚本:")
    lines.append("")
    lines.append("```bash")
    lines.append(f"insightor publish insightor-full-review-{pr_num_str}.md")
    lines.append("```")
    lines.append("")
    lines.append(f"<!-- insightor-full-review -->")
    lines.append(f"<!-- insightor-pr-url: {pr_url} -->")

    return "\n".join(lines)


def _extract_pr_num_from_url(pr_url):
    parts = pr_url.rstrip("/").split("/")
    if parts and parts[-1].isdigit():
        return parts[-1]
    return "unknown"


# =============================================================================
# publish
# =============================================================================

@main.command()
@click.argument("md_path")
@click.option("--dry-run", is_flag=True, help="仅预览，不发布到 GitHub")
@click.option("--json", "json_path", default=None, help="指定 companion JSON 文件路径")
def publish(md_path, dry_run, json_path):
    """Publish a human-confirmed review draft to GitHub.

    MD_PATH is the path to the edited Markdown review file.
    The PR URL is auto-detected from the file.
    """
    asyncio.run(_publish(md_path, dry_run, json_path))


async def _publish(md_path, dry_run, json_path):
    import re

    from insightor.feedback.draft_parser import DraftParser
    from insightor.feedback.quality_tracker import QualityTracker
    from insightor.output.github_comment import GitHubCommentOutput
    from insightor.output.json_output import JSONOutput
    from insightor.schemas.urf import ReviewResult

    md_file = Path(md_path)
    if not md_file.exists():
        console.print(f"[red]Error:[/red] {md_path} not found")
        sys.exit(1)

    md_text = md_file.read_text(encoding="utf-8")

    # Auto-detect PR URL
    pr_url_match = re.search(r"<!--\s*insightor-pr-url:\s*(https?://\S+)\s*-->", md_text)
    if not pr_url_match:
        console.print(
            "[red]Error:[/red] Could not find PR URL in markdown file. "
            "Ensure the file was generated by the Insightor review pipeline."
        )
        sys.exit(1)
    pr_url = pr_url_match.group(1).strip()

    # Load original result
    original = _load_original_result(md_file, pr_url, json_path)
    if original is None:
        console.print(
            "[red]Error:[/red] Could not find companion JSON review file. "
            "Run the review pipeline first to generate review data."
        )
        sys.exit(1)

    # Parse feedback
    console.print(f"Parsing {md_path} ...")
    updated_result, changes = DraftParser.parse(md_path, original)
    console.print(f"  PR: {pr_url}")
    console.print(f"  Feedback changes detected: {changes}")

    if changes == 0:
        console.print("  No feedback changes found. Nothing to publish.")
        return

    # For full review reports, publish all findings that have feedback
    is_full = "<!-- insightor-full-review -->" in md_text
    if is_full:
        updated_result.findings = [
            f for f in updated_result.findings
            if f.feedback and f.feedback.status is not None
        ]
        console.print(f"  Full review detected — publishing findings with feedback "
                       f"({len(updated_result.findings)} items)")

    if dry_run:
        console.print("\n--- DRY RUN (no changes posted) ---")
        for f in updated_result.findings:
            if f.feedback and f.feedback.status is not None:
                console.print(
                    f"  {f.feedback.status.value:14}  "
                    f"{f.title[:55]}  "
                    f"({f.location.path}:{f.location.range.start.line})"
                )
        console.print("--- end dry run ---")
        return

    # Publish to GitHub
    with console.status("[bold green]Publishing to GitHub..."):
        gh = GitHubCommentOutput(pr_url)
        gh.post(updated_result)
        gh.flush()

    # Save updated result
    json_out = JSONOutput()
    json_out.post(updated_result)

    # Track quality
    tracker = QualityTracker()
    tracker.track(updated_result)
    metrics = tracker.export_metrics()
    if metrics.historical_precision:
        console.print(f"  Quality metrics updated: {metrics.historical_precision}")

    console.print(f"  [green]Done.[/green] Published {changes} feedback changes.")


# =============================================================================
# Debug helpers
# =============================================================================

async def _debug_review(pr_url, depth):
    """Debug mode: print all intermediate pipeline data for the review tool."""
    from insightor.ai.litellm_handler import LiteLLMHandler
    from insightor.ai.prompt_builder import PromptBuilder
    from insightor.pipeline import ReviewPipeline
    from insightor.processing.diff_compressor import DiffCompressor
    from insightor.processing.file_filter import FileFilter
    from insightor.processing.language_detector import LanguageDetector
    from insightor.providers.github_provider import GitHubProvider
    from insightor.schemas.urf import AnalysisDepth

    console.print("=" * 60)
    console.print("  [bold yellow]DEBUG MODE[/bold yellow]")
    console.print("=" * 60)

    p = GitHubProvider()
    info = p.get_pr_info(pr_url)
    raw_files = p.get_files(pr_url)
    console.print(f"\n[1] PR: {info.title}")
    console.print(f"    文件数: {len(raw_files)}  +{info.additions}/-{info.deletions}")

    ff = FileFilter()
    ld = LanguageDetector()
    files = ff.filter(raw_files)
    main_lang = ReviewPipeline._detect_main_lang(ld, files)
    sorted_files = ld.sort_by_priority(files, main_language=main_lang)
    console.print(f"\n[2] 过滤: {len(raw_files)}→{len(files)}  语言: {main_lang}")

    depth_enum = AnalysisDepth(depth)
    dc = DiffCompressor(max_tokens=ReviewPipeline._calc_budget(depth_enum))
    compressed = dc.compress(sorted_files, depth=depth)
    console.print(
        f"[3] 压缩: level={compressed.level} tokens~{compressed.tokens_used}  "
        f"text={len(compressed.text)}chars  skipped={len(compressed.unprocessed_files)}"
    )

    commits = p.get_commits(pr_url)
    builder = PromptBuilder()
    commit_text = "\n".join(
        f"{c.sha[:8]} {c.message.split(chr(10))[0][:60]}" for c in commits[:5]
    )
    file_list = "\n".join(
        f"  [{f.edit_type.value}] {f.filename}" for f in sorted_files[:30]
    )
    sys_p, usr_p = builder.build("review", {
        "title": info.title, "description": info.description,
        "branch": info.branch, "base_branch": info.base_branch,
        "author": info.author, "additions": info.additions,
        "deletions": info.deletions, "files_changed": info.files_changed,
        "diff": compressed.text, "commit_messages": commit_text,
        "file_list": file_list,
    })
    console.print(f"[4] Prompt: system={len(sys_p)}chars user={len(usr_p)}chars")
    console.print(f"    --- DIFF (前300字) ---")
    console.print(compressed.text[:300])
    console.print(f"    --- DIFF (后200字) ---")
    console.print(compressed.text[-200:])
    console.print(f"    --- PROMPT 尾部 ---")
    console.print(usr_p[-300:])

    handler = LiteLLMHandler(fallback_models=["deepseek-v4-flash"])
    resp = await handler.chat_completion(
        model="deepseek-v4-flash", system_prompt=sys_p, user_prompt=usr_p,
        temperature=0.3, max_tokens=8192,
    )
    console.print(f"\n[5] LLM: {resp.model} {resp.duration_ms}ms")
    console.print(
        f"    usage: prompt={resp.usage.prompt_tokens} "
        f"completion={resp.usage.completion_tokens} total={resp.usage.total_tokens}"
    )
    console.print(f"    finish: {resp.finish_reason}")
    console.print(f"    content 长度: {len(resp.content)} chars")
    console.print(f"    --- 前300字 ---")
    console.print(resp.content[:300])
    console.print(f"    --- 后300字 ---")
    console.print(resp.content[-300:])


async def _debug_tool(pr_url, tool, depth):
    """Debug mode: print intermediate data for describe/risks/improve tools."""
    from insightor.ai.litellm_handler import LiteLLMHandler
    from insightor.ai.prompt_builder import PromptBuilder
    from insightor.pipeline import ReviewPipeline
    from insightor.processing.diff_compressor import DiffCompressor
    from insightor.processing.file_filter import FileFilter
    from insightor.processing.language_detector import LanguageDetector
    from insightor.providers.github_provider import GitHubProvider
    from insightor.schemas.urf import AnalysisDepth

    console.print("=" * 60)
    console.print(f"  [bold yellow]DEBUG MODE ({tool})[/bold yellow]")
    console.print("=" * 60)

    p = GitHubProvider()
    info = p.get_pr_info(pr_url)
    raw_files = p.get_files(pr_url)
    console.print(f"\n[1] PR: {info.title}")
    console.print(f"    文件数: {len(raw_files)}  +{info.additions}/-{info.deletions}")

    ff = FileFilter()
    ld = LanguageDetector()
    files = ff.filter(raw_files)
    main_lang = ReviewPipeline._detect_main_lang(ld, files)
    sorted_files = ld.sort_by_priority(files, main_language=main_lang)
    console.print(f"\n[2] 过滤: {len(raw_files)}→{len(files)}  语言: {main_lang}")

    depth_enum = AnalysisDepth(depth)
    dc = DiffCompressor(max_tokens=ReviewPipeline._calc_budget(depth_enum))
    compressed = dc.compress(sorted_files, depth=depth)
    console.print(
        f"[3] 压缩: level={compressed.level} tokens~{compressed.tokens_used}  "
        f"text={len(compressed.text)}chars  skipped={len(compressed.unprocessed_files)}"
    )

    commits = p.get_commits(pr_url)
    builder = PromptBuilder()
    commit_text = "\n".join(
        f"{c.sha[:8]} {c.message.split(chr(10))[0][:60]}" for c in commits[:5]
    )
    file_list = "\n".join(
        f"  [{f.edit_type.value}] {f.filename}" for f in sorted_files[:30]
    )
    sys_p, usr_p = builder.build(tool, {
        "title": info.title, "description": info.description,
        "branch": info.branch, "base_branch": info.base_branch,
        "author": info.author, "additions": info.additions,
        "deletions": info.deletions, "files_changed": info.files_changed,
        "diff": compressed.text, "commit_messages": commit_text,
        "file_list": file_list,
    })
    console.print(f"[4] Prompt: system={len(sys_p)}chars user={len(usr_p)}chars")
    console.print(f"    --- DIFF (前300字) ---")
    console.print(compressed.text[:300])
    console.print(f"    --- PROMPT 尾部 ---")
    console.print(usr_p[-300:])

    handler = LiteLLMHandler(fallback_models=["deepseek-v4-flash"])
    max_tok = 16384 if depth == "deep" else 8192
    resp = await handler.chat_completion(
        model="deepseek-v4-flash", system_prompt=sys_p, user_prompt=usr_p,
        temperature=0.3, max_tokens=max_tok,
    )
    console.print(f"\n[5] LLM: {resp.model} {resp.duration_ms}ms")
    console.print(
        f"    usage: prompt={resp.usage.prompt_tokens} "
        f"completion={resp.usage.completion_tokens} total={resp.usage.total_tokens}"
    )
    console.print(f"    finish: {resp.finish_reason}")
    console.print(f"    content 长度: {len(resp.content)} chars")
    console.print(f"    --- 前300字 ---")
    console.print(resp.content[:300])
    console.print(f"    --- 后300字 ---")
    console.print(resp.content[-300:])


# =============================================================================
# Publish helpers
# =============================================================================

def _load_original_result(md_file: Path, pr_url: str, explicit_json: str | None) -> object | None:
    """Load the companion JSON result file for a markdown draft."""
    import re

    from insightor.schemas.urf import ReviewResult

    if explicit_json:
        path = Path(explicit_json)
        if path.exists():
            return ReviewResult.model_validate_json(path.read_text(encoding="utf-8"))
        return None

    pr_num = None
    m = re.search(r"insightor-(?:full-)?review-(\d+)", md_file.name)
    if m:
        pr_num = m.group(1)
    else:
        parts = pr_url.rstrip("/").split("/")
        if parts and parts[-1].isdigit():
            pr_num = parts[-1]

    if pr_num is None:
        return None

    reviews_dir = Path(".insightor/reviews")
    if not reviews_dir.exists():
        return None

    candidates = sorted(reviews_dir.glob(f"insightor-review-{pr_num}-*.json"))
    if not candidates:
        return None

    return ReviewResult.model_validate_json(candidates[-1].read_text(encoding="utf-8"))
