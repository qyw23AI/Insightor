"""完整 Review 流程测试 — 拉取 PR → 构建 Prompt → 调用 LLM → 解析结果。

用法:
  python scripts/test_review.py <PR_URL>
"""

import asyncio
import sys
from dotenv import load_dotenv
load_dotenv()

from insightor.providers.github_provider import GitHubProvider
from insightor.processing.file_filter import FileFilter
from insightor.processing.diff_compressor import DiffCompressor
from insightor.ai.litellm_handler import LiteLLMHandler
from insightor.ai.prompt_builder import PromptBuilder
from insightor.ai.response_parser import ResponseParser
from insightor.schemas.urf import ReviewMeta


async def main():
    pr_url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/SCU-GuGuGaGa/Insightor/pull/2"

    # 1. 拉取数据
    print("=" * 60)
    print("[1/5] 拉取 PR 数据...")
    p = GitHubProvider()
    info = p.get_pr_info(pr_url)
    raw_files = p.get_files(pr_url)
    print(f"  PR #{info.pr_number}: {info.title}")
    print(f"  文件: {len(raw_files)}  +{info.additions}/-{info.deletions}")

    # 2. 过滤 + 压缩
    print("[2/5] 处理 diff...")
    ff = FileFilter()
    files = ff.filter(raw_files)
    dc = DiffCompressor(max_tokens=8000)
    compressed = dc.compress(files, depth="standard")
    print(f"  过滤: {len(raw_files)} → {len(files)}  压缩: level={compressed.level}, tokens={compressed.tokens_used}")

    # 3. 构建 Prompt
    print("[3/5] 构建 prompt...")
    builder = PromptBuilder()
    commit_text = "\n".join(f"{c.sha[:8]} {c.message.split(chr(10))[0][:60]}" for c in p.get_commits(pr_url)[:5])
    system, user = builder.build("review", {
        "title": info.title,
        "description": info.description,
        "branch": info.branch,
        "base_branch": info.base_branch,
        "author": info.author,
        "additions": info.additions,
        "deletions": info.deletions,
        "files_changed": info.files_changed,
        "diff": compressed.text,
        "commit_messages": commit_text,
    })
    print(f"  system: {len(system)} chars  user: {len(user)} chars")

    # 4. 调用 LLM
    print("[4/5] AI 分析中...")
    # 使用 v4-flash: 无推理模式, 直接输出 JSON
    # v4-pro 会消耗大量 token 做思维链推理, 适合复杂逻辑分析
    handler = LiteLLMHandler(timeout=120, fallback_models=["deepseek-v4-flash"])
    resp = await handler.chat_completion(
        model="deepseek-v4-flash",
        system_prompt=system,
        user_prompt=user,
        temperature=0.3,
        max_tokens=4096,
    )
    print(f"  模型: {resp.model}  耗时: {resp.duration_ms}ms")
    print(f"  Token: {resp.usage.prompt_tokens}+{resp.usage.completion_tokens}={resp.usage.total_tokens}")
    # debug: 看 LLM 原始返回
    print(f"  响应长度: {len(resp.content)} chars")
    print(f"  前200字: {resp.content[:200]}")
    print(f"  后300字: {resp.content[-300:]}")

    # 5. 解析结果
    print("[5/5] 解析结果...")
    meta = ReviewMeta(
        pr_url=pr_url, commit_sha=info.commit_sha,
        files_analyzed=len(files), files_skipped=len(compressed.unprocessed_files),
    )
    result = ResponseParser.parse(resp.content, meta)
    print(f"  Findings: {result.stats.total_findings}")
    print(f"  严重度分布: {result.stats.by_severity}")
    print(f"  合并建议: {result.merge_readiness.recommendation.value if result.merge_readiness else 'N/A'}")
    print(f"  评分: {result.merge_readiness.score if result.merge_readiness else 'N/A'}")

    # 展示结果
    print("\n" + "=" * 60)
    print(f"PR 总结: [{result.summary.pr_type}] {result.summary.overview}")
    print("=" * 60)
    for f in result.findings:
        print(f"  [{f.severity.value:8}] [{f.category:12}] {f.title}")
        print(f"    位置: {f.location.path}:{f.location.range.start.line}")
        print(f"    置信度: {f.confidence}")
        if f.suggestion and f.suggestion.suggested_code:
            print(f"    建议: {f.suggestion.suggested_code[:100]}")
        print()

    if result.merge_readiness:
        print(f"合并建议: {result.merge_readiness.recommendation.value} (评分: {result.merge_readiness.score})")
        print(f"  {result.merge_readiness.summary}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
