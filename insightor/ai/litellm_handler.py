"""LiteLLM Handler — 基于 litellm 的多模型统一调用。

支持:
  - OpenAI (gpt-4o, gpt-4o-mini, o3-mini, ...)
  - Anthropic (claude-sonnet-4-6, claude-haiku-4-5, ...)
  - DeepSeek (deepseek-v3, deepseek-reasoner, ...)
  - 及 litellm 支持的所有供应商

特性:
  - 指数退避重试 (最多 3 次)
  - Fallback 模型链
  - 超时控制 (默认 120s)
  - 流式 + 非流式
"""

import asyncio
import logging
import os
import time
from typing import AsyncIterator

from dotenv import load_dotenv

from insightor.ai.types import AIResponse, TokenUsage

load_dotenv()
logger = logging.getLogger(__name__)

# 模型前缀路由
_MODEL_PREFIX_MAP = {
    "claude-": "anthropic/",
    "sonnet-": "anthropic/claude-",
    "haiku-":  "anthropic/claude-",
    "opus-":   "anthropic/claude-",
}

DEFAULT_TIMEOUT = 120
MAX_RETRIES = 3


class LiteLLMHandler:
    """基于 litellm 的多模型 LLM 调用器。"""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        fallback_models: list[str] | None = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.fallback_models = fallback_models or []

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    async def chat_completion(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AIResponse:
        resolved = self._resolve_model(model)
        messages = self._build_messages(system_prompt, user_prompt)
        t0 = time.time()

        try:
            response = await self._call_with_retry(
                model=resolved, messages=messages,
                temperature=temperature, max_tokens=max_tokens,
                stream=False,
            )
        except Exception as e:
            if self.fallback_models:
                logger.warning("主模型 %s 失败，尝试 fallback: %s", resolved, e)
                return await self._try_fallback(
                    system_prompt, user_prompt, temperature, max_tokens
                )
            return AIResponse(finish_reason="error", duration_ms=int((time.time() - t0) * 1000))

        content = _extract_content(response)
        usage = _extract_usage(response)
        return AIResponse(
            content=content,
            model=response.get("model", resolved),
            finish_reason=response.get("finish_reason", "stop"),
            usage=usage,
            duration_ms=int((time.time() - t0) * 1000),
        )

    async def chat_completion_stream(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        resolved = self._resolve_model(model)
        messages = self._build_messages(system_prompt, user_prompt)

        try:
            response = await self._call_with_retry(
                model=resolved, messages=messages,
                temperature=temperature, max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
        except Exception as e:
            logger.warning("流式调用失败: %s", e)
            if self.fallback_models:
                fallback = self.fallback_models[0]
                resolved_fb = self._resolve_model(fallback)
                try:
                    response = await self._call_with_retry(
                        model=resolved_fb, messages=messages,
                        temperature=temperature, max_tokens=max_tokens,
                        stream=True,
                    )
                    async for chunk in response:
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                except Exception:
                    return

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    async def _call_with_retry(self, **kwargs) -> dict:
        """指数退避重试。"""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return await asyncio.wait_for(
                    self._do_call(**kwargs),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                last_error = TimeoutError(f"超时 ({self.timeout}s)")
            except Exception as e:
                last_error = e
                if "rate" in str(e).lower() or "429" in str(e):
                    wait = 2 ** (attempt + 2)  # 4s, 8s, 16s
                    logger.info("Rate limited, 等待 %ds...", wait)
                    await asyncio.sleep(wait)
                    continue
            if attempt < self.max_retries:
                wait = 2 ** attempt
                logger.debug("重试 %d/%d (等待 %ds): %s", attempt + 1, self.max_retries, wait, last_error)
                await asyncio.sleep(wait)
        raise last_error or RuntimeError("LLM call failed")

    async def _do_call(self, model, messages, temperature, max_tokens, stream, **kw):
        import litellm
        litellm.drop_params = True
        return await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kw,
        )

    async def _try_fallback(
        self, system_prompt: str, user_prompt: str,
        temperature: float, max_tokens: int,
    ) -> AIResponse:
        """Fallback 直接调用 _call_with_retry，避免递归进入 chat_completion 的 fallback 逻辑。"""
        import time
        for fb_model in self.fallback_models:
            try:
                resolved = self._resolve_model(fb_model)
                messages = self._build_messages(system_prompt, user_prompt)
                t0 = time.time()
                response = await self._call_with_retry(
                    model=resolved, messages=messages,
                    temperature=temperature, max_tokens=max_tokens,
                    stream=False,
                )
                content = _extract_content(response)
                usage = _extract_usage(response)
                return AIResponse(
                    content=content,
                    model=response.get("model", resolved),
                    finish_reason=response.get("finish_reason", "stop"),
                    usage=usage,
                    duration_ms=int((time.time() - t0) * 1000),
                )
            except Exception as e:
                logger.warning("Fallback %s 也失败: %s", fb_model, e)
                continue
        return AIResponse(finish_reason="error")

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_model(model: str) -> str:
        """自动添加 litellm 供应商前缀。"""
        # 已含前缀的直接返回
        if "/" in model:
            return model
        # DeepSeek
        if "deepseek" in model.lower():
            return f"deepseek/{model}"
        # Anthropic Claude
        for prefix, resolved in _MODEL_PREFIX_MAP.items():
            if model.lower().startswith(prefix):
                return f"{resolved}{model}"
        # OpenAI (默认)
        if any(model.lower().startswith(p) for p in ("gpt-", "o1", "o3", "o4")):
            return f"openai/{model}"
        return model

    @staticmethod
    def _build_messages(system_prompt: str, user_prompt: str) -> list[dict]:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": user_prompt})
        return msgs


def _extract_usage(response) -> "TokenUsage":
    """从 litellm 响应中提取 token 用量。"""
    # 1. dict 路径
    if isinstance(response, dict):
        u = response.get("usage", {})
        if u:
            return TokenUsage(
                prompt_tokens=u.get("prompt_tokens", 0) or 0,
                completion_tokens=u.get("completion_tokens", 0) or 0,
                total_tokens=u.get("total_tokens", 0) or 0,
            )
    # 2. 对象属性路径
    if hasattr(response, "usage") and response.usage:
        return TokenUsage(
            prompt_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(response.usage, "total_tokens", 0) or 0,
        )
    return TokenUsage()


def _extract_content(response) -> str:
    """从 litellm 响应中提取文本内容。

    litellm 返回的完整结构:
      {"choices": [{"message": {"content": "...", "role": "assistant"}}], ...}
    DeepSeek reasoning 模型可能还有 reasoning_content 字段。
    """
    # 1. 标准路径: choices[0].message.content
    try:
        choices = response.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            # DeepSeek reasoning 模型：如果 content 为空，取 reasoning_content
            if not content:
                content = msg.get("reasoning_content", "")
            if content:
                return content
    except (IndexError, AttributeError, KeyError):
        pass

    # 2. 顶部 content 字段 (某些简化模式)
    if response.get("content"):
        return response["content"]

    # 3. 尝试直接访问 (ModelResponse 对象)
    try:
        choice = response.choices[0]
        if hasattr(choice, "message"):
            content = choice.message.content or ""
            if not content and hasattr(choice.message, "reasoning_content"):
                content = choice.message.reasoning_content or ""
            if content:
                return content
    except Exception:
        pass

    return ""
