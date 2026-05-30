"""Analysis routes: start, stream, get result."""

import asyncio
import json
import logging
import re
import traceback

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web.backend.auth import get_current_user
from web.backend.database import get_db, async_session as _async_session
from web.backend.encryption import decrypt
from web.backend.app import job_manager, sse_manager
from web.backend.models import PREntry, Review, ReviewFinding, User, UserConfig

logger = logging.getLogger("insightor.web.analyze")
router = APIRouter(prefix="/api/analyze", tags=["analyze"])


def _parse_pr_url(url: str) -> tuple[str, int]:
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)", url.strip())
    if not m:
        raise ValueError(f"Invalid GitHub PR URL: {url}")
    return m.group(1), int(m.group(2))


class AnalyzeRequest(BaseModel):
    pr_urls: list[str]
    tool: str = "review"
    depth: str = "standard"
    model: str | None = None


class JobInfo(BaseModel):
    job_id: str
    pr_url: str
    pr_number: int


async def _get_github_token(user_id: str, db: AsyncSession) -> str | None:
    result = await db.execute(
        select(UserConfig).where(
            UserConfig.user_id == user_id,
            UserConfig.key == "GITHUB_TOKEN",
        )
    )
    config = result.scalar_one_or_none()
    if config and config.value:
        return decrypt(config.value)
    return None


async def _run_and_save(
    job_id: str,
    github_token: str | None,
):
    """Run analysis in background and persist results to DB."""
    import datetime as dt
    from datetime import timezone

    logger.info(f"[job={job_id}] Background task started, token={'***' if github_token else 'None'}")

    try:
        await job_manager.run(job_id, sse_manager, github_token)
        logger.info(f"[job={job_id}] Pipeline finished, status={job_manager.get_status(job_id)}")
    except Exception as e:
        logger.error(f"[job={job_id}] Pipeline CRASHED: {e}\n{traceback.format_exc()}")
        # Ensure error state is set even if job_manager.run() itself crashed
        try:
            await sse_manager.publish(job_id, "fail", {
                "message": str(e),
                "code": type(e).__name__,
            })
        except Exception:
            pass

    # Persist results to DB
    try:
        job_result = job_manager.get_result(job_id)
        diff_text = job_manager.get_diff(job_id)

        async with _async_session() as bg_db:
            result = await bg_db.execute(select(Review).where(Review.job_id == job_id))
            review_obj = result.scalar_one_or_none()
            if review_obj:
                if job_result:
                    review_obj.result_json = json.dumps(job_result, ensure_ascii=False)
                    review_obj.findings_count = len(job_result.get("findings", []))
                    mr = job_result.get("merge_readiness")
                    if mr:
                        review_obj.score = mr.get("score", 0)
                    meta = job_result.get("meta", {})
                    review_obj.duration_ms = meta.get("duration_ms", 0)
                    review_obj.tokens_used = meta.get("tokens_used", 0)
                    review_obj.status = "done"
                    review_obj.completed_at = dt.datetime.now(timezone.utc)

                    for f in job_result.get("findings", []):
                        loc = f.get("location", {})
                        loc_path = loc.get("path", "")
                        loc_range = loc.get("range", {})
                        loc_start = loc_range.get("start", {})
                        finding = ReviewFinding(
                            review_id=review_obj.id,
                            finding_id=f.get("id", ""),
                            title=f.get("title", ""),
                            severity=f.get("severity", "info"),
                            category=f.get("category", ""),
                            location_path=loc_path,
                            location_line=loc_start.get("line", 0),
                        )
                        bg_db.add(finding)
                else:
                    review_obj.status = "error"
                    review_obj.completed_at = dt.datetime.now(timezone.utc)

                if diff_text:
                    review_obj.diff_text = diff_text

                pr_result = await bg_db.execute(
                    select(PREntry).where(PREntry.id == review_obj.pr_entry_id)
                )
                pr_entry_obj = pr_result.scalar_one_or_none()
                if pr_entry_obj:
                    pr_entry_obj.status = review_obj.status
                    pr_entry_obj.last_reviewed_at = dt.datetime.now(timezone.utc)

                await bg_db.commit()
                logger.info(f"[job={job_id}] DB updated: status={review_obj.status}")

                # Publish SSE "done" AFTER DB commit so frontend sees persisted data
                done_data = job_manager.pop_done_data(job_id)
                if done_data:
                    await sse_manager.publish(job_id, "done", done_data)
                    logger.info(f"[job={job_id}] SSE done published (after DB commit)")
                else:
                    logger.warning(f"[job={job_id}] No done_data to publish (job may have failed)")

        logger.info(f"[job={job_id}] Background task complete")
    except Exception as e:
        logger.error(f"[job={job_id}] DB persist failed: {e}\n{traceback.format_exc()}")
        # Try to publish fail event if DB persist itself failed
        try:
            await sse_manager.publish(job_id, "fail", {
                "message": f"DB persist failed: {e}",
                "code": type(e).__name__,
            })
        except Exception:
            pass


