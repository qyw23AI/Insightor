"""
主评审逻辑 - 整合所有模块
"""
import sys
import os
from typing import Optional, Dict, List
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fetch_pr.fetch_pr import get_pr_info, get_pr_files
from ai_reviewer.context_builder import ContextBuilder
from ai_reviewer.ai_engine import AIEngine


class PRReviewer:
    """PR 代码评审器"""

    def __init__(
        self,
        repo_path: Optional[str] = None,
        model: str = "claude-opus-4-8",
        max_tokens: int = 4096
    ):
        """
        初始化评审器

        Args:
            repo_path: 本地仓库路径（可选）
            model: AI 模型名称
            max_tokens: 最大 token 数
        """
        self.repo_path = repo_path
        self.context_builder = ContextBuilder(repo_path)
        self.ai_engine = AIEngine(model=model, max_tokens=max_tokens)

    def review_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_types: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        评审 PR

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pr_number: PR 编号
            review_types: 评审类型列表，可选值：
                - comprehensive: 综合评审（默认）
                - security: 安全审查
                - performance: 性能分析
                - quality: 代码质量

        Returns:
            评审结果字典
        """
        print(f"\n🔍 开始评审 PR #{pr_number} ({owner}/{repo})")
        print("=" * 60)

        # 1. 获取 PR 信息
        print("\n📥 获取 PR 信息...")
        pr_data = get_pr_info(owner, repo, pr_number)
        if not pr_data:
            raise ValueError(f"无法获取 PR #{pr_number} 的信息")

        print(f"✓ PR 标题: {pr_data.get('title')}")
        print(f"✓ 作者: {pr_data.get('user', {}).get('login')}")
        print(f"✓ 分支: {pr_data.get('head', {}).get('ref')} → {pr_data.get('base', {}).get('ref')}")

        # 2. 获取文件变更
        print("\n📄 获取文件变更...")
        files_data = get_pr_files(owner, repo, pr_number)
        if not files_data:
            raise ValueError(f"无法获取 PR #{pr_number} 的文件变更")

        print(f"✓ 变更文件数: {len(files_data)}")

        # 3. 构建上下文
        print("\n🔨 构建评审上下文...")
        pr_context = self.context_builder.build_pr_context(pr_data, files_data)

        stats = pr_context['statistics']
        print(f"✓ 总变更: +{stats['total_additions']} -{stats['total_deletions']}")
        print(f"✓ 涉及语言: {', '.join(pr_context['metadata']['languages'])}")

        # 4. 执行 AI 评审
        review_types = review_types or ['comprehensive']
        review_results = {}

        for review_type in review_types:
            print(f"\n🤖 执行 {review_type} 评审...")
            try:
                result = self.ai_engine.review_pr(pr_context, review_type)
                review_results.update(result)
                print(f"✓ {review_type} 评审完成")
            except Exception as e:
                print(f"✗ {review_type} 评审失败: {e}")
                review_results[review_type] = f"评审失败: {str(e)}"

        # 5. 生成总结
        print("\n📊 生成评审总结...")
        try:
            summary = self.ai_engine.summarize_reviews(review_results)
            review_results['summary'] = summary
            print("✓ 总结生成完成")
        except Exception as e:
            print(f"✗ 总结生成失败: {e}")
            review_results['summary'] = "总结生成失败"

        print("\n" + "=" * 60)
        print("✅ 评审完成！")

        return {
            'pr_info': pr_context['pr_info'],
            'statistics': pr_context['statistics'],
            'metadata': pr_context['metadata'],
            'reviews': review_results
        }

    def review_pr_by_url(
        self,
        pr_url: str,
        review_types: Optional[List[str]] = None
    ) -> Dict[str, any]:
        """
        通过 PR URL 评审

        Args:
            pr_url: PR URL，格式如 https://github.com/owner/repo/pull/123
            review_types: 评审类型列表

        Returns:
            评审结果字典
        """
        # 解析 URL
        parts = pr_url.rstrip('/').split('/')
        if len(parts) < 7 or parts[-2] != 'pull':
            raise ValueError(f"无效的 PR URL: {pr_url}")

        owner = parts[-4]
        repo = parts[-3]
        pr_number = int(parts[-1])

        return self.review_pr(owner, repo, pr_number, review_types)

    def save_report(
        self,
        review_result: Dict[str, any],
        output_path: str,
        format: str = "markdown"
    ):
        """
        保存评审报告

        Args:
            review_result: 评审结果
            output_path: 输出文件路径
            format: 输出格式（markdown 或 json）
        """
        if format == "markdown":
            self._save_markdown_report(review_result, output_path)
        elif format == "json":
            self._save_json_report(review_result, output_path)
        else:
            raise ValueError(f"不支持的格式: {format}")

    def _save_markdown_report(self, review_result: Dict[str, any], output_path: str):
        """保存 Markdown 格式报告"""
        pr_info = review_result['pr_info']
        stats = review_result['statistics']
        reviews = review_result['reviews']

        # 构建 Markdown 内容
        lines = [
            f"# PR #{pr_info['number']} 代码评审报告",
            "",
            f"**标题**: {pr_info['title']}",
            f"**作者**: {pr_info['author']}",
            f"**分支**: `{pr_info['source_branch']}` → `{pr_info['target_branch']}`",
            f"**状态**: {pr_info['state']}",
            "",
            "## 📊 变更统计",
            "",
            f"- 总变更: **+{stats['total_additions']} -{stats['total_deletions']}**",
            f"- 文件数: {stats['files_added']} 新增, {stats['files_modified']} 修改, {stats['files_deleted']} 删除",
            "",
        ]

        # 添加总结
        if 'summary' in reviews:
            lines.extend([
                "## 📝 评审总结",
                "",
                reviews['summary'],
                ""
            ])

        # 添加各类评审结果
        for review_type, content in reviews.items():
            if review_type != 'summary':
                lines.extend([
                    f"## 🔍 {review_type.upper()} 评审",
                    "",
                    content,
                    ""
                ])

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"✓ 报告已保存到: {output_path}")

    def _save_json_report(self, review_result: Dict[str, any], output_path: str):
        """保存 JSON 格式报告"""
        import json

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(review_result, f, ensure_ascii=False, indent=2)

        print(f"✓ 报告已保存到: {output_path}")


# 便捷函数
def review_pr(
    owner: str,
    repo: str,
    pr_number: int,
    review_types: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    repo_path: Optional[str] = None
) -> Dict[str, any]:
    """
    快速评审 PR

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        pr_number: PR 编号
        review_types: 评审类型列表
        output_path: 输出文件路径（可选）
        repo_path: 本地仓库路径（可选）

    Returns:
        评审结果
    """
    reviewer = PRReviewer(repo_path=repo_path)
    result = reviewer.review_pr(owner, repo, pr_number, review_types)

    if output_path:
        reviewer.save_report(result, output_path)

    return result


def review_pr_by_url(
    pr_url: str,
    review_types: Optional[List[str]] = None,
    output_path: Optional[str] = None,
    repo_path: Optional[str] = None
) -> Dict[str, any]:
    """
    通过 URL 快速评审 PR

    Args:
        pr_url: PR URL
        review_types: 评审类型列表
        output_path: 输出文件路径（可选）
        repo_path: 本地仓库路径（可选）

    Returns:
        评审结果
    """
    reviewer = PRReviewer(repo_path=repo_path)
    result = reviewer.review_pr_by_url(pr_url, review_types)

    if output_path:
        reviewer.save_report(result, output_path)

    return result
