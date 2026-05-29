"""Insightor Describe — PR 变更总结工具。

用法:
  python scripts/describe.py <PR_URL>
  python scripts/describe.py <PR_URL> --depth quick|standard|deep
  python scripts/describe.py <PR_URL> --debug
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

    for i, a in enumerate(args):
        if a == "--depth" and i + 1 < len(args):
            depth = args[i + 1]

    if debug:
        from insightor.ai.litellm_handler import LiteLLMHandler
        from insightor.ai.prompt_builder import PromptBuilder
        from insightor.processing.diff_compressor import DiffCompressor
        from insightor.processing.file_filter import FileFilter
        from insightor.processing.language_detector import LanguageDetector
        from insightor.providers.github_provider import GitHubProvider

        print("=" * 60)
        print(f"  DEBUG MODE: describe tool")
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
        builder = PromptBuilder()
        sys_p, usr_p = builder.build("describe", {
            "title": info.title, "description": info.description,
            "branch": info.branch, "base_branch": info.base_branch,
            "author": info.author, "additions": info.additions,
            "deletions": info.deletions, "files_changed": info.files_changed,
            "diff": compressed.text, "file_list": file_list,
            "commit_messages": "",
        })
        print(f"[4] Prompt: system={len(sys_p)}chars user={len(usr_p)}chars")
        print(f"    --- DIFF (前300字) ---")
        print(compressed.text[:300].replace("\n", "\n    "))
        print(f"    --- PROMPT 尾部 ---")
        print(usr_p[-300:].replace("\n", "\n    "))

        handler = LiteLLMHandler(fallback_models=["deepseek-v4-flash"])
        resp = await handler.chat_completion(
            model="deepseek-v4-flash", system_prompt=sys_p, user_prompt=usr_p,
            temperature=0.3, max_tokens=2048,
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

    print(f"Insightor [describe] depth={depth}")
    print(f"PR: {pr_url}\n")

    result = await pipeline.run(pr_url=pr_url, tool="describe", depth=depth, on_progress=progress)

    print(f"\n{'=' * 60}")
    print(f"  {result.summary.pr_type.upper()} | {result.summary.overview}")
    print(f"{'=' * 60}\n")

    if result.file_walkthrough:
        print(f"变更文件 ({len(result.file_walkthrough)}):")
        for fw in result.file_walkthrough:
            print(f"  [{fw.edit_type.value:8}] {fw.path}")
            if fw.summary:
                print(f"         {fw.summary}")
    else:
        print("无文件变更信息。")

    if result.summary.diagram:
        print(f"\n--- 组件交互流程图 ---")
        print(result.summary.diagram)

    print(f"\n耗时: {result.meta.duration_ms}ms | Token: {result.meta.tokens_used} | 模型: {result.meta.model}")


if __name__ == "__main__":
    asyncio.run(main())
