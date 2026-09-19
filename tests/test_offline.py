from pathlib import Path

from sixman_rankings.live.service import LiveSeasonService
from sixman_rankings.offline import snapshot, write_offline_bundle


def test_offline_bundle_has_api_shaped_files(tmp_path: Path):
    dest = write_offline_bundle(tmp_path, service=LiveSeasonService.from_sample(start_week=4))
    names = {path.name for path in dest.iterdir()}
    assert names == {"status.json", "teams.json", "presets.json", "rankings.json", "boards.json", "history.json"}
    data = snapshot(LiveSeasonService.from_sample(start_week=4))
    assert data["status"]["provider"] == "offline-snapshot"
    assert len(data["rankings"]["rankings"]) == 20
    assert data["boards"]["districts"]
    assert data["boards"]["regions"]
    assert 0 in data["history"]["weeks"]
    assert "borden-county" in data["presets"]["presets"]["this_week_top10"]
