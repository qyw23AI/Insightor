"""测试 LanguageDetector、TokenEstimator、DiffCompressor、CacheManager。"""

import pytest

from insightor.processing.language_detector import LanguageDetector
from insightor.processing.token_estimator import TokenEstimator
from insightor.processing.diff_compressor import DiffCompressor, CompressResult
from insightor.processing.cache_manager import CacheManager
from insightor.providers.types import EditType, FilePatchInfo
from insightor.schemas.urf import PRSummary, ReviewMeta, ReviewResult


# =============================================================================
# LanguageDetector
# =============================================================================

class TestLanguageDetector:
    def test_detect_python(self):
        ld = LanguageDetector()
        assert ld.detect("src/main.py") == "Python"

    def test_detect_typescript(self):
        ld = LanguageDetector()
        assert ld.detect("src/App.tsx") == "TypeScript"

    def test_detect_dockerfile(self):
        ld = LanguageDetector()
        assert ld.detect("Dockerfile") == "Dockerfile"

    def test_detect_unknown(self):
        ld = LanguageDetector()
        assert ld.detect("somefile.xyz") == "Other"

    def test_group_by_language(self):
        ld = LanguageDetector()
        files = [
            FilePatchInfo(filename="a.py"), FilePatchInfo(filename="b.py"),
            FilePatchInfo(filename="c.js"), FilePatchInfo(filename="d.go"),
        ]
        groups = ld.group_by_language(files)
        assert len(groups["Python"]) == 2
        assert len(groups["JavaScript"]) == 1
        assert len(groups["Go"]) == 1

    def test_sort_priority_main_lang_first(self):
        ld = LanguageDetector()
        files = [
            FilePatchInfo(filename="c.js"), FilePatchInfo(filename="a.py"),
            FilePatchInfo(filename="b.py"),
        ]
        sorted_files = ld.sort_by_priority(files, main_language="Python")
        # Python files first
        assert sorted_files[0].filename.endswith(".py")
        assert sorted_files[1].filename.endswith(".py")
        # JS after
        assert sorted_files[2].filename.endswith(".js")


# =============================================================================
# TokenEstimator
# =============================================================================

class TestTokenEstimator:
    def test_basic_count(self):
        te = TokenEstimator(model="gpt-4o")
        n = te.count_tokens("hello world")
        assert n > 0

    def test_empty_string(self):
        te = TokenEstimator()
        assert te.count_tokens("") == 0

    def test_non_openai_fallback(self):
        te = TokenEstimator(model="claude-sonnet-4-6")
        n = te.count_tokens("a" * 100)
        assert n == int(100 * 0.30)

    def test_estimate_quick(self):
        n = TokenEstimator.estimate_quick("abcdefghij")  # 10 chars * 0.30 = 3
        assert n == 3

    def test_deepseek_factor(self):
        te = TokenEstimator(model="deepseek-v3")
        assert te.factor == 0.35


# =============================================================================
# DiffCompressor
# =============================================================================

def _make_file(name: str, plus: int = 5, minus: int = 2, edit=EditType.MODIFIED) -> FilePatchInfo:
    return FilePatchInfo(
        filename=name, edit_type=edit,
        num_plus_lines=plus, num_minus_lines=minus,
        patch="@@ -1,3 +1,5 @@\n line1\n+line2\n+line3\n-line4\n",
    )


class TestDiffCompressor:
    def test_full_assembly(self):
        dc = DiffCompressor(max_tokens=99999)
        files = [_make_file("a.py"), _make_file("b.py")]
        result = dc.compress(files, depth="deep")
        assert result.level == 0
        assert len(result.unprocessed_files) == 0

    def test_aggressive_clips_to_budget(self):
        # 用极小的预算强制进入 aggressive 模式，但 result 不应崩溃
        dc = DiffCompressor(max_tokens=50)
        files = [_make_file("a.py", plus=200), _make_file("b.py", plus=200)]
        result = dc.compress(files, depth="quick")
        assert result.level == 3
        assert len(result.text) > 0

    def test_deleted_file_stripped(self):
        dc = DiffCompressor(max_tokens=99999)
        files = [
            FilePatchInfo(filename="gone.py", edit_type=EditType.DELETED,
                         num_plus_lines=0, num_minus_lines=10, patch=""),
        ]
        result = dc.compress(files, depth="standard")
        assert "[deleted]" in result.text.lower() or "D" in result.text

    def test_format_header(self):
        f = FilePatchInfo(filename="test.py", edit_type=EditType.MODIFIED,
                         num_plus_lines=3, num_minus_lines=1)
        header = DiffCompressor._format_file_header(f)
        assert "M" in header
        assert "test.py" in header
        assert "+3/-1" in header or "+3" in header

    def test_strip_deletion_hunks(self):
        patch = "@@ -1,2 +1,1 @@\n-old_line\n-old_line2\n"
        result = DiffCompressor._strip_deletion_hunks(patch)
        # 纯删除 hunk 被移除
        assert result == "" or len(result) < len(patch)


# =============================================================================
# CacheManager
# =============================================================================

class TestCacheManager:
    @pytest.fixture
    def cm(self, tmp_path):
        return CacheManager(cache_root=str(tmp_path / "cache"))

    def test_put_and_get(self, cm):
        meta = ReviewMeta(pr_url="https://github.com/a/b/pull/1", commit_sha="abc123def456")
        result = ReviewResult(meta=meta, summary=PRSummary(overview="test"))
        cm.put(meta.pr_url, meta.commit_sha, result)

        loaded = cm.get(meta.pr_url, meta.commit_sha)
        assert loaded is not None
        assert loaded.summary.overview == "test"

    def test_get_missing(self, cm):
        assert cm.get("https://github.com/a/b/pull/1", "nonexistent") is None

    def test_get_latest(self, cm):
        pr_url = "https://github.com/owner/repo/pull/42"
        meta1 = ReviewMeta(pr_url=pr_url, commit_sha="aaa111222333")
        meta2 = ReviewMeta(pr_url=pr_url, commit_sha="bbb444555666")
        cm.put(pr_url, meta1.commit_sha, ReviewResult(meta=meta1))
        cm.put(pr_url, meta2.commit_sha, ReviewResult(meta=meta2))

        latest = cm.get_latest(pr_url)
        assert latest is not None
        assert latest.meta.commit_sha == "bbb444555666"

    def test_get_base_for_incremental_exact_hit(self, cm):
        pr_url = "https://github.com/a/b/pull/1"
        meta = ReviewMeta(pr_url=pr_url, commit_sha="abc123")
        cm.put(pr_url, "abc123", ReviewResult(meta=meta))

        sha, result = cm.get_base_for_incremental(pr_url, "abc123")
        assert sha == "abc123"
        assert result is not None

    def test_list_reviews(self, cm):
        pr_url = "https://github.com/a/b/pull/1"
        cm.put(pr_url, "aaa111", ReviewResult(meta=ReviewMeta(pr_url=pr_url, commit_sha="aaa111")))
        cm.put(pr_url, "bbb222", ReviewResult(meta=ReviewMeta(pr_url=pr_url, commit_sha="bbb222")))
        reviews = cm.list_reviews(pr_url)
        assert len(reviews) == 2
