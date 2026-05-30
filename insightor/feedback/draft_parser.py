"""DraftParser — Parse human-edited Markdown draft into ReviewResult feedback."""

import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from insightor.schemas.urf import FeedbackStatus, FindingFeedback, ReviewResult


class DraftParser:
    """Parse human-edited Markdown review draft to extract feedback.

    The markdown file contains finding IDs as HTML comments and feedback
    checkboxes that humans can toggle before publishing.
    """

    FINDING_ID_RE = re.compile(r"<!--\s*finding-id:\s*([a-f0-9\-]+)\s*-->")
    CHECKBOX_RE = re.compile(r"-\s*\[\s*([xX]?)\s*\]\s*(\w+)")
    REVIEWER_RE = re.compile(r"\*\*审查者:\*\*\s*(.*)")
    NOTE_RE = re.compile(r"\*\*备注:\*\*\s*(.*)")

    @staticmethod
    def parse(md_path: str, original_result: ReviewResult) -> tuple[ReviewResult, int]:
        """Parse edited markdown and apply feedback onto original result.

        Args:
            md_path: Path to the human-edited markdown file.
            original_result: Original ReviewResult to apply feedback onto.

        Returns:
            Tuple of (updated ReviewResult, count of feedbacks that changed).
        """
        md_text = Path(md_path).read_text(encoding="utf-8")
        feedback_map = DraftParser._extract_feedback_map(md_text)

        change_count = 0
        for finding in original_result.findings:
            if finding.id in feedback_map:
                fb = feedback_map[finding.id]
                if finding.feedback != fb:
                    finding.feedback = fb
                    change_count += 1

        return original_result, change_count

    @staticmethod
    def _extract_feedback_map(md_text: str) -> dict[UUID, FindingFeedback]:
        lines = md_text.split("\n")
        result: dict[UUID, FindingFeedback] = {}

        for i, line in enumerate(lines):
            id_match = DraftParser.FINDING_ID_RE.search(line)
            if not id_match:
                continue

            try:
                finding_id = UUID(id_match.group(1))
            except ValueError:
                continue

            section_lines = lines[i:]
            # Stop at the next finding-id marker to avoid bleeding into another finding
            for j, sl in enumerate(section_lines):
                if j > 0 and DraftParser.FINDING_ID_RE.search(sl):
                    section_lines = section_lines[:j]
                    break
            section = "\n".join(section_lines)

            status: FeedbackStatus | None = None
            for cb_match in DraftParser.CHECKBOX_RE.finditer(section):
                if cb_match.group(1).strip().lower() == "x":
                    try:
                        status = FeedbackStatus(cb_match.group(2).lower())
                        break
                    except ValueError:
                        continue

            if status is None:
                continue

            reviewer = None
            note = None
            r_match = DraftParser.REVIEWER_RE.search(section)
            n_match = DraftParser.NOTE_RE.search(section)
            if r_match:
                reviewer = r_match.group(1).strip() or None
            if n_match:
                note = n_match.group(1).strip() or None

            result[finding_id] = FindingFeedback(
                status=status,
                reviewer_note=note,
                reviewed_by=reviewer,
                reviewed_at=datetime.now(timezone.utc),
            )

        return result
