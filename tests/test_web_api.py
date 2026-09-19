"""FastAPI live ranking endpoints."""

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from sixman_rankings.io import DEMO_DATA
from sixman_rankings.live.service import reset_service
from sixman_rankings.web.app import create_app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("SIXMAN_FEED_URL", raising=False)
    monkeypatch.setenv("SIXMAN_DATA_DIR", str(DEMO_DATA))
    monkeypatch.setenv("SIXMAN_LIVE_START_WEEK", "4")
    monkeypatch.setenv("SIXMAN_DISABLE_POLLER", "1")
    reset_service()
    app = create_app()
    # Don't run the background poller in tests.
    app.router.on_startup.clear()
    with TestClient(app) as test_client:
        yield test_client
    reset_service()


def test_status_and_rankings(client):
    status = client.get("/api/status").json()
    assert status["current_week"] == 4
    table = client.get("/api/rankings").json()
    assert table["week"] == 4
    assert len(table["rankings"]) == 20
    assert table["rankings"][0]["team_id"]


def test_compare_defaults_to_a_preset(client):
    body = client.get("/api/compare").json()
    assert body["series"]
    assert body["metric"] == "power"


def test_boards_break_out_districts_and_regions(client):
    body = client.get("/api/boards").json()
    assert body["week"] == 4
    district_ids = {board["id"] for board in body["districts"]}
    region_ids = {board["id"] for board in body["regions"]}
    assert district_ids == {"8-1A DI", "9-1A DI", "2-1A DII", "1-1A DII", "5-1A DI"}
    assert region_ids == {"west-texas", "panhandle", "trans-pecos", "rolling-plains"}
    eight = next(board for board in body["districts"] if board["id"] == "8-1A DI")
    assert eight["power"][0]["local_rank"] == 1
    assert eight["power"][0]["statewide_rank"] >= 1
    assert {row["district"] for row in eight["power"]} == {"8-1A DI"}
    assert eight["standings"]
    west = next(board for board in body["regions"] if board["id"] == "west-texas")
    assert west["label"] == "West Texas"
    assert all(row["region"] == "west-texas" for row in west["power"])


def test_rankings_accept_district_and_region_filters(client):
    district = client.get("/api/rankings", params={"district": "8-1A DI"}).json()
    assert {row["district"] for row in district["rankings"]} == {"8-1A DI"}
    assert district["rankings"][0]["rank"] == 1
    region = client.get("/api/rankings", params={"region": "panhandle"}).json()
    assert {row["region"] for row in region["rankings"]} == {"panhandle"}


def test_what_if_is_provisional(client):
    before = client.get("/api/rankings").json()["rankings"]
    body = client.post(
        "/api/what-if",
        json={
            "home": "Darrouzett",
            "away": "Borden County",
            "home_score": 70,
            "away_score": 14,
        },
    ).json()
    assert body["writes_back"] is False
    assert body["movers"]
    after = client.get("/api/rankings").json()["rankings"]
    assert [row["power"] for row in before] == [row["power"] for row in after]


def test_rankings_classification_split(client):
    di = client.get("/api/rankings", params={"classification": "DI"}).json()
    assert di["rankings"]
    assert all("DII" not in row["classification"] for row in di["rankings"])
    assert di["rankings"][0]["rank"] == 1


def test_sync_and_ingest(client):
    before = client.get("/api/status").json()["finals"]
    synced = client.post("/api/sync").json()
    assert synced["finals"] >= before
    posted = client.post(
        "/api/ingest",
        json={
            "games": [
                {
                    "week": 9,
                    "home": "Borden County",
                    "away": "Rankin",
                    "home_score": 50,
                    "away_score": 12,
                    "status": "final",
                }
            ]
        },
    )
    assert posted.json()["ok"] is True
