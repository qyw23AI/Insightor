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

    # 2. 构建简单的 review prompt
    system = "你是一个代码审查助手。用中文简洁回答。"
    user = f"""请审查以下 PR 变更:

PR 标题: {info.title}
变更文件数: {len(files)}
变更行数: +{info.additions}/-{info.deletions}

Diff:
{diff[:3000]}

请用 3-5 句话总结这个 PR 做了什么。"""

    # 3. 调用 LLM
    handler = LiteLLMHandler(
        timeout=60,
        fallback_models=["deepseek-v4-flash"],
    )

    print("--- 非流式调用 ---")
    resp = await handler.chat_completion(
        model="deepseek-v4-pro",
        system_prompt=system,
        user_prompt=user,
        temperature=0.3,
        max_tokens=512,
    )
    print(f"模型: {resp.model}")
    print(f"耗时: {resp.duration_ms}ms")
    print(f"Token: {resp.usage.prompt_tokens}+{resp.usage.completion_tokens}={resp.usage.total_tokens}")
    print(f"回复: {resp.content}")

    print("\n--- 流式调用 ---")
    chunks = []
    async for chunk in handler.chat_completion_stream(
        model="deepseek-v4-flash",
        system_prompt=system,
        user_prompt="用一句话总结这个 PR。",
        temperature=0.3,
        max_tokens=128,
    ):
        chunks.append(chunk)
        print(chunk, end="", flush=True)
    print(f"\n(流式共 {len(chunks)} chunks)")

    print("\n测试通过!")


if __name__ == "__main__":
    asyncio.run(main())
