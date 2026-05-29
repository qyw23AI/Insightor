"""Diff 压缩器 —— 渐进式 token 预算管理。

压缩策略（参照 PR-Agent）：
  Level 0: 全量 diff + 上下文扩展
  Level 1: 去掉纯删除 hunks、减小上下文窗口
  Level 2: 按文件优先级贪婪打包（主语言优先）
  Level 3: 激进裁剪，仅保留修改函数/类级别 (quick 模式)

分析深度 → 压缩级别映射：
  deep     : Level 0-1 (尽可能保留上下文)
  standard : Level 1-2
  quick    : Level 3
"""

import re
from dataclasses import dataclass

from insightor.providers.types import EditType, FilePatchInfo
from insightor.processing.token_estimator import TokenEstimator

# Hunk header regex: @@ -old_start,old_len +new_start,new_len @@
_HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")


@dataclass
class CompressResult:
    text: str                       # 压缩后的 diff 文本
    unprocessed_files: list[str]    # 放不下的文件名列表
    tokens_used: int                # 实际 token 数
    level: int                      # 使用的压缩级别


class DiffCompressor:
    """渐进式 Diff 压缩器。"""

    def __init__(self, max_tokens: int = 8000, patch_extra_lines: int = 3):
        self.max_tokens = max_tokens
        self.patch_extra_lines = patch_extra_lines
        self._tokenizer = TokenEstimator()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def compress(
        self, files: list[FilePatchInfo], depth: str = "standard"
    ) -> CompressResult:
        """主入口：按分析深度选择压缩策略。"""
        if depth == "deep":
            result = self._try_level(files, 0)
            if result:
                return result
            return self._do_compress(files, level=1)
        elif depth == "standard":
            result = self._try_level(files, 1)
            if result:
                return result
            return self._do_compress(files, level=2)
        else:  # quick
            return self._do_compress(files, level=3)

    # ------------------------------------------------------------------
    # 压缩级别实现
    # ------------------------------------------------------------------

    def _try_level(self, files: list[FilePatchInfo], level: int) -> CompressResult | None:
        """尝试用指定级别压缩，token 不超预算则返回，否则返回 None。"""
        if level == 0:
            text = self._assemble_full(files)
        elif level == 1:
            text = self._assemble_with_context(files, self.patch_extra_lines)
        else:
            return None
        tokens = self._tokenizer.count_tokens(text)
        if tokens <= self.max_tokens:
            return CompressResult(text=text, unprocessed_files=[], tokens_used=tokens, level=level)
        return None

    def _do_compress(self, files: list[FilePatchInfo], level: int) -> CompressResult:
        """执行压缩（level 1-3），保证不超预算。"""
        if level == 1:
            return self._compress_reduce_context(files)
        elif level == 2:
            return self._compress_greedy(files)
        else:
            return self._compress_aggressive(files)

    # ------------------------------------------------------------------
    # Level 1: 减小上下文窗口
    # ------------------------------------------------------------------

    def _compress_reduce_context(self, files: list[FilePatchInfo]) -> CompressResult:
        half = max(1, self.patch_extra_lines // 2)
        text = self._assemble_with_context(files, half)
        tokens = self._tokenizer.count_tokens(text)
        if tokens <= self.max_tokens:
            return CompressResult(text=text, unprocessed_files=[], tokens_used=tokens, level=1)
        return self._compress_greedy(files)

    # ------------------------------------------------------------------
    # Level 2: 贪婪打包
    # ------------------------------------------------------------------

    def _compress_greedy(self, files: list[FilePatchInfo]) -> CompressResult:
        # 删除文件只保留文件名标记，不保留完整 patch
        parts: list[str] = []
        budget = int(self.max_tokens * 0.85)
        used = 0
        skipped: list[str] = []

        for f in files:
            if f.edit_type == EditType.DELETED:
                parts.append(f"# [deleted] {f.filename}\n")
                continue
            patch_text = self._strip_deletion_hunks(f.patch)
            chunk = self._format_file_header(f) + "\n" + patch_text + "\n"
            tokens = self._tokenizer.count_tokens(chunk)
            if used + tokens <= budget:
                parts.append(chunk)
                used += tokens
            else:
                skipped.append(f.filename)

        text = "\n".join(parts)
        return CompressResult(text=text, unprocessed_files=skipped, tokens_used=used, level=2)

    # ------------------------------------------------------------------
    # Level 3: 激进裁剪 (quick 模式)
    # ------------------------------------------------------------------

    def _compress_aggressive(self, files: list[FilePatchInfo]) -> CompressResult:
        # 每个文件只保留 hunk header + 前 10 行变更
        parts: list[str] = []
        budget = int(self.max_tokens * 0.5)
        used = 0
        skipped: list[str] = []

        for f in files:
            if f.edit_type == EditType.DELETED:
                parts.append(f"# [deleted] {f.filename}\n")
                continue
            slim = self._slim_patch(f.patch, max_lines=10)
            chunk = self._format_file_header(f) + "\n" + slim + "\n"
            tokens = self._tokenizer.count_tokens(chunk)
            if used + tokens <= budget:
                parts.append(chunk)
                used += tokens
            else:
                skipped.append(f.filename)

        text = "\n".join(parts)
        return CompressResult(text=text, unprocessed_files=skipped, tokens_used=used, level=3)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _assemble_full(self, files: list[FilePatchInfo]) -> str:
        return "\n".join(self._format_file(f) for f in files)

    def _assemble_with_context(self, files: list[FilePatchInfo], extra: int) -> str:
        parts: list[str] = []
        for f in files:
            header = self._format_file_header(f)
            patch = self._strip_deletion_hunks(f.patch) if f.edit_type != EditType.DELETED else "# file deleted"
            parts.append(header + "\n" + patch)
        return "\n".join(parts)

    @staticmethod
    def _format_file(f: FilePatchInfo) -> str:
        h = DiffCompressor._format_file_header(f)
        return h + "\n" + (f.patch or "# no patch")

    @staticmethod
    def _format_file_header(f: FilePatchInfo) -> str:
        prefix = {"added": "A", "modified": "M", "deleted": "D", "renamed": "R"}.get(f.edit_type.value, "?")
        line = f"# [{prefix}] {f.filename}  +{f.num_plus_lines}/-{f.num_minus_lines}"
        if f.edit_type == EditType.RENAMED and f.old_filename:
            line += f"  (from {f.old_filename})"
        return line

    @staticmethod
    def _strip_deletion_hunks(patch: str) -> str:
        """移除纯删除的 hunk（- 行），保留有新增或修改的 hunk。"""
        if not patch:
            return ""
        lines = patch.split("\n")
        result: list[str] = []
        buf: list[str] = []
        has_add = False
        for line in lines:
            if _HUNK_RE.match(line):
                if buf and has_add:
                    result.extend(buf)
                buf = [line]
                has_add = False
            elif line:
                buf.append(line)
                if line.startswith("+") or (not line.startswith("-") and not line.startswith(" ")):
                    has_add = True
        if buf and has_add:
            result.extend(buf)
        return "\n".join(result)

    @staticmethod
    def _slim_patch(patch: str, max_lines: int) -> str:
        """每个 hunk 仅保留前 max_lines 行变更。"""
        if not patch:
            return ""
        lines = patch.split("\n")
        result: list[str] = []
        count = 0
        for line in lines:
            if _HUNK_RE.match(line):
                result.append(line)
                count = 0
            elif count < max_lines:
                result.append(line)
                if line.startswith("+") or line.startswith("-"):
                    count += 1
        return "\n".join(result)
