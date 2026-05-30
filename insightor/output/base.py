"""OutputService 协议与 CompositeOutput 组合器。

参考 reviewdog 的 CommentService 模式：高度抽象，便于扩展多平台输出。
"""

from typing import Protocol

from insightor.schemas.urf import ReviewResult


class OutputService(Protocol):
    """输出服务抽象 —— 将 ReviewResult 发布到目标媒介。"""

    def post(self, result: ReviewResult) -> None:
        """发布审查结果。"""
        ...

    def flush(self) -> None:
        """确保所有内容已写出（关闭文件句柄等）。"""
        ...


class CompositeOutput:
    """组合多个 OutputService，遍历调用。"""

    def __init__(self, services: list[OutputService] | None = None):
        self._services: list[OutputService] = services or []

    def add(self, service: OutputService) -> None:
        self._services.append(service)

    def post(self, result: ReviewResult) -> None:
        import logging
        import traceback
        _log = logging.getLogger(__name__)
        for svc in self._services:
            try:
                svc.post(result)
            except Exception:
                _log.exception("OutputService %s 写入失败", type(svc).__name__)
                traceback.print_exc()

    def flush(self) -> None:
        for svc in self._services:
            try:
                svc.flush()
            except Exception:
                pass
