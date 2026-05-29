"""测试 FileFilter。"""

from insightor.processing.file_filter import FileFilter
from insightor.providers.types import EditType, FilePatchInfo


def _f(name: str) -> FilePatchInfo:
    return FilePatchInfo(filename=name, edit_type=EditType.MODIFIED)


class TestFileFilter:
    def test_passes_normal_code(self):
        ff = FileFilter()
        files = [_f("src/main.py"), _f("app.js"), _f("lib.rs")]
        assert len(ff.filter(files)) == 3

    def test_filters_lock_files(self):
        ff = FileFilter()
        files = [_f("src/main.py"), _f("package-lock.json"), _f("yarn.lock")]
        result = ff.filter(files)
        assert len(result) == 1
        assert result[0].filename == "src/main.py"

    def test_filters_images(self):
        ff = FileFilter()
        files = [_f("logo.png"), _f("icon.jpg"), _f("src/code.py")]
        assert len(ff.filter(files)) == 1

    def test_filters_node_modules(self):
        ff = FileFilter()
        files = [_f("node_modules/foo/index.js"), _f("src/app.ts")]
        assert len(ff.filter(files)) == 1

    def test_filters_vendor(self):
        ff = FileFilter()
        files = [_f("vendor/lib/utils.go"), _f("main.go")]
        assert len(ff.filter(files)) == 1

    def test_filters_minified(self):
        ff = FileFilter()
        files = [_f("jquery.min.js"), _f("app.js")]
        assert len(ff.filter(files)) == 1

    def test_custom_globs(self):
        ff = FileFilter(extra_globs=["*.autogen.py"])
        files = [_f("models.autogen.py"), _f("handlers.py")]
        assert len(ff.filter(files)) == 1
        assert ff.filter(files)[0].filename == "handlers.py"

    def test_custom_regex(self):
        ff = FileFilter(extra_regex=[r"/generated/"])
        files = [_f("src/generated/types.py"), _f("src/handlers.py")]
        assert len(ff.filter(files)) == 1

    def test_is_ignored(self):
        ff = FileFilter()
        assert ff.is_ignored("yarn.lock") is True
        assert ff.is_ignored("src/main.py") is False
