"""测试 ConfigLoader 四级配置覆盖。"""

import pytest
from insightor.config.loader import ConfigLoader


class TestConfigLoader:
    def test_loads_defaults(self):
        loader = ConfigLoader()
        assert loader.get("models.primary") == "claude-sonnet-4-6"
        assert loader.get("review.min_severity") == "medium"

    def test_default_on_missing_key(self):
        loader = ConfigLoader()
        assert loader.get("nonexistent.key", "default_val") == "default_val"

    def test_get_section(self):
        loader = ConfigLoader()
        models = loader.get_section("models")
        assert "primary" in models
        assert "fallback" in models

    def test_convenience_methods(self):
        loader = ConfigLoader()
        assert isinstance(loader.get_rules(), list)
        assert isinstance(loader.get_conventions(), list)
        assert isinstance(loader.get_safe_patterns(), list)
        assert isinstance(loader.get_dependency_map(), dict)

    def test_cli_override(self):
        loader = ConfigLoader()
        loader.apply_cli_args(**{"models.primary": "custom-model"})
        assert loader.get("models.primary") == "custom-model"

    def test_cli_none_ignored(self):
        loader = ConfigLoader()
        loader.apply_cli_args(**{"models.primary": None, "review.min_severity": "high"})
        assert loader.get("models.primary") == "claude-sonnet-4-6"  # unchanged
        assert loader.get("review.min_severity") == "high"  # changed
