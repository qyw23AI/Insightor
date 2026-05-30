"""文件过滤器 —— 排除不应审查的二进制、生成代码、lock 文件等。

参考 PR-Agent 的 filter_ignored + file_filter，Reviewdog 的 diff filter 模式。
"""

import fnmatch
import re
from pathlib import Path

from insightor.providers.types import FilePatchInfo

# ---- 默认忽略规则 -----------------------------------------
# 可直接被 .insightor.yml 覆盖

DEFAULT_IGNORE_GLOBS: list[str] = [
    # 二进制 / 媒体
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg",
    "*.woff", "*.woff2", "*.ttf", "*.eot",
    "*.mp4", "*.mp3", "*.avi", "*.mov",
    "*.zip", "*.tar", "*.gz", "*.7z",
    "*.pdf", "*.doc", "*.docx", "*.xls", "*.xlsx",
    "*.pyc", "*.pyo", "*.so", "*.dll", "*.exe",
    # 生成 / 锁定文件
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock",
    "Cargo.lock", "Gemfile.lock", "composer.lock",
    "*.generated.*", "*.gen.*",
    "*.min.js", "*.min.css",
    # IDE / 工具
    ".vscode/*", ".idea/*",
    "__pycache__/*", "*.pyc",
    ".mypy_cache/*", ".pytest_cache/*", ".ruff_cache/*",
]

DEFAULT_IGNORE_REGEX: list[str] = [
    r"^vendor/",
    r"^node_modules/",
    r"/migrations/",
    r"\.pb\.(go|py|java)$",          # protobuf 生成文件
    r"\.pb\.gw\.(go|py)$",
    r"^dist/",
    r"^build/",
]


class FileFilter:
    """根据 glob + regex 规则过滤文件。"""

    def __init__(
        self,
        extra_globs: list[str] | None = None,
        extra_regex: list[str] | None = None,
    ):
        globs = list(DEFAULT_IGNORE_GLOBS) + (extra_globs or [])
        regexes = list(DEFAULT_IGNORE_REGEX) + (extra_regex or [])

        self._glob_re = re.compile(
            "|".join(fnmatch.translate(g) for g in globs), re.IGNORECASE
        ) if globs else None

        self._regex = re.compile(
            "|".join(rf"(?:{r})" for r in regexes), re.IGNORECASE
        ) if regexes else None

    def is_ignored(self, filename: str) -> bool:
        if self._glob_re and self._glob_re.fullmatch(filename):
            return True
        if self._regex and self._regex.search(filename):
            return True
        return False

    def filter(self, files: list[FilePatchInfo]) -> list[FilePatchInfo]:
        return [f for f in files if not self.is_ignored(f.filename)]
