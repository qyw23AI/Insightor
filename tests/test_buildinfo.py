"""测试 BuildInfo CI 环境检测。"""

import os
from unittest.mock import patch

from insightor.environment.buildinfo import BuildInfo, detect_build_info


class TestBuildInfo:
    def test_defaults(self):
        info = BuildInfo()
        assert info.is_ci is False
        assert info.repo_full_name == ""

    def test_is_ci_true(self):
        info = BuildInfo(ci_system="github_actions")
        assert info.is_ci is True


class TestDetectBuildInfo:
    def test_local_default(self):
        """在无 CI 环境变量时返回 local。"""
        with patch.dict(os.environ, {}, clear=True):
            info = detect_build_info()
            assert info.ci_system == "local"

    def test_github_actions_detection(self):
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123",
            "GITHUB_HEAD_REF": "feature-branch",
        }
        with patch.dict(os.environ, env, clear=True):
            info = detect_build_info()
            assert info.ci_system == "github_actions"
            assert info.owner == "owner"
            assert info.repo == "repo"
            assert info.commit_sha == "abc123"
            assert info.branch == "feature-branch"

    def test_gitlab_ci_detection(self):
        env = {
            "GITLAB_CI": "true",
            "CI_PROJECT_NAMESPACE": "gitlab-org",
            "CI_PROJECT_NAME": "my-project",
            "CI_MERGE_REQUEST_IID": "42",
            "CI_COMMIT_SHA": "def456",
            "CI_MERGE_REQUEST_SOURCE_BRANCH_NAME": "mr-feature",
        }
        with patch.dict(os.environ, env, clear=True):
            info = detect_build_info()
            assert info.ci_system == "gitlab_ci"
            assert info.owner == "gitlab-org"
            assert info.repo == "my-project"
            assert info.pr_number == 42
