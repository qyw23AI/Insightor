"""GitHubCommentOutput — 将审查结果发布为 GitHub PR 评论。"""

import logging
import os

from insightor.schemas.urf import ReviewResult, Severity

logger = logging.getLogger(__name__)

BOT_SIGNATURE = "🤖 **Insightor**"
_SEVERITY_ICON = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟡",
    Severity.MEDIUM: "🔵",
    Severity.LOW: "⚪",
    Severity.INFO: "ℹ️",
}


class GitHubCommentOutput:
    """将 ReviewResult 以结构化评论发布到 GitHub PR。

    要求: 环境变量 GITHUB_TOKEN 已设置。
    """

    def __init__(self, pr_url: str, update_existing: bool = True):
        self._pr_url = pr_url
        self._update_existing = update_existing
        self._comment_id: int | None = None

    def post(self, result: ReviewResult) -> None:
        try:
            import github
            from github import Auth, Github
        except ImportError:
            logger.warning("PyGithub 未安装，跳过 GitHub 评论发布")
            return

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_ACCESS_TOKEN")
        if not token:
            logger.warning("未设置 GITHUB_TOKEN，跳过 GitHub 评论发布")
            return

        # Parse PR URL
        parts = self._pr_url.rstrip("/").split("/")
        pr_num_idx = -1
        for i, p in enumerate(parts):
            if p == "pull":
                pr_num_idx = i + 1
                break
        if pr_num_idx < 0:
            logger.warning("无法解析 PR URL: %s", self._pr_url)
            return

        owner = parts[-4]
        repo = parts[-3]
        pr_number = int(parts[pr_num_idx])

        body = self._build_comment(result)

        client = Github(auth=Auth.Token(token))
        try:
            pr = client.get_repo(f"{owner}/{repo}").get_pull(pr_number)

            if self._update_existing:
                existing = self._find_bot_comment(pr)
                if existing:
                    existing.edit(body)
                    self._comment_id = existing.id
                    logger.info("已更新 GitHub 评论 #%d", existing.id)
                    return

            comment = pr.create_issue_comment(body)
            self._comment_id = comment.id
            logger.info("已发布 GitHub 评论 #%d", comment.id)
        except Exception:
            logger.exception("发布 GitHub 评论失败")

    def flush(self) -> None:
        pass

    @property
    def comment_id(self) -> int | None:
        return self._comment_id

    def _build_comment(self, result: ReviewResult) -> str:
        s = result.summary
        mr = result.merge_readiness
        lines: list[str] = []

        # Header
        lines.append(BOT_SIGNATURE)
        lines.append("")
        lines.append(f"**{s.pr_type.upper() or 'REVIEW'}** — {s.overview or '审查完成'}")

        # Summary
        lines.append(f"")
        lines.append(f"## 总结")
        lines.append(f"")
        lines.append(f"- **类型**: {s.pr_type or 'N/A'}")
        lines.append(f"- **概述**: {s.overview or '无'}")
        lines.append(f"- **文件变更**: {result.meta.files_analyzed} 个  |  发现: {len(result.findings)} 个")

        # Merge Readiness
        if mr:
            score_icon = "✅" if mr.score >= 80 else "⚠️" if mr.score >= 50 else "🔴"
            lines.append(f"")
            lines.append(f"## 合并风险评估")
            lines.append(f"")
            lines.append(f"- **评分**: {score_icon} {mr.score:.0f}/100 — {mr.recommendation.value}")
            if mr.blocking_issues:
                lines.append(f"- **阻断问题**: {len(mr.blocking_issues)} 个")
                for bi in mr.blocking_issues:
                    lines.append(f"  - {bi}")
            if mr.summary:
                lines.append(f"- {mr.summary}")

        # File Walkthrough
        if result.file_walkthrough:
            lines.append(f"")
            lines.append(f"## 变更文件 ({len(result.file_walkthrough)})")
            lines.append(f"")
            lines.append("| 操作 | 文件 | 说明 |")
            lines.append("|------|------|------|")
            for fw in result.file_walkthrough:
                lines.append(f"| {fw.edit_type.value} | `{fw.path}` | {fw.summary[:80]} |")

        # Findings (full detail, same structure as markdown)
        if result.findings:
            lines.append(f"")
            lines.append(f"## 发现 ({len(result.findings)})")
            for i, f in enumerate(result.findings, 1):
                icon = _SEVERITY_ICON.get(f.severity, "")
                lines.append(f"")
                lines.append(f"### {i}. {icon} [{f.severity.value}] {f.title}")
                lines.append(f"")
                lines.append(f"- **类别**: {f.category}")
                lines.append(f"- **文件**: `{f.location.path}:{f.location.range.start.line}`")
                if f.description:
                    lines.append(f"- **说明**: {f.description}")
                if f.suggestion:
                    if f.suggestion.current_code:
                        lines.append(f"- **当前代码**:")
                        lines.append(f"  ```")
                        lines.append(f"  {f.suggestion.current_code}")
                        lines.append(f"  ```")
                    if f.suggestion.suggested_code:
                        lines.append(f"- **建议代码**:")
                        lines.append(f"  ```")
                        lines.append(f"  {f.suggestion.suggested_code}")
                        lines.append(f"  ```")
                if f.confidence:
                    lines.append(f"- **置信度**: {f.confidence:.0%}")
                if f.feedback and f.feedback.status is not None:
                    feedback_status = f.feedback.status.value
                    fb_map = {"confirmed": "已确认", "false_positive": "误报",
                              "addressed": "已处理", "ignored": "忽略"}
                    lines.append(f"- **反馈**: {fb_map.get(feedback_status, feedback_status)}")
                    if f.feedback.reviewer_note:
                        lines.append(f"  - 备注: {f.feedback.reviewer_note}")

        return "\n".join(lines)

    @staticmethod
    def _find_bot_comment(pr):
        """查找已有 bot 评论。"""
        try:
            for comment in pr.get_issue_comments():
                if BOT_SIGNATURE in (comment.body or ""):
                    return comment
        except Exception:
            pass
        return None
