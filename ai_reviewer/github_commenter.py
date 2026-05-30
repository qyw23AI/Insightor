import os
import requests
from typing import Dict


def _build_summary_markdown(review_result: Dict) -> str:
    pr = review_result.get('pr_info', {})
    reviews = review_result.get('reviews', {})

    lines = [f"# AI Review for PR #{pr.get('number')}: {pr.get('title')}", ""]
    if 'summary' in reviews:
        lines.extend(["## Summary", "", reviews['summary'], ""])

    # Add short per-section excerpts
    for k, v in reviews.items():
        if k == 'summary':
            continue
        lines.extend([f"### {k}", "", (v or '')[:1000], ""])

    return "\n".join(lines)


def post_review_comment(owner: str, repo: str, pr_number: int, review_result: Dict, comment_type: str, token: str) -> bool:
    """
    Post a review comment to a GitHub PR (issue comments).

    comment_type: 'summary'|'full'|'separate' (separate currently behaves like full)
    """
    if not token:
        print("⚠️  GITHUB_TOKEN not provided, skipping post to GitHub")
        return False

    if comment_type == 'summary':
        body = _build_summary_markdown(review_result)
    else:
        # full or separate -> post the full markdown report
        # Reuse PRReviewer._save_markdown_report style by building content here
        pr = review_result.get('pr_info', {})
        stats = review_result.get('statistics', {})
        reviews = review_result.get('reviews', {})

        parts = [
            f"# PR #{pr.get('number')} Review Report",
            "",
            f"**Title**: {pr.get('title')}",
            f"**Author**: {pr.get('author')}",
            "",
            "## Summary",
            "",
            reviews.get('summary', ''),
            "",
        ]

        for review_type, content in reviews.items():
            if review_type == 'summary':
                continue
            parts.extend([f"## {review_type.upper()}", "", content or '', ""])

        body = "\n".join(parts)

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Insightor-AI-Reviewer"
    }

    resp = requests.post(url, json={"body": body}, headers=headers)
    if resp.status_code in (200, 201):
        print(f"✓ Posted comment to PR #{pr_number} ({comment_type})")
        return True
    else:
        print(f"✗ Failed to post comment: {resp.status_code} - {resp.text}")
        return False
