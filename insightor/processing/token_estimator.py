"""Token 估算器 —— tiktoken 精确计数 + 非 OpenAI 模型估算。"""

import logging

logger = logging.getLogger(__name__)

# 已知模型的估算系数 (token ≈ chars × factor)
_MODEL_FACTORS: dict[str, float] = {
    "claude": 0.30,
    "deepseek": 0.35,
    "gpt-4": 0.30,
    "gpt-3.5": 0.30,
}
_DEFAULT_FACTOR = 0.30

# tiktoken 编码器缓存
_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            import tiktoken
            _encoder = tiktoken.get_encoding("o200k_base")
        except Exception:
            _encoder = False  # 标记为不可用
    return _encoder if _encoder is not False else None


class TokenEstimator:
    """Token 数量估算。

    对 OpenAI 系列模型使用 tiktoken 精确计数；
    对其他模型使用字符数 × 估算系数。
    """

    def __init__(self, model: str = "", factor: float | None = None):
        self.model = model.lower()
        self.factor = factor or self._get_factor()

    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        enc = _get_encoder()
        if enc and ("gpt" in self.model or "o1" in self.model or "o3" in self.model or "o4" in self.model):
            try:
                return len(enc.encode(text))
            except Exception:
                pass
        return self._estimate(text)

    def _estimate(self, text: str) -> int:
        return max(1, int(len(text) * self.factor))

    def _get_factor(self) -> float:
        for prefix, f in _MODEL_FACTORS.items():
            if self.model.startswith(prefix):
                return f
        return _DEFAULT_FACTOR

    @staticmethod
    def estimate_quick(text: str, factor: float = _DEFAULT_FACTOR) -> int:
        """快速估算（不初始化 model）。"""
        return max(1, int(len(text) * factor))
