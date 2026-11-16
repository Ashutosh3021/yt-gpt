"""Serve the bundled frontend and fall back to the repo's Vite build."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from ..util import safe_child


def frontend_root() -> Path:
    packaged = Path(__file__).resolve().parent / "static"
    if (packaged / "index.html").exists():
        return packaged
    dev = Path(__file__).resolve().parents[4] / "frontend" / "dist"
    if (dev / "index.html").exists():
        return dev
    return packaged


def mount_frontend(app: FastAPI) -> None:
    root = frontend_root()
    assets = root / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")
        if full_path:
            try:
                candidate = safe_child(root, *full_path.split("/"))
            except ValueError:
                raise HTTPException(status_code=404, detail="Not found.") from None
            if candidate.is_file():
                return FileResponse(candidate)
        index = root / "index.html"
        if index.is_file():
            return FileResponse(index, headers={"Cache-Control": "no-cache"})
        return HTMLResponse(
            "<!doctype html><html><body style='font-family:system-ui;padding:2rem'>"
            "<h1>yt-gpt backend is running</h1>"
            "<p>The frontend bundle is missing. Build it with "
            "<code>cd frontend &amp;&amp; npm run build</code> or reinstall the package.</p>"
            "</body></html>",
            status_code=200,
        )
