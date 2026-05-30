"""FeedbackCollector — Collect developer feedback from GitHub Reactions.

Note: The GitHub Reactions reading is stubbed for now. Full implementation
requires a PR comment to exist first, so it will be completed in a follow-up PR.
"""

from insightor.schemas.urf import ReviewResult


class FeedbackCollector:
    """Collect developer feedback from GitHub comment reactions.

    This is a placeholder. In the future it will:
      1. Find the bot comment on the PR
      2. Read emoji reactions (:+1:, :-1:, etc.)
      3. Map reactions to FeedbackStatus
      4. Update the ReviewResult
    """

    async def collect(self, result: ReviewResult) -> ReviewResult:
        """Stub: pass-through, no-op until Reactions reading is implemented."""
        return result

    async def read_comment_reactions(self, comment_url: str) -> dict[str, str]:
        """Stub: read reactions from a GitHub comment.

        Raises:
            NotImplementedError: Always — not yet implemented.
        """
        raise NotImplementedError(
            "GitHub Reactions feedback collection will be implemented "
            "in a future PR once the PR comment posting workflow is established."
        )
