"""Vercel Python function: exposes the FastAPI jyotisha engine.

Vercel rewrites /api/py/(.*) to this function (see vercel.json). The ASGI
request keeps the ORIGINAL path (/api/py/...), so we remap it onto the
FastAPI app's route table: /api/py/health -> /health, /api/py/<x> -> /api/<x>.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app as fastapi_app  # noqa: E402


class _RemapPath:
    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            if path == "/api/py" or path.startswith("/api/py/"):
                rest = path[len("/api/py"):].lstrip("/")
                new_path = "/health" if rest in ("", "health") else f"/api/{rest}"
                scope = dict(scope)
                scope["path"] = new_path
                if scope.get("raw_path"):
                    scope["raw_path"] = new_path.encode()
        await self._app(scope, receive, send)


app = _RemapPath(fastapi_app)
