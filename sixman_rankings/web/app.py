"""FastAPI app: live rankings API + optional built SPA."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from sixman_rankings.export import ranked_record
from sixman_rankings.live.service import get_service
from sixman_rankings.live.window import in_football_window

DIST = Path(__file__).resolve().parents[2] / "web" / "dist"
PAGES_ORIGIN = "https://rcullens.github.io"


def _interval() -> float:
    raw = os.environ.get("SIXMAN_SYNC_INTERVAL_SEC")
    if raw:
        return max(5.0, float(raw))
    return 20.0 if in_football_window() else 120.0


def cors_allow_origins() -> list[str]:
    """GitHub Pages is the phone UI; * still covers APK / Capacitor / LAN serve."""

    raw = os.environ.get("SIXMAN_CORS_ORIGINS")
    if raw is None:
        return [PAGES_ORIGIN, "*"]
    origins = [part.strip() for part in raw.split(",") if part.strip()]
    return origins or [PAGES_ORIGIN, "*"]


def _poller_enabled() -> bool:
    if os.environ.get("SIXMAN_DISABLE_POLLER") == "1":
        return False
    # Fluid/serverless: no long-lived process. Season reloads from committed data.
    if os.environ.get("VERCEL") == "1":
        return False
    return True


def create_app() -> FastAPI:
    app = FastAPI(title="Six-Man Rankings", version="0.3.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins(),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    async def _start_poller() -> None:
        get_service()

        async def loop() -> None:
            while True:
                await asyncio.sleep(_interval())
                try:
                    get_service().sync()
                except Exception:
                    continue

        if _poller_enabled():
            app.state.poller = asyncio.create_task(loop())

    @app.on_event("shutdown")
    async def _stop_poller() -> None:
        task = getattr(app.state, "poller", None)
        if task:
            task.cancel()

    @app.get("/")
    def root():
        return {
            "ok": True,
            "service": "sixman-rank",
            "ui": "https://rcullens.github.io/ranking-tool/",
            "health": "/api/health",
            "docs": "/docs",
        }

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/status")
    def status():
        st = get_service().status()
        return st.__dict__ | {"interval_sec": _interval()}

    @app.post("/api/sync")
    def sync_now():
        return get_service().sync(force_replay=True).__dict__

    @app.post("/api/ingest")
    async def ingest(request: Request):
        payload = await request.json()
        if not isinstance(payload, dict):
            payload = {"games": payload}
        service = get_service()
        n = service.ingest_and_merge(payload)
        return {"ok": True, "updates": n}

    @app.post("/api/what-if")
    async def what_if(request: Request):
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(400, "expected a JSON object")
        try:
            return get_service().what_if(
                home_id=str(body.get("home_id") or body.get("home") or ""),
                away_id=str(body.get("away_id") or body.get("away") or ""),
                home_score=body.get("home_score"),
                away_score=body.get("away_score"),
                margin=body.get("margin"),
                neutral=bool(body.get("neutral")),
                district_game=bool(body.get("district_game")),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get("/api/teams")
    def teams():
        service = get_service()
        table = {r.team_id: r for r in service.rankings()}
        rows = []
        for team in service.teams:
            ranked = table.get(team.team_id)
            rows.append(
                {
                    "team_id": team.team_id,
                    "name": team.name,
                    "district": team.district,
                    "region": team.region,
                    "classification": team.classification,
                    "association": getattr(team, "association", None) or "UIL",
                    "rank": ranked.rank if ranked else None,
                    "record": ranked.record if ranked else "",
                    "power": round(ranked.power, 2) if ranked else None,
                }
            )
        rows.sort(key=lambda r: (r["rank"] is None, r["rank"] or 99, r["name"]))
        return {"teams": rows}

    @app.get("/api/presets")
    def presets():
        return {"presets": get_service().presets()}

    @app.get("/api/rankings")
    def rankings(
        classification: Optional[str] = None,
        district: Optional[str] = None,
        region: Optional[str] = None,
        association: Optional[str] = None,
    ):
        service = get_service()
        rows = service.rankings(
            classification=classification,
            district=district,
            region=region,
            association=association,
        )
        week = service.current_week()
        return {
            "week": week,
            "classification": classification,
            "district": district,
            "region": region,
            "association": association,
            "rankings": [ranked_record(r, week=week, season=service.season) for r in rows],
        }

    @app.get("/api/boards")
    def boards():
        return get_service().boards()

    @app.get("/api/history")
    def history():
        service = get_service()
        hist = service.history()
        return {
            "weeks": sorted(hist),
            "history": {
                str(week): [ranked_record(r, week=week, season=service.season) for r in rows]
                for week, rows in hist.items()
            },
        }

    @app.get("/api/source-ranks")
    def source_ranks():
        from sixman_rankings.live.source_ranks import source_ranks_payload

        return source_ranks_payload(get_service(), pull=False, persist=False)

    @app.get("/api/compare")
    def compare(teams: str = "", metric: str = "power"):
        ids = [part.strip() for part in teams.split(",") if part.strip()]
        if not ids:
            presets = get_service().presets()
            ids = presets.get("last_week_top10") or presets.get("this_week_top10") or []
        if metric not in {"power", "rank"}:
            raise HTTPException(400, "metric must be power or rank")
        return get_service().compare_series(ids, metric=metric)

    if DIST.is_dir():
        assets = DIST / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404)
            target = DIST / path
            if path and target.is_file():
                return FileResponse(target)
            index = DIST / "index.html"
            if index.is_file():
                return FileResponse(index)
            raise HTTPException(404, "frontend not built")

    return app


app = create_app()
