"""Job lifecycle manager — wraps ReviewPipeline for web API."""

import asyncio
import json
import logging
import os
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from insightor.pipeline import ReviewPipeline
from insightor.schemas.urf import ReviewResult

from web.backend.sse_manager import SSEManager

logger = logging.getLogger("insightor.web.job_manager")

JOB_STORE = Path(".insightor/jobs")

# Reference-counting lock for env vars — prevents race between concurrent jobs
# that need different per-user API keys / tokens. On first job we save current
# env var state; each subsequent job overwrites; last job restores the original.
_env_lock = asyncio.Lock()
_active_token_jobs = 0
_saved_env_vars: dict[str, str | None] = {}

# Config keys to inject as env vars. If a value is a list, set each alias to the
# same value (handles both _API_BASE / _BASE_URL naming conventions).
_CONFIG_ENV_MAP: dict[str, str | list[str]] = {
    "GITHUB_TOKEN": "GITHUB_TOKEN",
    "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY": "OPENAI_API_KEY",
    "DEEPSEEK_API_KEY": "DEEPSEEK_API_KEY",
    "ANTHROPIC_BASE_URL": ["ANTHROPIC_API_BASE", "ANTHROPIC_BASE_URL"],
    "OPENAI_API_BASE": ["OPENAI_API_BASE", "OPENAI_BASE_URL"],
    "DEEPSEEK_API_BASE": ["DEEPSEEK_API_BASE", "DEEPSEEK_BASE_URL"],
    "INSIGHTOR_MODELS_PRIMARY": "INSIGHTOR_MODELS_PRIMARY",
    "INSIGHTOR_MODELS_WEAK": "INSIGHTOR_MODELS_WEAK",
    "INSIGHTOR_MODELS_REASONING": "INSIGHTOR_MODELS_REASONING",
    "INSIGHTOR_REVIEW_MIN_SEVERITY": "INSIGHTOR_REVIEW_MIN_SEVERITY",
    "INSIGHTOR_REVIEW_MAX_FINDINGS": "INSIGHTOR_REVIEW_MAX_FINDINGS",
}

# Known pipeline steps for progress estimation
_PIPELINE_STEPS = [
    "获取 PR 数据",
    "处理代码变更",
    "优化输入",
    "构建分析提示",
    "AI 分析",
    "解析分析结果",
    "保存结果",
    "输出结果",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_progress_callback(sse_manager: SSEManager, job_id: str, job_dict: dict | None = None):
    """Bridge sync on_progress callback to async SSE publish."""

    def callback(msg: str):
        # Detect which step we're in based on the message
        step_index = -1
        step_total = len(_PIPELINE_STEPS)
        for i, keyword in enumerate(_PIPELINE_STEPS):
            if keyword in msg:
                step_index = i + 1
                break

        # Store last step for late-connecting SSE clients
        if job_dict is not None:
            job_dict["last_step"] = msg
            job_dict["last_step_index"] = step_index

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                sse_manager.publish(
                    job_id,
                    "step",
                    {
                        "step": msg,
                        "step_index": step_index,
                        "step_total": step_total,
                        "timestamp": _now_iso(),
                    },
                )
            )
        except RuntimeError:
            pass

    return callback


def _iter_env_keys(user_configs: dict[str, str]):
    """Yield all env var keys that would be set for the given config dict."""
    for cfg_key in user_configs:
        targets = _CONFIG_ENV_MAP.get(cfg_key)
        if not targets:
            continue
        if isinstance(targets, str):
            yield targets
        else:
            yield from targets


def _iter_env_items(user_configs: dict[str, str]):
    """Yield (env_key, value) pairs for all config entries that have an env mapping."""
    for cfg_key, value in user_configs.items():
        targets = _CONFIG_ENV_MAP.get(cfg_key)
        if not targets:
            continue
        if isinstance(targets, str):
            yield targets, value
        else:
            for alias in targets:
                yield alias, value


