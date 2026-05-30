"""四级配置加载系统：default.toml → .insightor.yml → 环境变量 → CLI 参数。"""

import os
from pathlib import Path
from typing import Any

import tomllib
import yaml
from dotenv import load_dotenv

load_dotenv()


class ConfigLoader:
    """四级配置覆盖加载器。

    优先级 (低 → 高):
      1. default.toml  — 全局默认
      2. .insightor.yml — 项目级覆盖（从仓库根目录加载）
      3. INSIGHTOR_* 环境变量
      4. CLI 参数（外部设置）
    """

    def __init__(self, config_path: str | None = None):
        self._data: dict[str, Any] = {}
        self._project_config: dict[str, Any] = {}
        self._cli_overrides: dict[str, Any] = {}

        builtin = config_path or str(Path(__file__).resolve().parent / "default.toml")
        self._load_builtin(builtin)

    # ------------------------------------------------------------------
    # 内部加载
    # ------------------------------------------------------------------

    def _load_builtin(self, path: str) -> None:
        if Path(path).exists():
            with open(path, "rb") as f:
                self._data = tomllib.load(f)

    def _apply_project_overrides(self) -> dict[str, Any]:
        merged = dict(self._data)
        for section in ("review", "context", "models", "output"):
            if section in self._project_config:
                if section not in merged:
                    merged[section] = {}
                merged[section] = {**merged[section], **self._project_config[section]}
        return merged

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def load_project_config(self, repo_root: str) -> dict[str, Any] | None:
        """加载仓库根目录的 .insightor.yml。"""
        path = Path(repo_root) / ".insightor.yml"
        if not path.exists():
            self._project_config = {}
            return None
        with open(path, encoding="utf-8") as f:
            self._project_config = yaml.safe_load(f) or {}
        return self._project_config

    def apply_cli_args(self, **kwargs: Any) -> None:
        """应用 CLI 参数覆盖（最高优先级）。"""
        self._cli_overrides = {k: v for k, v in kwargs.items() if v is not None}

    def get(self, key_path: str, default: Any = None) -> Any:
        """按 'section.key' 路径取值，自动应用覆盖优先级。"""
        env_val = self._get_env(key_path)
        if env_val is not None:
            return env_val

        if key_path in self._cli_overrides:
            return self._cli_overrides[key_path]

        parts = key_path.split(".")
        merged = self._apply_project_overrides()

        val: Any = merged
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                return default
        return val if val is not None else default

    def get_section(self, section: str) -> dict[str, Any]:
        """获取整个配置段。"""
        merged = self._apply_project_overrides()
        base = merged.get(section, {})
        cli = {k.replace(f"{section}.", ""): v for k, v in self._cli_overrides.items() if k.startswith(f"{section}.")}
        return {**base, **cli}

    # ------------------------------------------------------------------
    # 便捷方法
    # ------------------------------------------------------------------

    def get_rules(self) -> list[str]:
        return self.get("review.custom_rules") or []

    def get_conventions(self) -> list[str]:
        return self.get("review.conventions") or []

    def get_safe_patterns(self) -> list[str]:
        return self.get("review.safe_patterns") or []

    def get_dependency_map(self) -> dict[str, list[str]]:
        return self.get("context.dependency_map") or {}

    def get_focus_categories(self) -> list[str]:
        return self.get("review.focus_categories") or ["security", "performance", "logic"]

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _get_env(key_path: str) -> str | None:
        env_key = "INSIGHTOR_" + key_path.upper().replace(".", "_")
        return os.environ.get(env_key)


# 全局单例
config = ConfigLoader()
