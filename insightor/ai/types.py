"""AI 层数据类型。"""

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class AIResponse:
    content: str = ""
    model: str = ""
    finish_reason: str = ""   # "stop" | "length" | "error"
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_ms: int = 0


class AIHandler(Protocol):
    """LLM 调用抽象 —— 所有模型供应商的统一接口。"""

    async def chat_completion(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AIResponse:
        """发送 prompt，获取完整响应。"""
        ...

    async def chat_completion_stream(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """流式调用，逐 token yield。"""
        ...
