"""JSONOutput — ReviewResult JSON 持久化。"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from insightor.schemas.urf import ReviewResult


class JSONOutput:
    """将 ReviewResult 保存为 JSON 文件。"""

    def __init__(self, output_dir: str = ".insightor/reviews"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def post(self, result: ReviewResult) -> None:
        meta = result.meta
        sha_short = meta.commit_sha[:8] if meta.commit_sha else "unknown"

        # Extract PR number from URL
        pr_num = "unknown"
        if meta.pr_url:
            parts = meta.pr_url.rstrip("/").split("/")
            if parts and parts[-1].isdigit():
                pr_num = parts[-1]

        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        fname = f"insightor-review-{pr_num}-{sha_short}-{ts}.json"
        path = self._output_dir / fname

        model_dump = result.model_dump(mode="json")

        with open(path, "w", encoding="utf-8") as f:
            json.dump(model_dump, f, ensure_ascii=False, indent=2)

    def flush(self) -> None:
        pass
