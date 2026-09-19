"""Live score ingest, football-night scheduler, and in-memory season store."""

from sixman_rankings.live.service import LiveSeasonService, get_service

__all__ = ["LiveSeasonService", "get_service"]
