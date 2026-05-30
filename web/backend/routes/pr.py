"""PR entry routes: save, list, delete PRs."""

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.auth import get_current_user
from web.backend.database import get_db
from web.backend.models import PREntry, User

router = APIRouter(prefix="/api/pr", tags=["pr"])


def _parse_pr_url(url: str) -> tuple[str, int]:
    """Extract repo and PR number from GitHub URL."""
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", url.strip())
    if not m:
        raise ValueError(f"Invalid GitHub PR URL: {url}")
    return m.group(1), int(m.group(2))


class PREntryRequest(BaseModel):
    pr_urls: list[str]


class PREntryResponse(BaseModel):
    id: str
    pr_url: str
    pr_number: int
    repo: str
    title: str
    status: str
    added_at: str | None
    last_reviewed_at: str | None


@router.get("/entries", response_model=list[PREntryResponse])
async def list_entries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PREntry)
        .where(PREntry.user_id == current_user.id)
        .order_by(PREntry.added_at.desc())
        .limit(50)
    )
    entries = result.scalars().all()
    return [
        PREntryResponse(
            id=e.id,
            pr_url=e.pr_url,
            pr_number=e.pr_number,
            repo=e.repo,
            title=e.title,
            status=e.status,
            added_at=e.added_at.isoformat() if e.added_at else None,
            last_reviewed_at=e.last_reviewed_at.isoformat() if e.last_reviewed_at else None,
        )
        for e in entries
    ]


@router.post("/entries", response_model=list[PREntryResponse])
async def add_entries(
    req: PREntryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    added = []
    for url in req.pr_urls:
        try:
            repo, pr_num = _parse_pr_url(url)
        except ValueError:
            continue

        result = await db.execute(
            select(PREntry).where(
                PREntry.user_id == current_user.id,
                PREntry.pr_url == url.strip(),
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            added.append(existing)
            continue

        entry = PREntry(
            user_id=current_user.id,
            pr_url=url.strip(),
            pr_number=pr_num,
            repo=repo,
            title=f"{repo}#{pr_num}",
            status="pending",
        )
        db.add(entry)
        added.append(entry)

    await db.commit()
    for e in added:
        await db.refresh(e)

    return [
        PREntryResponse(
            id=e.id,
            pr_url=e.pr_url,
            pr_number=e.pr_number,
            repo=e.repo,
            title=e.title,
            status=e.status,
            added_at=e.added_at.isoformat() if e.added_at else None,
            last_reviewed_at=e.last_reviewed_at.isoformat() if e.last_reviewed_at else None,
        )
        for e in added
    ]


@router.delete("/entries/{entry_id}")
async def delete_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PREntry).where(
            PREntry.id == entry_id,
            PREntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="PR entry not found")

    await db.delete(entry)
    await db.commit()
    return {"ok": True}
