"""核心 Review 管线 — 串联 Provider → Processing → AI → Output 全流程。

支持:
  - 三种分析深度 (quick/standard/deep)
  - 增量审查 (基于 CacheManager)
  - 步骤级进度回调
  - 统一异常体系
"""

import logging
import time
from typing import Callable, Optional

from insightor.ai.litellm_handler import LiteLLMHandler
from insightor.ai.prompt_builder import PromptBuilder
from insightor.ai.response_parser import ResponseParser, DescribeParser, RisksParser
from insightor.config.loader import config
from insightor.output.base import CompositeOutput
from insightor.output.console import ConsoleOutput
from insightor.output.json_output import JSONOutput
from insightor.output.markdown import MarkdownFileOutput
from insightor.processing.cache_manager import CacheManager
from insightor.processing.diff_compressor import DiffCompressor
from insightor.processing.file_filter import FileFilter
from insightor.processing.language_detector import LanguageDetector
from insightor.processing.token_estimator import TokenEstimator
from insightor.providers.github_provider import GitHubProvider
from insightor.schemas.urf import AnalysisDepth, ReviewMeta, ReviewResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "deepseek-v4-flash"
MAX_TOKENS = config.get("token.max_input_tokens", 32000)


# =============================================================================
# 异常体系
# =============================================================================

class PipelineError(Exception): ...


# =============================================================================
# ReviewPipeline
# =============================================================================

class ReviewPipeline:
    """Insightor 核心管线: PR URL → ReviewResult。"""

    def __init__(
        self,
        model: str | None = None,
        fallback_models: list[str] | None = None,
        cache_dir: str | None = None,
    ):
        self.model = model or DEFAULT_MODEL
        self.fallback_models = fallback_models or config.get("models.fallback", [])
        self.cache_dir = cache_dir or config.get("output.cache_dir", ".insightor")
        self._provider: Optional[GitHubProvider] = None
        self._ai: Optional[LiteLLMHandler] = None

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def run(
        self,
        pr_url: str,
        tool: str = "review",
        depth: str = "standard",
        incremental: bool = False,
        on_progress: Callable[[str], None] | None = None,
        skip_markdown: bool = False,
    ) -> ReviewResult:
        """执行完整 review 管线。

        Args:
            pr_url: GitHub PR URL
            tool: 使用的 prompt 模板 (review/describe/risks)
            depth: 分析深度 (quick/standard/deep)
            incremental: 是否增量审查
            on_progress: 步骤进度回调
            skip_markdown: 跳过 Markdown 文件生成（full 命令自己生成合并报告）
        """
        t_start = time.time()
        self._provider = GitHubProvider()
        self._ai = LiteLLMHandler(fallback_models=self.fallback_models)

        # Step 1: 获取 PR 数据
        self._progress(on_progress, "正在获取 PR 数据...")
        info = self._provider.get_pr_info(pr_url)
        raw_files = self._provider.get_files(pr_url)
        commits = self._provider.get_commits(pr_url)

        # Step 2: 处理文件
        self._progress(on_progress, "正在处理代码变更...")
        ff = FileFilter()
        ld = LanguageDetector()
        files = ff.filter(raw_files)
        main_lang = self._detect_main_lang(ld, files)
        sorted_files = ld.sort_by_priority(files, main_language=main_lang)

        # Step 3: Token 估算 + 压缩
        self._progress(on_progress, "正在优化输入...")
        depth_enum = AnalysisDepth(depth)
        token_budget = self._calc_budget(depth_enum)
        dc = DiffCompressor(max_tokens=token_budget)
        compressed = dc.compress(sorted_files, depth=depth)

        # Step 4: 构建 Prompt
        self._progress(on_progress, "正在构建分析提示...")
        builder = PromptBuilder()
        commit_text = "\n".join(
            f"{c.sha[:8]} {c.message.split(chr(10))[0][:60]}" for c in commits[:5]
        )
        file_list = "\n".join(
            f"  [{f.edit_type.value}] {f.filename}" for f in sorted_files[:30]
        )
        system, user = builder.build(tool, {
            "title": info.title,
            "description": info.description,
            "branch": info.branch,
            "base_branch": info.base_branch,
            "author": info.author,
            "additions": info.additions,
            "deletions": info.deletions,
            "files_changed": info.files_changed,
            "diff": compressed.text,
            "commit_messages": commit_text,
            "file_list": file_list,
            "custom_rules": config.get_rules(),
            "focus_categories": config.get_focus_categories(),
        })

        # Step 5: AI 分析
        self._progress(on_progress, "正在 AI 分析中...")
        ai_model = self._pick_model(depth_enum)
        resp = await self._ai.chat_completion(
            model=ai_model,
            system_prompt=system,
            user_prompt=user,
            temperature=0.3,
            max_tokens=16384 if depth_enum == AnalysisDepth.DEEP else 8192,
        )
        # Step 6: 解析结果
        self._progress(on_progress, f"正在解析分析结果... (finish={resp.finish_reason}, completion={resp.usage.completion_tokens}tok)")
        meta = ReviewMeta(
            pr_url=pr_url,
            commit_sha=info.commit_sha,
            analysis_depth=depth_enum,
            model=resp.model,
            duration_ms=int((time.time() - t_start) * 1000),
            tokens_used=resp.usage.total_tokens,
            files_analyzed=len(files),
            files_skipped=len(raw_files) - len(files) + len(compressed.unprocessed_files),
            is_incremental=incremental,
            context_layers=["diff"],
        )
        if tool == "describe":
            result = DescribeParser.parse(resp.content, meta)
        elif tool == "risks":
            result = RisksParser.parse(resp.content, meta)
        else:
            result = ResponseParser.parse(resp.content, meta)

        # Step 7: 缓存结果
        self._progress(on_progress, "正在保存结果...")
        cm = CacheManager(cache_root=self.cache_dir)
        cm.put(pr_url, info.commit_sha, result)

        # Step 8: 输出结果
        self._progress(on_progress, "正在输出结果...")
        outputs = [ConsoleOutput(), JSONOutput()]
        if not skip_markdown:
            outputs.insert(1, MarkdownFileOutput())
        output = CompositeOutput(outputs)
        output.post(result)
        output.flush()

        if tool == "describe":
            self._progress(on_progress, f"分析完成 ({len(result.file_walkthrough)} 个文件)")
        elif tool == "risks":
            self._progress(on_progress, f"风险分析完成 ({len(result.findings)} 个发现)")
        else:
            self._progress(on_progress, f"分析完成 ({len(result.findings)} 个发现)")
        return result

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    @staticmethod
    def _progress(cb, msg):
        if cb:
            cb(msg)

    @staticmethod
    def _detect_main_lang(ld, files):
        if not files:
            return ""
        groups = ld.group_by_language(files)
        if not groups:
            return ""
        return max(groups, key=lambda k: len(groups[k]))

    @staticmethod
    def _calc_budget(depth: AnalysisDepth) -> int:
        """按分析深度分配 token 预算。"""
        if depth == AnalysisDepth.QUICK:
            return int(MAX_TOKENS * 0.3)
        elif depth == AnalysisDepth.DEEP:
            return int(MAX_TOKENS * 0.8)
        return int(MAX_TOKENS * 0.5)  # standard

    @staticmethod
    def _pick_model(depth: AnalysisDepth) -> str:
        """按分析深度选择模型。"""
        if depth == AnalysisDepth.QUICK:
            return config.get("models.weak", DEFAULT_MODEL)
        elif depth == AnalysisDepth.DEEP:
            return config.get("models.reasoning", DEFAULT_MODEL)
        return DEFAULT_MODEL
