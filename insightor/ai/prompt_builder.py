"""Prompt 模板引擎 — Jinja2 渲染 TOML 存储的 prompt 模板。"""

import tomllib
from pathlib import Path

from jinja2 import Environment, BaseLoader


class PromptBuilder:
    """从 TOML 文件加载并渲染 prompt 模板。

    模板变量:
      title, description, branch, base_branch, author
      additions, deletions, files_changed
      diff, file_list, commit_messages
      extra_instructions, custom_rules, conventions, focus_categories
    """

    def __init__(self, template_dir: str | None = None):
        if template_dir is None:
            template_dir = str(Path(__file__).resolve().parent.parent / "config" / "prompts")
        self._dir = Path(template_dir)
        self._jinja = Environment(loader=BaseLoader(), autoescape=False)
        self._cache: dict[str, tuple[str, str]] = {}

    def build(self, tool: str, vars: dict | None = None) -> tuple[str, str]:
        """返回 (system_prompt, user_prompt)。"""
        vars = vars or {}
        if tool not in self._cache:
            self._cache[tool] = self._load(tool)
        sys_tmpl, user_tmpl = self._cache[tool]
        return (
            self._jinja.from_string(sys_tmpl).render(**vars).strip(),
            self._jinja.from_string(user_tmpl).render(**vars).strip(),
        )

    def render(self, template_name: str, context: dict | None = None) -> str:
        """渲染单个模板 (不需要 tool 前缀)。"""
        context = context or {}
        path = self._dir / template_name
        if not path.exists():
            raise FileNotFoundError(f"模板不存在: {path}")
        tmpl = path.read_text(encoding="utf-8")
        return self._jinja.from_string(tmpl).render(**context).strip()

    def _load(self, tool: str) -> tuple[str, str]:
        path = self._dir / f"{tool}.toml"
        if not path.exists():
            raise FileNotFoundError(f"模板不存在: {path}")
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return data["system"]["content"], data["user"]["content"]
