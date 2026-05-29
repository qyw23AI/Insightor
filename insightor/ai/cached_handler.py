"""CachedAIHandler — 基于 (model + prompt) SHA256 的 LLM 响应缓存。

用于:
  - 避免对相同 prompt 重复调用 LLM（同一 PR 同一 SHA 的重复分析）
  - 减少 API 成本
"""

import hashlib
import json
from pathlib import Path
from typing import AsyncIterator

from insightor.ai.types import AIHandler, AIResponse


class CachedAIHandler:
    """装饰器模式：缓存 AI 响应，避免重复 LLM 调用。"""

    def __init__(self, handler: AIHandler, cache_dir: str = ".insightor/ai_cache"):
        self._handler = handler
        self._cache_dir = Path(cache_dir)

    async def chat_completion(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AIResponse:
        key = _make_key(model, system_prompt, user_prompt)
        cached = self._read_cache(key)
        if cached is not None:
            cached.duration_ms = 0  # 缓存命中，耗时为 0
            return cached

        response = await self._handler.chat_completion(
            model=model, system_prompt=system_prompt, user_prompt=user_prompt,
            temperature=temperature, max_tokens=max_tokens,
        )
        if response.finish_reason != "error":
            self._write_cache(key, response)
        return response

    async def chat_completion_stream(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        # 流式调用不缓存（因为无法预先知道完整内容）
        async for chunk in self._handler.chat_completion_stream(
            model=model, system_prompt=system_prompt, user_prompt=user_prompt,
            temperature=temperature, max_tokens=max_tokens,
        ):
            yield chunk

    # ------------------------------------------------------------------

    def _cache_path(self, key: str) -> Path:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        return self._cache_dir / f"{key}.json"

    def _read_cache(self, key: str) -> AIResponse | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return AIResponse(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def _write_cache(self, key: str, response: AIResponse) -> None:
        try:
            self._cache_path(key).write_text(
                json.dumps({
                    "content": response.content,
                    "model": response.model,
                    "finish_reason": response.finish_reason,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                    "duration_ms": response.duration_ms,
                }, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass


def _make_key(model: str, system: str, user: str) -> str:
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(system.encode())
    h.update(user.encode())
    return h.hexdigest()[:16]
