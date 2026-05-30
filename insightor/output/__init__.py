"""Insightor Output Layer — 多路输出与反馈闭环。

提供:
  - OutputService 协议 + CompositeOutput 组合器
  - ConsoleOutput: Rich 终端美化
  - MarkdownFileOutput: 结构化审查报告
  - GitHubCommentOutput: PR 评论发布
  - JSONOutput: ReviewResult 持久化
  - FingerprintGenerator: SHA256 去重指纹
"""

from insightor.output.base import CompositeOutput, OutputService
from insightor.output.console import ConsoleOutput
from insightor.output.fingerprint import FingerprintGenerator
from insightor.output.github_comment import GitHubCommentOutput
from insightor.output.json_output import JSONOutput
from insightor.output.markdown import MarkdownFileOutput

__all__ = [
    "OutputService",
    "CompositeOutput",
    "ConsoleOutput",
    "MarkdownFileOutput",
    "GitHubCommentOutput",
    "JSONOutput",
    "FingerprintGenerator",
]
