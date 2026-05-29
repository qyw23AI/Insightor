"""Insightor Feedback Layer — Human-in-the-loop review and feedback tracking.

Provides:
  - DraftParser: Parse human-edited Markdown drafts into ReviewResult feedback
  - QualityTracker: Track historical precision metrics per category
  - FeedbackCollector: Collect developer feedback from GitHub Reactions (stubbed)
"""

from insightor.feedback.collector import FeedbackCollector
from insightor.feedback.draft_parser import DraftParser
from insightor.feedback.quality_tracker import QualityTracker

__all__ = [
    "DraftParser",
    "QualityTracker",
    "FeedbackCollector",
]
