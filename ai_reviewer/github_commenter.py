"""
GitHub 评论发布模块 - 将评审结果发布到 GitHub PR
"""
import os
import requests
from typing import Dict, Optional, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class GitHubCommenter:
    """GitHub PR 评论发布器"""

    def __init__(self, token: Optional[str] = None):
        """
        初始化评论发布器

        Args:
            token: GitHub Personal Access Token（如果不提供，从环境变量读取）
        """
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("未找到 GitHub Token，请设置 GITHUB_TOKEN 环境变量")

        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        self.base_url = 'https://api.github.com'

    def post_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_result: Dict[str, any],
        comment_type: str = "summary"
    ) -> Dict[str, any]:
        """
        发布评审评论到 PR

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pr_number: PR 编号
            review_result: 评审结果字典
            comment_type: 评论类型
                - summary: 只发布总结（默认）
                - full: 发布完整评审结果
                - separate: 分别发布每个评审类型

        Returns:
            GitHub API 响应
        """
        print(f"\n📤 准备发布评审评论到 PR #{pr_number}...")

        if comment_type == "summary":
            return self._post_summary_comment(owner, repo, pr_number, review_result)
        elif comment_type == "full":
            return self._post_full_comment(owner, repo, pr_number, review_result)
        elif comment_type == "separate":
            return self._post_separate_comments(owner, repo, pr_number, review_result)
        else:
            raise ValueError(f"不支持的评论类型: {comment_type}")

    def _post_summary_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_result: Dict[str, any]
    ) -> Dict[str, any]:
        """发布总结评论"""
        comment_body = self._format_summary_comment(review_result)
        return self._post_issue_comment(owner, repo, pr_number, comment_body)

    def _post_full_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_result: Dict[str, any]
    ) -> Dict[str, any]:
        """发布完整评审评论"""
        comment_body = self._format_full_comment(review_result)
        return self._post_issue_comment(owner, repo, pr_number, comment_body)

    def _post_separate_comments(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_result: Dict[str, any]
    ) -> List[Dict[str, any]]:
        """分别发布每个评审类型的评论"""
        responses = []

        # 先发布总结
        if 'summary' in review_result.get('reviews', {}):
            summary_body = self._format_summary_comment(review_result)
            response = self._post_issue_comment(owner, repo, pr_number, summary_body)
            responses.append(response)

        # 再发布各个评审类型
        for review_type, content in review_result.get('reviews', {}).items():
            if review_type != 'summary':
                comment_body = self._format_single_review_comment(review_type, content, review_result)
                response = self._post_issue_comment(owner, repo, pr_number, comment_body)
                responses.append(response)

        return responses

    def _post_issue_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str
    ) -> Dict[str, any]:
        """
        发布 Issue 评论（PR 也是 Issue）

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pr_number: PR 编号
            body: 评论内容

        Returns:
            GitHub API 响应
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        payload = {'body': body}

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"✓ 评论已发布: {result.get('html_url')}")
            return result
        except requests.exceptions.RequestException as e:
            print(f"✗ 发布评论失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  响应内容: {e.response.text}")
            raise

    def _format_summary_comment(self, review_result: Dict[str, any]) -> str:
        """格式化总结评论"""
        pr_info = review_result.get('pr_info', {})
        stats = review_result.get('statistics', {})
        reviews = review_result.get('reviews', {})

        lines = [
            "## 🤖 AI 代码评审报告",
            "",
            "### 📊 变更统计",
            "",
            f"- **总变更**: +{stats.get('total_additions', 0)} -{stats.get('total_deletions', 0)}",
            f"- **文件数**: {stats.get('files_added', 0)} 新增, {stats.get('files_modified', 0)} 修改, {stats.get('files_deleted', 0)} 删除",
            ""
        ]

        # 添加语言分布
        if 'metadata' in review_result and 'languages' in review_result['metadata']:
            languages = review_result['metadata']['languages']
            if languages:
                lines.extend([
                    f"- **涉及语言**: {', '.join(languages)}",
                    ""
                ])

        # 添加总结
        if 'summary' in reviews:
            lines.extend([
                "### 📝 评审总结",
                "",
                reviews['summary'],
                ""
            ])

        # 添加评审类型列表
        review_types = [rt for rt in reviews.keys() if rt != 'summary']
        if review_types:
            lines.extend([
                "### 🔍 评审类型",
                "",
                "本次评审包含以下类型：",
                ""
            ])
            for rt in review_types:
                lines.append(f"- {rt.upper()}")
            lines.append("")

        lines.extend([
            "---",
            "*由 AI 代码评审工具自动生成*"
        ])

        return '\n'.join(lines)

    def _format_full_comment(self, review_result: Dict[str, any]) -> str:
        """格式化完整评审评论"""
        pr_info = review_result.get('pr_info', {})
        stats = review_result.get('statistics', {})
        reviews = review_result.get('reviews', {})

        lines = [
            "## 🤖 AI 代码评审报告（完整版）",
            "",
            "### 📊 变更统计",
            "",
            f"- **总变更**: +{stats.get('total_additions', 0)} -{stats.get('total_deletions', 0)}",
            f"- **文件数**: {stats.get('files_added', 0)} 新增, {stats.get('files_modified', 0)} 修改, {stats.get('files_deleted', 0)} 删除",
            ""
        ]

        # 添加语言分布
        if 'metadata' in review_result and 'languages' in review_result['metadata']:
            languages = review_result['metadata']['languages']
            if languages:
                lines.extend([
                    f"- **涉及语言**: {', '.join(languages)}",
                    ""
                ])

        # 添加总结
        if 'summary' in reviews:
            lines.extend([
                "### 📝 评审总结",
                "",
                reviews['summary'],
                ""
            ])

        # 添加各类评审结果
        for review_type, content in reviews.items():
            if review_type != 'summary':
                lines.extend([
                    f"### 🔍 {review_type.upper()} 评审",
                    "",
                    content,
                    ""
                ])

        lines.extend([
            "---",
            "*由 AI 代码评审工具自动生成*"
        ])

        return '\n'.join(lines)

    def _format_single_review_comment(
        self,
        review_type: str,
        content: str,
        review_result: Dict[str, any]
    ) -> str:
        """格式化单个评审类型的评论"""
        lines = [
            f"## 🔍 {review_type.upper()} 评审",
            "",
            content,
            "",
            "---",
            "*由 AI 代码评审工具自动生成*"
        ]

        return '\n'.join(lines)

    def create_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        review_result: Dict[str, any],
        event: str = "COMMENT"
    ) -> Dict[str, any]:
        """
        创建 PR Review（支持 APPROVE/REQUEST_CHANGES/COMMENT）

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pr_number: PR 编号
            review_result: 评审结果
            event: Review 事件类型
                - COMMENT: 仅评论（默认）
                - APPROVE: 批准
                - REQUEST_CHANGES: 请求修改

        Returns:
            GitHub API 响应
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

        body = self._format_summary_comment(review_result)
        payload = {
            'body': body,
            'event': event
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"✓ Review 已创建: {result.get('html_url')}")
            return result
        except requests.exceptions.RequestException as e:
            print(f"✗ 创建 Review 失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  响应内容: {e.response.text}")
            raise

    def post_inline_comments(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        comments: List[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """
        发布行内评论（针对具体代码行）

        Args:
            owner: 仓库所有者
            repo: 仓库名称
            pr_number: PR 编号
            comments: 评论列表，每个评论包含：
                - path: 文件路径
                - line: 行号
                - body: 评论内容

        Returns:
            GitHub API 响应列表
        """
        # 获取 PR 的最新 commit SHA
        pr_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
        pr_response = requests.get(pr_url, headers=self.headers)
        pr_response.raise_for_status()
        pr_data = pr_response.json()
        commit_id = pr_data['head']['sha']

        # 创建 Review 并添加行内评论
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"

        review_comments = []
        for comment in comments:
            review_comments.append({
                'path': comment['path'],
                'line': comment['line'],
                'body': comment['body']
            })

        payload = {
            'commit_id': commit_id,
            'event': 'COMMENT',
            'comments': review_comments
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"✓ 已发布 {len(review_comments)} 条行内评论")
            return result
        except requests.exceptions.RequestException as e:
            print(f"✗ 发布行内评论失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  响应内容: {e.response.text}")
            raise


# 便捷函数
def post_review_to_github(
    owner: str,
    repo: str,
    pr_number: int,
    review_result: Dict[str, any],
    comment_type: str = "summary",
    token: Optional[str] = None
) -> Dict[str, any]:
    """
    快速发布评审结果到 GitHub

    Args:
        owner: 仓库所有者
        repo: 仓库名称
        pr_number: PR 编号
        review_result: 评审结果
        comment_type: 评论类型（summary/full/separate）
        token: GitHub Token（可选）

    Returns:
        GitHub API 响应
    """
    commenter = GitHubCommenter(token=token)
    return commenter.post_review_comment(owner, repo, pr_number, review_result, comment_type)
