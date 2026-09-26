"""Application entrypoint.

Serves the JSON/SSE API and, when a frontend build exists
(frontend/dist), the assistant UI itself — one process, one port.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .db import init_db

app = FastAPI(title="Personal AI Assistant", version="0.1.0")

# The UI may be served from a dev server or a desktop shell later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.include_router(router)

_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        candidate = (_FRONTEND_DIST / path).resolve()
        if (
            path
            and candidate.is_file()
            and candidate.is_relative_to(_FRONTEND_DIST)
        ):
            return FileResponse(candidate)
        return FileResponse(_FRONTEND_DIST / "index.html")