class JobManager:
    def __init__(self):
        self._jobs: dict[str, dict] = {}
        JOB_STORE.mkdir(parents=True, exist_ok=True)

    async def create(
        self,
        pr_url: str,
        pr_number: int,
        repo: str,
        tool: str = "review",
        depth: str = "standard",
        model: str | None = None,
    ) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "repo": repo,
            "tool": tool,
            "depth": depth,
            "model": model,
            "status": "pending",
            "result": None,
            "diff_text": None,
            "error": None,
            "last_step": None,
            "last_step_index": 0,
            "created_at": _now_iso(),
        }
        return job_id

    async def run(
        self,
        job_id: str,
        sse_manager: SSEManager,
        user_configs: dict[str, str] | None = None,
    ):
        global _active_token_jobs, _saved_env_vars

        job = self._jobs.get(job_id)
        if not job:
            logger.error(f"[job={job_id}] Job not found in _jobs dict — cannot run!")
            return

        logger.info(f"[job={job_id}] Starting pipeline: pr={job.get('pr_url')}, tool={job.get('tool')}, depth={job.get('depth')}")
        job["status"] = "running"
        job["started_at"] = _now_iso()
        on_progress = _make_progress_callback(sse_manager, job_id, job)

        pipeline = ReviewPipeline(model=job.get("model"))

        try:
            # --- Safely set user configs as env vars with reference counting ---
            user_configs = user_configs or {}
            async with _env_lock:
                if user_configs:
                    if _active_token_jobs == 0:
                        # Save current state before first job overwrites anything
                        _saved_env_vars.clear()
                        for env_key in _iter_env_keys(user_configs):
                            _saved_env_vars[env_key] = os.environ.get(env_key)
                    for env_key, env_val in _iter_env_items(user_configs):
                        os.environ[env_key] = env_val
                    _active_token_jobs += 1

            # Run the pipeline (GitHubProvider reads token from env on init)
            logger.info(f"[job={job_id}] Calling pipeline.run()...")
            result: ReviewResult = await pipeline.run(
                pr_url=job["pr_url"],
                tool=job["tool"],
                depth=job["depth"],
                on_progress=on_progress,
            )
            logger.info(f"[job={job_id}] Pipeline finished successfully, findings={len(result.findings) if hasattr(result, 'findings') else 0}")

            job["result"] = result

            # Get diff text — pass token explicitly so it works even if
            # another job has already finished and decremented the refcount.
            diff_text = ""
            try:
                from insightor.providers.github_provider import GitHubProvider

                github_token = user_configs.get("GITHUB_TOKEN")
                provider = GitHubProvider(token=github_token)
                raw_diff = provider.get_diff(job["pr_url"])  # sync, returns bytes
                if isinstance(raw_diff, bytes):
                    diff_text = raw_diff.decode("utf-8", errors="replace")
                else:
                    diff_text = str(raw_diff)
                logger.info(f"[job={job_id}] Diff fetched: {len(diff_text)} chars")
            except Exception as e:
                logger.warning(f"[job={job_id}] Failed to fetch diff: {e}")
            job["diff_text"] = diff_text

            # Send findings one by one
            findings_list = result.findings if hasattr(result, 'findings') else []
            for f in findings_list:
                await sse_manager.publish(job_id, "finding", f.model_dump(mode="json"))
                await asyncio.sleep(0)

            # Store done data — caller (_run_and_save) will publish SSE "done"
            # AFTER persisting to DB, so frontend sees complete data on reload.
            job["_done_data"] = {
                "meta": result.meta.model_dump(mode="json"),
                "stats": result.stats.model_dump(mode="json"),
                "findings_count": len(findings_list),
                "merge_readiness": (
                    result.merge_readiness.model_dump(mode="json")
                    if result.merge_readiness
                    else None
                ),
                "diff_text": diff_text,
            }
            job["status"] = "done"

        except Exception as e:
            logger.error(f"[job={job_id}] Pipeline error: {e}\n{traceback.format_exc()}")
            job["status"] = "error"
            job["error"] = str(e)
            await sse_manager.publish(
                job_id,
                "fail",
                {
                    "message": str(e),
                    "code": type(e).__name__,
                },
            )

        finally:
            # --- Restore env vars with reference counting ---
            if user_configs:
                async with _env_lock:
                    _active_token_jobs -= 1
                    if _active_token_jobs == 0:
                        for env_key, saved_val in _saved_env_vars.items():
                            if saved_val is not None:
                                os.environ[env_key] = saved_val
                            elif env_key in os.environ:
                                del os.environ[env_key]
                        _saved_env_vars.clear()

            job["finished_at"] = _now_iso()
            self._save_job(job_id)
            logger.info(f"[job={job_id}] Job complete: status={job['status']}")

    def get_status(self, job_id: str) -> str:
        job = self._jobs.get(job_id)
        if not job:
            path = JOB_STORE / f"{job_id}.json"
            if path.exists():
                return "done"
            return "not_found"
        return job.get("status", "not_found")

    def get_result(self, job_id: str) -> dict | None:
        job = self._jobs.get(job_id)
        if not job:
            return self._load_from_disk(job_id)
        if job.get("result"):
            return job["result"].model_dump(mode="json")
        return None

    def get_diff(self, job_id: str) -> str | None:
        job = self._jobs.get(job_id)
        if not job:
            data = self._load_raw(job_id)
            if data:
                return data.get("diff_text")
            return None
        return job.get("diff_text")

    def get_job_info(self, job_id: str) -> dict | None:
        """Get job metadata (for multi-job progress display)."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        return {
            "job_id": job.get("job_id"),
            "pr_url": job.get("pr_url"),
            "pr_number": job.get("pr_number"),
            "repo": job.get("repo"),
            "tool": job.get("tool"),
            "depth": job.get("depth"),
            "status": job.get("status"),
            "error": job.get("error"),
            "created_at": job.get("created_at"),
        }

    def pop_done_data(self, job_id: str) -> dict | None:
        """Get and clear the stored SSE 'done' event data (so it's only published once)."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        return job.pop("_done_data", None)

    def get_current_state(self, job_id: str) -> dict | None:
        """Get current state for late-connecting SSE clients to replay."""
        job = self._jobs.get(job_id)
        if not job:
            return None
        status = job.get("status", "pending")
        state: dict = {"status": status}

        if status == "done" and job.get("result"):
            result = job["result"]
            state["event"] = "done"
            state["data"] = {
                "meta": result.meta.model_dump(mode="json"),
                "stats": result.stats.model_dump(mode="json"),
                "findings_count": len(result.findings if hasattr(result, 'findings') else []),
                "merge_readiness": (
                    result.merge_readiness.model_dump(mode="json")
                    if result.merge_readiness else None
                ),
                "diff_text": job.get("diff_text", ""),
            }
        elif status == "error":
            state["event"] = "fail"
            state["data"] = {
                "message": job.get("error", "Unknown error"),
                "code": "JobError",
            }
        elif status == "running":
            state["event"] = "step"
            state["data"] = {
                "step": job.get("last_step") or "Starting...",
                "step_index": job.get("last_step_index", 0),
                "step_total": len(_PIPELINE_STEPS),
                "timestamp": _now_iso(),
            }
        else:
            state["event"] = "step"
            state["data"] = {
                "step": "Queued...",
                "step_index": 0,
                "step_total": len(_PIPELINE_STEPS),
                "timestamp": _now_iso(),
            }

        return state

    def _save_job(self, job_id: str):
        job = self._jobs.get(job_id)
        if not job:
            return
        data = {}
        if job.get("result"):
            data["result"] = job["result"].model_dump(mode="json")
        if job.get("diff_text"):
            data["diff_text"] = job["diff_text"]
        data["status"] = job.get("status", "done")
        data["job_id"] = job_id
        data["pr_url"] = job.get("pr_url", "")
        data["pr_number"] = job.get("pr_number", 0)
        data["repo"] = job.get("repo", "")
        data["tool"] = job.get("tool", "review")
        data["depth"] = job.get("depth", "standard")
        if data:
            path = JOB_STORE / f"{job_id}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_from_disk(self, job_id: str) -> dict | None:
        data = self._load_raw(job_id)
        if data and "result" in data:
            return data["result"]
        return None

    def _load_raw(self, job_id: str) -> dict | None:
        path = JOB_STORE / f"{job_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None
