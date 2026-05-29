"""GitProvider 和 DiffService 协议定义。

参考 reviewdog 的 CommentService/DiffService 接口模式：
高度抽象，仅定义必要方法，便于未来扩展多平台。
"""

from typing import Protocol

from insightor.providers.types import CommitInfo, FilePatchInfo, IssueInfo, PRInfo


class GitProvider(Protocol):
    """Git 平台抽象 —— 获取 PR 数据和仓库信息。"""

    def get_pr_info(self, pr_url: str) -> PRInfo:
        """获取 PR 元数据：标题/描述/分支/作者/SHA。"""
        ...

    def get_files(self, pr_url: str) -> list[FilePatchInfo]:
        """获取 PR 变更文件列表（含 unified diff patch）。"""
        ...

    def get_commits(self, pr_url: str) -> list[CommitInfo]:
        """获取 PR 的提交列表。"""
        ...

    def get_repo_settings(self, pr_url: str) -> str | None:
        """获取仓库根目录的 .insightor.yml 内容（用于配置加载）。"""
        ...

    def get_issue_context(self, pr_url: str, issue_refs: list[str]) -> list[IssueInfo]:
        """获取 PR 关联的 Issue 信息（Layer 3 上下文）。"""
        ...


class DiffService(Protocol):
    """Diff 获取抽象 —— 从不同平台获取 PR 的 unified diff。

    参考 reviewdog 的 DiffService 模式，将 diff 获取从 GitProvider 中解耦。
    """

    def get_diff(self, pr_url: str) -> bytes:
        """获取 PR 的完整 unified diff 字节流。"""
        ...

    def get_strip(self) -> int:
        """diff 路径前缀 strip 数（参考 patch -pN 的 N）。"""
        ...
