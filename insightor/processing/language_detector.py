"""语言检测与优先级排序 —— 按仓库主语言对文件排序，提升上下文质量。"""

from pathlib import Path

from insightor.providers.types import FilePatchInfo

# 扩展名 → 语言名 映射
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python", ".pyx": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin",
    ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".sql": "SQL",
    ".yaml": "YAML", ".yml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".md": "Markdown", ".rst": "Markdown",
    ".toml": "TOML",
    ".cfg": "Config", ".ini": "Config",
    ".tf": "Terraform", ".hcl": "Terraform",
    ".dockerfile": "Dockerfile",
    ".proto": "Protobuf",
}


class LanguageDetector:
    """检测文件语言并按主语言优先级排序。"""

    def __init__(self, ext_map: dict[str, str] | None = None):
        self._map = ext_map or EXTENSION_LANGUAGE_MAP

    def detect(self, filename: str) -> str:
        """检测单个文件的语言。"""
        name = Path(filename).name.lower()
        if name == "dockerfile":
            return "Dockerfile"
        if name == "makefile":
            return "Makefile"
        suffix = Path(filename).suffix.lower()
        if suffix:
            return self._map.get(suffix, "Other")
        return "Other"

    def group_by_language(self, files: list[FilePatchInfo]) -> dict[str, list[FilePatchInfo]]:
        """按语言分组。"""
        groups: dict[str, list[FilePatchInfo]] = {}
        for f in files:
            lang = f.language or self.detect(f.filename)
            f.language = lang
            groups.setdefault(lang, []).append(f)
        return groups

    def sort_by_priority(
        self, files: list[FilePatchInfo], main_language: str = ""
    ) -> list[FilePatchInfo]:
        """主语言文件排最前，其余按语言名排序。"""
        groups = self.group_by_language(files)
        result: list[FilePatchInfo] = []
        # 主语言优先
        if main_language and main_language in groups:
            result.extend(groups.pop(main_language))
        # 其余语言按字母序
        for lang in sorted(groups):
            result.extend(groups[lang])
        return result