def _on_task_done(job_id: str):
    """Callback to log task completion and catch silent failures."""
    def cb(task: asyncio.Task):
        try:
            exc = task.exception()
            if exc:
                logger.error(f"[job={job_id}] Unhandled task exception: {exc}\n{traceback.format_exc()}")
                # Try to publish error via SSE
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        sse_manager.publish(job_id, "fail", {
                            "message": str(exc),
                            "code": type(exc).__name__,
                        })
                    )
                except Exception:
                    pass
            else:
                logger.info(f"[job={job_id}] Task completed normally")
        except Exception:
            pass
    return cb


@router.post("", response_model=dict)
async def create_analysis(
    req: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    github_token = await _get_github_token(current_user.id, db)
    logger.info(f"Creating analysis for {len(req.pr_urls)} PR(s) by user={current_user.username}, token={'***' if github_token else 'None'}")

    jobs = []
    for url in req.pr_urls:
        try:
            repo, pr_num = _parse_pr_url(url)
        except ValueError:
            logger.warning(f"Invalid PR URL skipped: {url}")
            continue

        logger.info(f"Creating job for {repo}#{pr_num}")

        job_id = await job_manager.create(
            pr_url=url.strip(),
            pr_number=pr_num,
            repo=repo,
            tool=req.tool,
            depth=req.depth,
            model=req.model,
        )
        logger.info(f"[job={job_id}] Job created, status=pending")

        result = await db.execute(
            select(PREntry).where(
                PREntry.user_id == current_user.id,
                PREntry.pr_url == url.strip(),
            )
        )
        pr_entry = result.scalar_one_or_none()
        if not pr_entry:
            pr_entry = PREntry(
                user_id=current_user.id,
                pr_url=url.strip(),
                pr_number=pr_num,
                repo=repo,
                title=f"{repo}#{pr_num}",
                status="running",
            )
            db.add(pr_entry)
        else:
            pr_entry.status = "running"
        await db.commit()
        await db.refresh(pr_entry)

        review = Review(
            user_id=current_user.id,
            pr_entry_id=pr_entry.id,
            job_id=job_id,
            tool=req.tool,
            depth=req.depth,
            status="running",
        )
        db.add(review)
        await db.commit()

        # Launch background task with error callback
        task = asyncio.create_task(
            _run_and_save(job_id, github_token)
        )
        task.add_done_callback(_on_task_done(job_id))
        logger.info(f"[job={job_id}] Background task scheduled")

        jobs.append(JobInfo(job_id=job_id, pr_url=url.strip(), pr_number=pr_num))

    logger.info(f"Analysis created: {len(jobs)} job(s)")
    return {"jobs": [j.model_dump() for j in jobs]}


@router.get("/{job_id}/stream")
async def stream_analysis(job_id: str):
    status = job_manager.get_status(job_id)
    logger.info(f"[job={job_id}] SSE connect requested, status={status}")
    if status == "not_found":
        raise HTTPException(404, "Job not found")

    queue = await sse_manager.subscribe(job_id)
    logger.info(f"[job={job_id}] SSE subscribed")

    async def event_generator():
        try:
            # --- Immediately replay current state for late-connecting clients ---
            current = job_manager.get_current_state(job_id)
            if current:
                logger.info(f"[job={job_id}] SSE replay: event={current['event']}")
                yield f"event: {current['event']}\ndata: {json.dumps(current['data'], ensure_ascii=False)}\n\n"
                if current["event"] in ("done", "fail"):
                    logger.info(f"[job={job_id}] SSE done/error on replay, closing")
                    return  # Job already finished

            # --- Then stream live events ---
            while True:
                event, data = await queue.get()
                logger.debug(f"[job={job_id}] SSE live: event={event}")
                yield f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
                if event in ("done", "fail"):
                    logger.info(f"[job={job_id}] SSE stream ended: {event}")
                    break
        except asyncio.CancelledError:
            logger.info(f"[job={job_id}] SSE cancelled")
        finally:
            await sse_manager.unsubscribe(job_id, queue)
            logger.info(f"[job={job_id}] SSE unsubscribed")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/result")
async def get_result(job_id: str):
    result = job_manager.get_result(job_id)
    diff = job_manager.get_diff(job_id)
    if result is None:
        raise HTTPException(404, "Result not found")
    return {"review": result, "diff": diff}


@router.get("/{job_id}/info")
async def get_job_info(job_id: str):
    info = job_manager.get_job_info(job_id)
    if info is None:
        raise HTTPException(404, "Job not found")
    return info


@router.post("/jobs/info")
async def batch_job_info(job_ids: list[str]):
    """Get info for multiple jobs at once."""
    return {
        "jobs": [
            info
            for jid in job_ids
            if (info := job_manager.get_job_info(jid)) is not None
        ]
    }
