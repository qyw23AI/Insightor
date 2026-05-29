"""测试 GitHubProvider 和 Provider 类型。"""

import pytest
from unittest.mock import MagicMock, patch

from insightor.providers.github_provider import GitHubProvider, parse_pr_url
from insightor.providers.types import EditType, FilePatchInfo, PRInfo


# ---------------------------------------------------------------------------
# URL 解析
# ---------------------------------------------------------------------------

class TestParsePRURL:
    def test_standard_url(self):
        owner, repo, num = parse_pr_url("https://github.com/owner/repo/pull/123")
        assert owner == "owner"; assert repo == "repo"; assert num == 123

    def test_url_with_trailing_slash(self):
        owner, repo, num = parse_pr_url("https://github.com/a/b/pull/42/")
        assert owner == "a"; assert repo == "b"; assert num == 42

    def test_url_with_files_suffix(self):
        owner, repo, num = parse_pr_url("https://github.com/x/y/pull/99/files")
        assert owner == "x"; assert repo == "y"; assert num == 99

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="无法解析"):
            parse_pr_url("https://gitlab.com/a/b/merge_requests/1")

    def test_enterprise_url(self):
        owner, repo, num = parse_pr_url("https://github.mycompany.com/org/proj/pull/7")
        assert owner == "org"; assert repo == "proj"; assert num == 7


# ---------------------------------------------------------------------------
# 类型
# ---------------------------------------------------------------------------

class TestFilePatchInfo:
    def test_defaults(self):
        f = FilePatchInfo(filename="test.py")
        assert f.edit_type == EditType.UNKNOWN
        assert f.patch == ""
        assert f.num_plus_lines == -1

    def test_full(self):
        f = FilePatchInfo(
            filename="src/main.py", patch="@@ -1 +1 @@\n-old\n+new",
            edit_type=EditType.MODIFIED, num_plus_lines=1, num_minus_lines=1,
        )
        assert f.edit_type == EditType.MODIFIED
        assert f.num_plus_lines == 1


class TestPRInfo:
    def test_defaults(self):
        info = PRInfo()
        assert info.title == ""; assert info.pr_number == 0

    def test_full(self):
        info = PRInfo(title="feat: new feature", repo_owner="a", repo_name="b", pr_number=1)
        assert info.title == "feat: new feature"


# ---------------------------------------------------------------------------
# GitHubProvider Mock 测试
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def provider(mock_client):
    """构造一个跳过认证的 GitHubProvider，注入 mock client。"""
    p = GitHubProvider.__new__(GitHubProvider)
    p._client = mock_client
    return p


def _make_mock_pr():
    pr = MagicMock()
    pr.title = "feat: add login"
    pr.body = "Adds JWT-based login"
    pr.head.ref = "feature/login"
    pr.head.sha = "abc123def"
    pr.base.ref = "main"
    pr.user.login = "dev42"
    pr.html_url = "https://github.com/owner/repo/pull/1"
    pr.additions = 42
    pr.deletions = 7
    pr.changed_files = 3
    return pr


class TestGitHubProviderMock:
    def test_get_pr_info(self, provider, mock_client):
        mock_pr = _make_mock_pr()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        info = provider.get_pr_info("https://github.com/owner/repo/pull/1")

        mock_client.get_repo.assert_called_once_with("owner/repo")
        assert info.title == "feat: add login"
        assert info.author == "dev42"
        assert info.branch == "feature/login"
        assert info.base_branch == "main"
        assert info.commit_sha == "abc123def"
        assert info.additions == 42
        assert info.pr_number == 1

    def test_to_file_patch(self):
        class MockFile:
            filename = "src/auth.py"
            patch = "@@ -1,3 +1,5 @@\n line1\n+line2\n+line3"
            status = "modified"
            additions = 2
            deletions = 0
            previous_filename = None
        result = GitHubProvider._to_file_patch(MockFile)
        assert result.filename == "src/auth.py"
        assert result.edit_type == EditType.MODIFIED
        assert result.num_plus_lines == 2
        assert result.num_minus_lines == 0

    def test_get_files_returns_list(self, provider, mock_client):
        mock_pr = MagicMock()
        mock_pr.get_files.return_value = []
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        files = provider.get_files("https://github.com/owner/repo/pull/1")
        assert files == []

    def test_repo_construction(self, provider, mock_client):
        mock_pr = _make_mock_pr()
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        info = provider.get_pr_info("https://github.com/myorg/myrepo/pull/42")
        mock_client.get_repo.assert_called_once_with("myorg/myrepo")
        assert info.repo_owner == "myorg"
        assert info.repo_name == "myrepo"
        assert info.pr_number == 42

    def test_get_commits(self, provider, mock_client):
        mock_commit = MagicMock()
        mock_commit.sha = "abc123"
        mock_commit.commit.message = "fix: something"
        mock_commit.commit.author.name = "dev"
        mock_commit.commit.author.date = "2026-01-01"

        mock_pr = MagicMock()
        mock_pr.get_commits.return_value = [mock_commit]
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        commits = provider.get_commits("https://github.com/owner/repo/pull/1")
        assert len(commits) == 1
        assert commits[0].sha == "abc123"
        assert commits[0].message == "fix: something"

    def test_get_repo_settings_not_found(self, provider, mock_client):
        mock_repo = MagicMock()
        from github import UnknownObjectException
        mock_repo.get_contents.side_effect = UnknownObjectException(404, "not found")
        mock_client.get_repo.return_value = mock_repo

        result = provider.get_repo_settings("https://github.com/owner/repo/pull/1")
        assert result is None

    def test_get_issue_context(self, provider, mock_client):
        mock_issue = MagicMock()
        mock_issue.number = 42
        mock_issue.title = "Add JWT auth"
        mock_issue.body = "Implement JWT-based authentication"
        mock_issue.labels = []
        mock_issue.state = "open"

        mock_repo = MagicMock()
        mock_repo.get_issue.return_value = mock_issue
        mock_client.get_repo.return_value = mock_repo

        issues = provider.get_issue_context(
            "https://github.com/owner/repo/pull/1", ["42", "not-an-issue"]
        )
        assert len(issues) == 1
        assert issues[0].number == 42
        assert issues[0].title == "Add JWT auth"

    def test_get_issue_context_invalid_ref(self, provider, mock_client):
        mock_repo = MagicMock()
        mock_client.get_repo.return_value = mock_repo

        issues = provider.get_issue_context(
            "https://github.com/owner/repo/pull/1", ["not-a-number", "abc"]
        )
        assert issues == []

    def test_parse_pr_url_invalid_raises(self, provider):
        with pytest.raises(ValueError, match="无法解析"):
            provider.get_pr_info("not-a-valid-url")
