"""GitHub Provider — 基于 PyGithub 的 PR 数据获取实现。

支持 Personal Access Token (GITHUB_TOKEN) 和 GitHub Actions Token 两种认证。
"""

import logging
import os
import re
from typing import Optional

import github
from github import Auth, Github
from github.GithubException import GithubException, RateLimitExceededException, UnknownObjectException

from insightor.providers.types import CommitInfo, EditType, FilePatchInfo, IssueInfo, PRInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PR URL 解析
# ---------------------------------------------------------------------------

_PR_URL_RE = re.compile(r"github\.com[:/](\S[^/]+)/(\S[^/]+)/pull/(\d+)")


def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    """解析 GitHub PR URL → (owner, repo, pr_number)。

    支持的格式:
      https://github.com/owner/repo/pull/123
      https://github.com/owner/repo/pull/123/files
      https://www.github.com/owner/repo/pull/123
      https://github.mycompany.com/org/proj/pull/7  (企业版)
    """
    pr_url = pr_url.strip().rstrip("/")
    m = re.search(r"github\.[^/]+/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
    if not m:
        raise ValueError(f"无法解析 GitHub PR URL: {pr_url}")
    return m.group(1).strip(), m.group(2).strip(), int(m.group(3))


# ---------------------------------------------------------------------------
# GitHubProvider
# ---------------------------------------------------------------------------


class GitHubProvider:
    """GitHub 平台的 PR 数据获取器。

    实现了 GitProvider 和 DiffService 两个 Protocol。
    """

    def __init__(self, token: str | None = None):
        """初始化 GitHub 客户端。

        token 优先级:
          1. 参数传入
          2. 环境变量 GITHUB_TOKEN
          3. 环境变量 GITHUB_ACCESS_TOKEN (GitHub Actions)
        """
        token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_ACCESS_TOKEN")
        if token:
            self._client = Github(auth=Auth.Token(token))
        else:
            # 无认证：只能访问公开仓库，有严格限速
            self._client = Github()

    # ------------------------------------------------------------------
    # GitProvider 实现
    # ------------------------------------------------------------------

    def get_pr_info(self, pr_url: str) -> PRInfo:
        owner, repo, pr_number = parse_pr_url(pr_url)
        try:
            pr = self._client.get_repo(f"{owner}/{repo}").get_pull(pr_number)
            return PRInfo(
                title=pr.title or "",
                description=pr.body or "",
                branch=pr.head.ref,
                base_branch=pr.base.ref,
                author=pr.user.login if pr.user else "",
                repo_owner=owner,
                repo_name=repo,
                pr_number=pr_number,
                commit_sha=pr.head.sha,
                additions=pr.additions,
                deletions=pr.deletions,
                files_changed=pr.changed_files,
                url=pr.html_url,
            )
        except UnknownObjectException:
            raise ValueError(f"PR 不存在或无权限访问: {pr_url}")
        except RateLimitExceededException:
            raise RuntimeError("GitHub API 限速已用尽，请设置 GITHUB_TOKEN")

    def get_files(self, pr_url: str) -> list[FilePatchInfo]:
        owner, repo, pr_number = parse_pr_url(pr_url)
        try:
            pr = self._client.get_repo(f"{owner}/{repo}").get_pull(pr_number)
            files = pr.get_files()
            return [self._to_file_patch(f) for f in files]
        except UnknownObjectException:
            raise ValueError(f"PR 不存在或无权限访问: {pr_url}")
        except RateLimitExceededException:
            raise RuntimeError("GitHub API 限速已用尽，请设置 GITHUB_TOKEN")

    def get_commits(self, pr_url: str) -> list[CommitInfo]:
        owner, repo, pr_number = parse_pr_url(pr_url)
        try:
            pr = self._client.get_repo(f"{owner}/{repo}").get_pull(pr_number)
            commits = pr.get_commits()
            return [
                CommitInfo(
                    sha=c.sha or "",
                    message=(c.commit.message or "") if c.commit else "",
                    author=c.commit.author.name if c.commit and c.commit.author else "",
                    date=str(c.commit.author.date) if c.commit and c.commit.author and c.commit.author.date else "",
                )
                for c in commits
            ]
        except GithubException as e:
            logger.warning("获取 commits 失败: %s", e)
            return []

    def get_repo_settings(self, pr_url: str) -> str | None:
        """从仓库默认分支获取 .insightor.yml 内容。"""
        owner, repo, _ = parse_pr_url(pr_url)
        try:
            r = self._client.get_repo(f"{owner}/{repo}")
            content = r.get_contents(".insightor.yml")
            if content and hasattr(content, "decoded_content"):
                return content.decoded_content.decode("utf-8")
        except (UnknownObjectException, GithubException):
            pass
        return None

    def get_issue_context(self, pr_url: str, issue_refs: list[str]) -> list[IssueInfo]:
        """获取 PR 关联的 Issue 信息。

        issue_refs 可以是 GitHub issue 编号 (如 ["42", "58"])。
        """
        owner, repo, _ = parse_pr_url(pr_url)
        issues: list[IssueInfo] = []
        for ref in issue_refs:
            try:
                num = int(re.sub(r"[^0-9]", "", ref))
                if num <= 0:
                    continue
                issue = self._client.get_repo(f"{owner}/{repo}").get_issue(num)
                issues.append(IssueInfo(
                    number=issue.number,
                    title=issue.title or "",
                    body=issue.body or "",
                    labels=[lb.name for lb in issue.labels] if issue.labels else [],
                    state=issue.state or "",
                ))
            except (ValueError, GithubException):
                logger.debug("无法获取 issue: %s", ref)
        return issues

    # ------------------------------------------------------------------
    # DiffService 实现
    # ------------------------------------------------------------------

    def get_diff(self, pr_url: str) -> bytes:
        """获取 PR 的完整 unified diff。

        从 get_files() 的每个文件 patch 拼接，不额外调用 API。
        """
        files = self.get_files(pr_url)
        parts: list[str] = []
        for f in files:
            if not f.patch:
                continue
            header = f"diff --git a/{f.filename} b/{f.filename}"
            if f.edit_type == EditType.RENAMED and f.old_filename:
                header += f"\nrename from {f.old_filename}\nrename to {f.filename}"
            parts.append(header + "\n" + f.patch)
        return "\n".join(parts).encode("utf-8")

    @staticmethod
    def get_strip() -> int:
        return 1  # github diff 通常以 a/... b/... 为前缀

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _get_headers(self) -> dict[str, str]:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_ACCESS_TOKEN")
        headers = {"Accept": "application/vnd.github.v3.diff"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _to_file_patch(f: github.File.File) -> FilePatchInfo:
        """将 PyGithub File 对象转换为 FilePatchInfo。"""
        edit_type = _map_edit_type(f.status)
        return FilePatchInfo(
            filename=f.filename,
            patch=f.patch or "",
            edit_type=edit_type,
            old_filename=f.previous_filename if edit_type == EditType.RENAMED else None,
            num_plus_lines=f.additions,
            num_minus_lines=f.deletions,
        )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _map_edit_type(status: str) -> EditType:
    """GitHub file status → EditType。"""
    mapping = {
        "added": EditType.ADDED,
        "modified": EditType.MODIFIED,
        "removed": EditType.DELETED,
        "renamed": EditType.RENAMED,
    }
    return mapping.get(status, EditType.UNKNOWN)
