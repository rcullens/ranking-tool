"""Vercel Python catch-all so /api/* hits FastAPI on the existing Vite git project."""

from sixman_rankings.web.app import app

__all__ = ["app"]
