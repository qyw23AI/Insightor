"""QualityTracker — Track historical accuracy of findings per category."""

import json
from datetime import datetime, timezone
from pathlib import Path

from insightor.schemas.urf import QualityMetrics, ReviewResult


class QualityTracker:
    """Track and persist historical precision metrics per finding category.

    Persists to:
      .insightor/quality/history.json  — cumulative feedback counts
      .insightor/quality/metrics.json   — pre-computed QualityMetrics
    """

    _FILE_HISTORY = "history.json"
    _FILE_METRICS = "metrics.json"

    def __init__(self, storage_dir: str = ".insightor/quality"):
        self._storage_dir = Path(storage_dir)

    def track(self, result: ReviewResult) -> None:
        """Analyze feedback in result and update historical precision."""
        history = self._load_history()
        categories = history.setdefault("categories", {})

        for finding in result.findings:
            if not finding.feedback or finding.feedback.status is None:
                continue
            cat = finding.category
            cat_data = categories.setdefault(cat, {
                "total": 0, "confirmed": 0, "false_positive": 0,
                "addressed": 0, "ignored": 0,
            })
            cat_data["total"] += 1
            status_key = finding.feedback.status.value
            if status_key in cat_data:
                cat_data[status_key] += 1

        history["total_reviews"] = history.get("total_reviews", 0) + 1
        history["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save_history(history)
        self._save_metrics(self._compute_metrics(history))

    def get_precision(self, category: str) -> float:
        """Return confirmed / total for a category. Returns 0.0 if no data."""
        history = self._load_history()
        cat = history.get("categories", {}).get(category, {})
        total = cat.get("total", 0)
        if total == 0:
            return 0.0
        return cat.get("confirmed", 0) / total

    def export_metrics(self) -> QualityMetrics:
        """Return consolidated quality metrics with historical_precision."""
        metrics_dict = self._load_metrics()
        return QualityMetrics(**metrics_dict)

    def _ensure_dir(self) -> Path:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        return self._storage_dir

    def _load_history(self) -> dict:
        path = self._ensure_dir() / self._FILE_HISTORY
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"categories": {}, "total_reviews": 0, "last_updated": None}

    def _save_history(self, data: dict) -> None:
        path = self._ensure_dir() / self._FILE_HISTORY
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_metrics(self) -> dict:
        path = self._ensure_dir() / self._FILE_METRICS
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"historical_precision": {}}

    def _save_metrics(self, data: dict) -> None:
        path = self._ensure_dir() / self._FILE_METRICS
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _compute_metrics(history: dict) -> dict:
        cats = history.get("categories", {})
        precision: dict[str, float] = {}
        for cat_name, cat_data in cats.items():
            total = cat_data.get("total", 0)
            if total > 0:
                precision[cat_name] = round(
                    cat_data.get("confirmed", 0) / total, 3
                )
        return {"historical_precision": precision}
