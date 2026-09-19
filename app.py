"""ASGI entrypoint for Vercel / uvicorn (`sixman-rank serve`)."""

from sixman_rankings.web.app import app

__all__ = ["app"]
