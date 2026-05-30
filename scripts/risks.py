"""Insightor Risks — PR 风险代码识别工具。

用法:
  python scripts/risks.py <PR_URL>
  python scripts/risks.py <PR_URL> --depth quick|standard|deep
  python scripts/risks.py <PR_URL> --focus security,concurrency
  python scripts/risks.py <PR_URL> --debug
"""

import asyncio
import sys
from dotenv import load_dotenv
load_dotenv()

from insightor.pipeline import ReviewPipeline


async def main():
    args = sys.argv[1:]
    pr_url = args[0] if args else "https://github.com/SCU-GuGuGaGa/Insightor/pull/2"
    depth = "standard"
    debug = "--debug" in args
    focus_categories = None

    for i, a in enumerate(args):
        if a == "--depth" and i + 1 < len(args):
            depth = args[i + 1]
        elif a == "--focus" and i + 1 < len(args):
            focus_categories = [x.strip() for x in args[i + 1].split(",")]

    if debug:
        from insightor.ai.litellm_handler import LiteLLMHandler
        from insightor.ai.prompt_builder import PromptBuilder
        from insightor.processing.diff_compressor import DiffCompressor
        from insightor.processing.file_filter import FileFilter
        from insightor.processing.language_detector import LanguageDetector
        from insightor.providers.github_provider import GitHubProvider

        print("=" * 60)
        print(f"  DEBUG MODE: risks tool")
        print("=" * 60)

        p = GitHubProvider()
        info = p.get_pr_info(pr_url)
        raw_files = p.get_files(pr_url)
        print(f"\n[1] PR: {info.title}")
        print(f"    文件数: {len(raw_files)}  +{info.additions}/-{info.deletions}")

        ff = FileFilter()
        ld = LanguageDetector()
        files = ff.filter(raw_files)
        sorted_files = ld.sort_by_priority(files, main_language=ReviewPipeline._detect_main_lang(ld, files))
        print(f"\n[2] 过滤: {len(raw_files)} -> {len(files)}  语言: {ReviewPipeline._detect_main_lang(ld, files)}")

        from insightor.schemas.urf import AnalysisDepth
        depth_enum = AnalysisDepth(depth)
        dc = DiffCompressor(max_tokens=ReviewPipeline._calc_budget(depth_enum))
        compressed = dc.compress(sorted_files, depth=depth)
        print(f"[3] 压缩: level={compressed.level}  tokens~{compressed.tokens_used}  text={len(compressed.text)}chars  skipped={len(compressed.unprocessed_files)}")

        file_list = "\n".join(
            f"  [{f.edit_type.value}] {f.filename}" for f in sorted_files[:30]
        )
        commits = p.get_commits(pr_url)
        commit_text = "\n".join(
            f"{c.sha[:8]} {c.message.split(chr(10))[0][:60]}" for c in commits[:5]
        )
        builder = PromptBuilder()
        sys_p, usr_p = builder.build("risks", {
            "title": info.title, "description": info.description,
            "branch": info.branch, "base_branch": info.base_branch,
            "author": info.author, "additions": info.additions,
            "deletions": info.deletions, "files_changed": info.files_changed,
            "diff": compressed.text, "file_list": file_list,
            "commit_messages": commit_text,
            "focus_categories": focus_categories,
        })
        print(f"[4] Prompt: system={len(sys_p)}chars user={len(usr_p)}chars")
        print(f"    --- DIFF (前300字) ---")
        print(compressed.text[:300].replace("\n", "\n    "))
        print(f"    --- PROMPT 尾部 ---")
        print(usr_p[-300:].replace("\n", "\n    "))

        handler = LiteLLMHandler(fallback_models=["deepseek-v4-flash"])
        resp = await handler.chat_completion(
            model="deepseek-v4-flash", system_prompt=sys_p, user_prompt=usr_p,
            temperature=0.3, max_tokens=8192,
        )
        print(f"\n[5] LLM: {resp.model} {resp.duration_ms}ms")
        print(f"    usage: prompt={resp.usage.prompt_tokens} completion={resp.usage.completion_tokens} total={resp.usage.total_tokens}")
        print(f"    finish: {resp.finish_reason}")
        print(f"    content 长度: {len(resp.content)} chars")
        print(f"    --- 前300字 ---")
        print(resp.content[:300])
        print(f"    --- 后300字 ---")
        print(resp.content[-300:])
        return

    # ---- 正常模式 ----
    pipeline = ReviewPipeline()

    def progress(msg):
        print(f"  {msg}")

    print(f"Insightor [risks] depth={depth}")
    if focus_categories:
        print(f"Focus: {', '.join(focus_categories)}")
    print(f"PR: {pr_url}\n")

    from insightor.config.loader import config
    original_focus = config.get("review.focus_categories", None)

    result = await pipeline.run(
        pr_url=pr_url, tool="risks", depth=depth, on_progress=progress,
    )

    print(f"\n{'=' * 60}")
    print(f"  风险分析结果")
    print(f"{'=' * 60}\n")

    if result.findings:
        print(f"发现 ({result.stats.total_findings}):")
        for f in result.findings:
            icon = {"critical": "!!", "high": "! ", "medium": "· ", "low": "  "}.get(f.severity.value, "  ")
            print(f"  {icon} [{f.severity.value:8}] [{f.category:12}] {f.title}")
            print(f"      {f.location.path}:{f.location.range.start.line}  (置信度: {f.confidence:.0%})")
            if f.description:
                print(f"      {f.description[:100]}")
    else:
        print("未发现明显风险。")

    if result.merge_readiness:
        mr = result.merge_readiness
        print(f"\n合并建议: {mr.recommendation.value} (评分: {mr.score:.0f}/100)")
        print(f"审查优先级: {mr.review_priority}")
        if mr.blocking_issues:
            print(f"阻断问题:")
            for bi in mr.blocking_issues:
                print(f"  ! {bi}")
        print(f"预估审查时间: {mr.estimated_review_time_min} min")
        if mr.summary:
            print(f"\n{mr.summary}")

    print(f"\n耗时: {result.meta.duration_ms}ms | Token: {result.meta.tokens_used} | 模型: {result.meta.model}")


if __name__ == "__main__":
    asyncio.run(main())
