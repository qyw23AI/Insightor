"""CI 环境自动检测，类似 reviewdog 的 cienv 包。

将 GitHub Actions / GitLab CI / 本地 等不同 CI 平台的差异
统一抽象为 BuildInfo 数据类。
"""

import os
import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class BuildInfo:
    owner: str = ""
    repo: str = ""
    pr_number: int = 0
    commit_sha: str = ""
    branch: str = ""
    ci_system: Literal["github_actions", "gitlab_ci", "local", "unknown"] = "local"
    extra: dict = field(default_factory=dict)

    @property
    def is_ci(self) -> bool:
        return self.ci_system != "local"

    @property
    def repo_full_name(self) -> str:
        return f"{self.owner}/{self.repo}" if self.owner and self.repo else ""


def detect_build_info() -> BuildInfo:
    """从环境变量自动检测 CI 环境。"""

    # --- GitHub Actions ---
    if os.environ.get("GITHUB_ACTIONS") == "true":
        info = BuildInfo(ci_system="github_actions")
        info.owner, info.repo = _parse_github_repo()
        info.pr_number = _get_github_pr_number()
        info.commit_sha = os.environ.get("GITHUB_SHA", "")
        info.branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "")
        return info

    # --- GitLab CI ---
    if os.environ.get("GITLAB_CI") == "true":
        return BuildInfo(
            ci_system="gitlab_ci",
            owner=os.environ.get("CI_PROJECT_NAMESPACE", ""),
            repo=os.environ.get("CI_PROJECT_NAME", ""),
            pr_number=_parse_int(os.environ.get("CI_MERGE_REQUEST_IID")),
            commit_sha=os.environ.get("CI_COMMIT_SHA", ""),
            branch=os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_NAME", ""),
        )

    # --- Generic CI env vars (Jenkins, Circle, Drone, ...) ---
    return _detect_generic()


# =============================================================================
# 内部辅助
# =============================================================================

def _parse_github_repo() -> tuple[str, str]:
    """从 GITHUB_REPOSITORY 解析 owner/repo。"""
    repo = os.environ.get("GITHUB_REPOSITORY", "/")
    parts = repo.split("/")
    return parts[0], parts[1] if len(parts) > 1 else ""


def _get_github_pr_number() -> int:
    """从 GitHub event JSON 或环境变量提取 PR 编号。"""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.exists(event_path):
        import json
        try:
            with open(event_path) as f:
                event = json.load(f)
            return event.get("pull_request", {}).get("number", 0) or event.get("number", 0)
        except (json.JSONDecodeError, OSError):
            pass
    return _parse_int(os.environ.get("GITHUB_REF")) if os.environ.get("GITHUB_REF", "").startswith("refs/pull/") else 0


def _detect_generic() -> BuildInfo:
    """从通用 CI_* 环境变量检测。"""
    pr = _parse_int(os.environ.get("CI_PULL_REQUEST") or os.environ.get("CI_MERGE_REQUEST_IID") or
                    os.environ.get("PULL_REQUEST_NUMBER") or os.environ.get("ghprbPullId"))

    owner = os.environ.get("CI_REPO_OWNER") or os.environ.get("CIRCLE_PROJECT_USERNAME") or ""
    repo = os.environ.get("CI_REPO_NAME") or os.environ.get("CIRCLE_PROJECT_REPONAME") or ""

    has_ci_hint = any([pr, owner, repo])
    return BuildInfo(
        ci_system="unknown" if has_ci_hint else "local",
        owner=owner,
        repo=repo,
        pr_number=pr,
        commit_sha=os.environ.get("CI_COMMIT") or os.environ.get("CIRCLE_SHA1") or "",
        branch=os.environ.get("CI_BRANCH") or "",
    )


def _parse_int(val: str | None) -> int:
    if val is None:
        return 0
    match = re.search(r"(\d+)", str(val))
    return int(match.group(1)) if match else 0
