"""缓存管理器 —— 基于文件的 ReviewResult 缓存，支持增量审查。

缓存路径: .insightor/cache/{owner}/{repo}/pr-{number}/
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from insightor.schemas.urf import ReviewResult


class CacheManager:
    """PR 审查结果持久化缓存。

    用于:
      - 增量审查: 缓存上次结果，下次只分析新 commit
      - 去重: 相同 SHA 的 PR 不重复分析
    """

    def __init__(self, cache_root: str = ".insightor/cache"):
        self.root = Path(cache_root)

    # ------------------------------------------------------------------
    # 公开方法
    # ------------------------------------------------------------------

    def put(self, pr_url: str, sha: str, result: ReviewResult) -> Path:
        """保存 ReviewResult 到缓存。"""
        cache_dir = self._dir_for(pr_url)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # 写入审查结果
        result_path = cache_dir / f"{sha[:12]}.json"
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

        # 更新 latest 指针
        latest_path = cache_dir / "latest.json"
        latest_path.write_text(json.dumps({"sha": sha, "timestamp": datetime.now(timezone.utc).isoformat()}))

        return result_path

    def get(self, pr_url: str, sha: str) -> Optional[ReviewResult]:
        """按 PR URL + commit SHA 精确查找。"""
        cache_dir = self._dir_for(pr_url)
        path = cache_dir / f"{sha[:12]}.json"
        if path.exists():
            return ReviewResult.model_validate_json(path.read_text(encoding="utf-8"))
        return None

    def get_latest(self, pr_url: str) -> Optional[ReviewResult]:
        """获取 PR 的最近一次审查结果（用于增量审查基准）。"""
        cache_dir = self._dir_for(pr_url)
        latest_path = cache_dir / "latest.json"
        if not latest_path.exists():
            return None
        try:
            meta = json.loads(latest_path.read_text(encoding="utf-8"))
            return self.get(pr_url, meta["sha"])
        except (json.JSONDecodeError, KeyError):
            return None

    def get_base_for_incremental(
        self, pr_url: str, current_sha: str
    ) -> tuple[str, Optional[ReviewResult]]:
        """返回上一次审查的 (sha, result)，用于增量 diff 基准。

        如果当前 SHA 已有缓存 → 返回该缓存（无需重新分析）
        否则返回 latest 缓存作为基准（需增量分析）
        """
        cached = self.get(pr_url, current_sha)
        if cached is not None:
            return current_sha, cached

        latest = self.get_latest(pr_url)
        if latest is not None:
            return latest.meta.commit_sha, latest

        return "", None

    def list_reviews(self, pr_url: str) -> list[dict]:
        """列出 PR 的所有历史审查记录。"""
        cache_dir = self._dir_for(pr_url)
        if not cache_dir.exists():
            return []
        results: list[dict] = []
        for path in sorted(cache_dir.glob("*.json")):
            if path.name == "latest.json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                results.append({
                    "sha": data.get("meta", {}).get("commit_sha", path.stem),
                    "timestamp": data.get("meta", {}).get("timestamp", ""),
                    "findings": data.get("stats", {}).get("total_findings", 0),
                })
            except (json.JSONDecodeError, KeyError):
                pass
        return results

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _dir_for(self, pr_url: str) -> Path:
        # https://github.com/owner/repo/pull/123 → owner/repo/pr-123
        import re
        m = re.search(r"github\.com/(\S[^/]+)/(\S[^/]+)/pull/(\d+)", pr_url)
        if m:
            return self.root / m.group(1) / m.group(2) / f"pr-{m.group(3)}"
        # fallback: hash the URL
        import hashlib
        h = hashlib.sha256(pr_url.encode()).hexdigest()[:16]
        return self.root / h
