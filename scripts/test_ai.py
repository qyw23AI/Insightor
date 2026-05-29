"""测试 AI Handler — 用真实 LLM 进行代码审查。

用法:
  python scripts/test_ai.py
  python scripts/test_ai.py <PR_URL>
"""

import asyncio
import sys
from dotenv import load_dotenv
load_dotenv()

from insightor.providers.github_provider import GitHubProvider
from insightor.ai.litellm_handler import LiteLLMHandler


async def main():
    pr_url = sys.argv[1] if len(sys.argv) > 1 else "https://github.com/SCU-GuGuGaGa/Insightor/pull/5"

    # 1. 拉取 PR
    p = GitHubProvider()
    info = p.get_pr_info(pr_url)
    files = p.get_files(pr_url)
    diff = p.get_diff(pr_url).decode("utf-8", errors="replace")

    print(f"PR: {info.title}")
    print(f"文件: {len(files)}, Diff: {len(diff)} chars\n")

    # 2. 构建 review prompt
    system = "你是一个资深代码审查员。用中文回答，简洁专业。"
    # 展示每个文件概要，diff 取前 8000 字符
    file_list = "\n".join(f"  [{f.edit_type.value}] {f.filename} (+{f.num_plus_lines}/-{f.num_minus_lines})" for f in files[:15])
    user = f"""请审查以下 PR:

PR 标题: {info.title}
分支: {info.branch} → {info.base_branch}
作者: {info.author}
变更: +{info.additions}/-{info.deletions} ({info.files_changed} 个文件)

变更文件:
{file_list}

Diff (前 8000 字符):
{diff[:8000]}

请分析:
1. 这个 PR 做了什么? (2-3 句话)
2. 有没有明显的代码问题? (列出 1-2 个, 没有就说"无明显问题")
3. 整体评价 (1 句话)"""

    # 3. 调用 LLM
    handler = LiteLLMHandler(timeout=90, fallback_models=["deepseek-v4-flash"])

    print("--- 非流式调用 ---")
    resp = await handler.chat_completion(
        model="deepseek-v4-pro",
        system_prompt=system,
        user_prompt=user,
        temperature=0.3,
        max_tokens=1024,
    )
    print(f"模型: {resp.model}  耗时: {resp.duration_ms}ms  Token: {resp.usage.prompt_tokens}+{resp.usage.completion_tokens}={resp.usage.total_tokens}")
    print(f"回复:\n{resp.content}")

    print("\n--- 流式调用 ---")
    stream_system = "你是一个代码审查助手。简洁回答。"
    stream_user = f"审查这个 PR 的一句话总结: {info.title} (+{info.additions}/-{info.deletions}, {len(files)} 文件)"
    print("回复: ", end="", flush=True)
    async for chunk in handler.chat_completion_stream(
        model="deepseek-v4-flash",
        system_prompt=stream_system,
        user_prompt=stream_user,
        temperature=0.3,
        max_tokens=256,
    ):
        print(chunk, end="", flush=True)
    print(f"\n(流式完成)")

    print("\n测试通过!")


if __name__ == "__main__":
    asyncio.run(main())
