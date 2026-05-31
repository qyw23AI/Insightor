"""FastAPI application factory for Insightor Web."""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from insightor import __version__

from web.backend.sse_manager import SSEManager
from web.backend.job_manager import JobManager

# --- Logging setup: visible in uvicorn console ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
# Ensure insightor modules are at INFO level
logging.getLogger("insightor").setLevel(logging.INFO)
logging.getLogger("insightor.web").setLevel(logging.DEBUG)

# Module-level singletons — survive uvicorn reload
sse_manager = SSEManager()
job_manager = JobManager()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Insightor Web",
        version=__version__,
        description="AI-Powered PR Review Console",
    )

    # CORS for dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Set on state for route compatibility
    app.state.sse_manager = sse_manager
    app.state.job_manager = job_manager

    # Import routes lazily to avoid circular imports
    from web.backend.routes.auth import router as auth_router
    from web.backend.routes.admin import router as admin_router
    from web.backend.routes.config import router as config_router
    from web.backend.routes.pr import router as pr_router
    from web.backend.routes.analyze import router as analyze_router
    from web.backend.routes.reviews import router as reviews_router

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(config_router)
    app.include_router(pr_router)
    app.include_router(analyze_router)
    app.include_router(reviews_router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "version": __version__}

    # Production static file serving (when React is built)
    dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if dist_dir.exists() and (dist_dir / "index.html").exists():
        # Mount /assets first — serves JS, CSS, and other static assets
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # SPA catch-all: serve index.html for any unmatched GET request.
        # This MUST come after all API routes and the /assets mount so that
        # API calls and static assets are not swallowed.
        # IMPORTANT: Register any new API routes BEFORE this point.
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            from fastapi.responses import FileResponse
            return FileResponse(dist_dir / "index.html")

    return app


app = create_app()
