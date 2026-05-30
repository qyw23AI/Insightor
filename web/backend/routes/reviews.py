"""Review history routes."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from web.backend.encryption import decrypt

from web.backend.auth import get_current_user
from web.backend.database import get_db
from web.backend.models import Review, ReviewFinding, User, UserConfig

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


class ReviewSummary(BaseModel):
    id: str
    pr_entry_id: str
    pr_url: str
    pr_number: int
    job_id: str
    tool: str
    depth: str
    status: str
    published: bool
    findings_count: int
    score: float | None
    duration_ms: int
    tokens_used: int
    created_at: str | None
    completed_at: str | None


class FeedbackItem(BaseModel):
    finding_id: str
    status: str  # confirmed | false_positive | addressed | ignored
    note: str | None = None
    reviewer: str | None = None


class PublishRequest(BaseModel):
    feedbacks: list[FeedbackItem]


@router.get("", response_model=list[ReviewSummary])
async def list_reviews(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Review).where(Review.user_id == current_user.id).options(selectinload(Review.pr_entry))

    if status == "published":
        query = query.where(Review.published == True)
    elif status == "unpublished":
        query = query.where(Review.published == False, Review.status == "done")

    query = query.order_by(Review.created_at.desc()).limit(20)
    result = await db.execute(query)
    reviews = result.scalars().all()

    summaries = []
    for r in reviews:
        # Get PR URL from entry
        pr_url = ""
        pr_number = 0
        if r.pr_entry:
            pr_url = r.pr_entry.pr_url
            pr_number = r.pr_entry.pr_number

        summaries.append(ReviewSummary(
            id=r.id,
            pr_entry_id=r.pr_entry_id,
            pr_url=pr_url,
            pr_number=pr_number,
            job_id=r.job_id,
            tool=r.tool,
            depth=r.depth,
            status=r.status,
            published=r.published,
            findings_count=r.findings_count,
            score=r.score,
            duration_ms=r.duration_ms,
            tokens_used=r.tokens_used,
            created_at=r.created_at.isoformat() if r.created_at else None,
            completed_at=r.completed_at.isoformat() if r.completed_at else None,
        ))
    return summaries


@router.get("/{review_id}")
async def get_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Review).where(Review.id == review_id, Review.user_id == current_user.id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")

    review_data = None
    if review.result_json:
        review_data = json.loads(review.result_json)

    # Get findings feedback
    f_result = await db.execute(
        select(ReviewFinding).where(ReviewFinding.review_id == review_id)
    )
    findings = f_result.scalars().all()
    feedbacks = {}
    for f in findings:
        if f.feedback_status:
            feedbacks[f.finding_id] = {
                "status": f.feedback_status,
                "note": f.feedback_note,
                "reviewer": f.feedback_by,
            }

    return {
        "review": review_data,
        "diff": review.diff_text,
        "feedbacks": feedbacks,
        "published": review.published,
    }


@router.get("/{review_id}/diff")
async def get_review_diff(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Review).where(Review.id == review_id, Review.user_id == current_user.id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")
    return {"diff": review.diff_text or ""}


@router.post("/{review_id}/publish")
async def publish_review(
    review_id: str,
    req: PublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eagerly load pr_entry to avoid MissingGreenlet
    result = await db.execute(
        select(Review)
        .where(Review.id == review_id, Review.user_id == current_user.id)
        .options(selectinload(Review.pr_entry))
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")
    if not review.result_json:
        raise HTTPException(400, "No review result to publish")

    # Get PR URL for GitHub publishing
    pr_url = review.pr_entry.pr_url if review.pr_entry else ""

    # Get user's GitHub token from config
    github_token = None
    token_result = await db.execute(
        select(UserConfig).where(
            UserConfig.user_id == current_user.id,
            UserConfig.key == "GITHUB_TOKEN",
        )
    )
    token_config = token_result.scalar_one_or_none()
    if token_config and token_config.value:
        github_token = decrypt(token_config.value)

    if not github_token:
        raise HTTPException(400, "Please configure your GitHub Token in Settings first")

    # Update finding feedbacks in DB
    for fb in req.feedbacks:
        f_result = await db.execute(
            select(ReviewFinding).where(
                ReviewFinding.review_id == review_id,
                ReviewFinding.finding_id == fb.finding_id,
            )
        )
        finding = f_result.scalar_one_or_none()
        if finding:
            finding.feedback_status = fb.status
            finding.feedback_note = fb.note
            finding.feedback_by = fb.reviewer

    # Publish to GitHub
    try:
        review_data = json.loads(review.result_json)
        from insightor.schemas.urf import ReviewResult
        result_obj = ReviewResult.model_validate(review_data)

        # Apply feedbacks to the result
        feedback_map = {fb.finding_id: fb for fb in req.feedbacks}
        for f in result_obj.findings:
            fid = str(f.id)
            if fid in feedback_map:
                fb = feedback_map[fid]
                from insightor.schemas.urf import FeedbackStatus, FindingFeedback
                try:
                    status_enum = FeedbackStatus(fb.status)
                except ValueError:
                    continue
                f.feedback = FindingFeedback(
                    status=status_enum,
                    reviewer_note=fb.note,
                    reviewed_by=fb.reviewer or current_user.username,
                    reviewed_at=datetime.now(timezone.utc),
                )

        # Set token in env for PyGithub (it reads from env)
        import os
        old_token = os.environ.get("GITHUB_TOKEN")
        os.environ["GITHUB_TOKEN"] = github_token

        from insightor.output.github_comment import GitHubCommentOutput
        gh_output = GitHubCommentOutput(pr_url=pr_url)
        gh_output.post(result_obj)
        gh_output.flush()

        # Restore env
        if old_token is not None:
            os.environ["GITHUB_TOKEN"] = old_token
        elif "GITHUB_TOKEN" in os.environ:
            del os.environ["GITHUB_TOKEN"]

        review.published = True
        review.published_at = datetime.now(timezone.utc)
        await db.commit()

        return {"published": len(req.feedbacks), "ok": True}

    except Exception as e:
        raise HTTPException(500, f"Publish failed: {e}")


@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Review).where(Review.id == review_id, Review.user_id == current_user.id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(404, "Review not found")

    await db.delete(review)
    await db.commit()
    return {"ok": True}
