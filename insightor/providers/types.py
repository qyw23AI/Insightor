"""Provider 层通用数据类型。"""

from dataclasses import dataclass, field
from enum import Enum


class EditType(str, Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    UNKNOWN = "unknown"


@dataclass
class FilePatchInfo:
    """单个文件的 diff 信息。"""
    filename: str                   # 文件相对路径
    patch: str = ""                 # unified diff patch 内容
    edit_type: EditType = EditType.UNKNOWN
    old_filename: str | None = None # rename 时的旧文件名
    num_plus_lines: int = -1
    num_minus_lines: int = -1
    language: str | None = None
    tokens: int = -1                # patch 的 token 估算数 (由 processing 层填充)


@dataclass
class PRInfo:
    """PR 元数据。"""
    title: str = ""
    description: str = ""
    branch: str = ""            # 源分支名
    base_branch: str = ""       # 目标分支名
    author: str = ""            # GitHub username
    repo_owner: str = ""
    repo_name: str = ""
    pr_number: int = 0
    commit_sha: str = ""        # 最新 commit SHA
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    url: str = ""


@dataclass
class CommitInfo:
    """提交信息。"""
    sha: str = ""
    message: str = ""
    author: str = ""
    date: str = ""


@dataclass
class IssueInfo:
    """关联 Issue 信息（来自 Layer 3 上下文管线）。"""
    number: int = 0
    title: str = ""
    body: str = ""
    labels: list[str] = field(default_factory=list)
    state: str = ""
