"""
Shared test setup.

Fixtures in tests/fixtures/<match_id>/ are real MLS API responses saved from
the four endpoints `MLSApiClient.get_all_match_data()` calls, plus videos.json
(trimmed to the fields we read) from `get_videos()`. A missing file means that
endpoint returned 404 (e.g. the stats API before a match), or for videos, that
there are none yet.
"""
import copy
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Always test against config-example.py, never a local config.py with real
# secrets or non-default feature flags.
_spec = importlib.util.spec_from_file_location("config", ROOT / "config-example.py")
_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config)
sys.modules["config"] = _config

# Thread titles and headers use local time.
os.environ["TZ"] = "America/Chicago"
time.tzset()

from api_client import ApiEndpoint, MLSApiClient, MLSApiClientError  # noqa: E402

FINAL_ID = "MLS-MAT-0009MQ"     # STL 6-2 LA Galaxy, regular season, includes a penalty goal
SHOOTOUT_ID = "MLS-MAT-000A8K"  # STL 2-2 HOU (4-2 pens), U.S. Open Cup, extra time + coach cards
PRE_MATCH_ID = "MLS-MAT-0009N5" # STL vs VAN, 3 days out: only the sport API has data
# 2025 MLS Cup Playoffs Round One, SD vs POR: Game 1 SD 2-1, Game 2 POR 2-2 (3-2 pens),
# Game 3 SD 4-0. Games 1 and 2 only have match_base saved.
SERIES_GAME_3_ID = "MLS-MAT-00098X"
SERIES_EARLIER_IDS = ("MLS-MAT-00098S", "MLS-MAT-00098W")
KNOCKOUT_ID = "MLS-MAT-00099K"  # 2025 Conference Semifinal, VAN 2-2 LAFC (4-3 pens) after extra time
# 2026 playoff placeholders saved before the matchups were set: TBC teams, no
# season optaId, and roundName "best_of_3" with a blank roundGroup.
PLACEHOLDER_ROUND_ONE_ID = "MLS-MAT-000ACR"  # Round One, Game 1
PLACEHOLDER_MLS_CUP_ID = "MLS-MAT-000ABL"

PAYLOAD_NAMES = ("match_info", "match_base", "match_stats", "match_events")


def load_fixture(match_id: str, name: str) -> Optional[dict]:
    path = FIXTURES / match_id / f"{name}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_schedule_json() -> dict:
    """STL's 2026 schedule from the stats API, saved on 2026-10-12."""
    with open(FIXTURES / "schedule_2026.json", encoding="utf-8") as f:
        return json.load(f)


def load_sd_schedule() -> dict:
    """San Diego FC's schedule from Oct 20, 2025 on, saved on 2026-11-08: the
    Round One series with Portland, then the Conference Semifinal and Final."""
    with open(FIXTURES / "schedule_sd_2025.json", encoding="utf-8") as f:
        return json.load(f)


def load_payloads(match_id: str) -> Dict[str, Optional[dict]]:
    return {name: load_fixture(match_id, name) for name in PAYLOAD_NAMES + ("videos",)}


def _scheduled_payloads() -> Dict[str, Optional[dict]]:
    """~30 min before kickoff: lineups are out, no events or stats yet."""
    payloads = load_payloads(FINAL_ID)
    info = payloads["match_base"]["match_information"]
    info.update(match_status="scheduled", home_team_goals=0, away_team_goals=0, minute_of_play=None)
    payloads["match_events"]["events"] = []
    payloads["match_stats"] = None
    return payloads


def _live_payloads() -> Dict[str, Optional[dict]]:
    """33rd minute of the final fixture, rebuilt by dropping later events."""
    payloads = load_payloads(FINAL_ID)
    cutoff = "2026-10-11T23:45:30Z"
    events = payloads["match_events"]["events"]
    payloads["match_events"]["events"] = [e for e in events if e["event"]["event_time"] < cutoff]
    info = payloads["match_base"]["match_information"]
    info.update(match_status="firstHalf", home_team_goals=3, away_team_goals=1, minute_of_play="33")
    return payloads


def _halftime_payloads() -> Dict[str, Optional[dict]]:
    """Halftime break: the API reports match_status "half" with minute_of_play "46"."""
    payloads = _live_payloads()
    payloads["match_base"]["match_information"].update(match_status="half", minute_of_play="46")
    return payloads


def _without(match_id: str, *names: str) -> Dict[str, Optional[dict]]:
    payloads = load_payloads(match_id)
    for name in names:
        payloads[name] = None
    return payloads


def _empty_events() -> Dict[str, Optional[dict]]:
    payloads = load_payloads(FINAL_ID)
    payloads["match_events"]["events"] = []
    return payloads


def _series_payloads(match_id: str, earlier: tuple = ()) -> Dict[str, Optional[dict]]:
    """A best-of-3 game plus match_base for the earlier games in its series."""
    payloads = load_payloads(match_id)
    payloads["other_match_bases"] = {mid: load_fixture(mid, "match_base") for mid in earlier}
    return payloads


def _series_game_payloads(status: str, home_goals: int, away_goals: int,
                          minute: Optional[str]) -> Dict[str, Optional[dict]]:
    """The Game 3 fixture rewound to an earlier point in the match."""
    payloads = _series_payloads(SERIES_GAME_3_ID, SERIES_EARLIER_IDS)
    info = payloads["match_base"]["match_information"]
    info.update(match_status=status, home_team_goals=home_goals, away_team_goals=away_goals,
                minute_of_play=minute)
    if status == "scheduled":
        payloads["match_events"]["events"] = []
        payloads["match_stats"] = None
    return payloads


MATCH_STATES = {
    "pre_match": lambda: load_payloads(PRE_MATCH_ID),
    "scheduled": _scheduled_payloads,
    "live": _live_payloads,
    "halftime": _halftime_payloads,
    "final": lambda: load_payloads(FINAL_ID),
    "playoff_series": lambda: _series_payloads(SERIES_GAME_3_ID, SERIES_EARLIER_IDS),
    "playoff_series_scheduled": lambda: _series_game_payloads("scheduled", 0, 0, None),
    "playoff_knockout": lambda: load_payloads(KNOCKOUT_ID),
    "playoff_placeholder": lambda: load_payloads(PLACEHOLDER_ROUND_ONE_ID),
    "playoff_mls_cup_placeholder": lambda: load_payloads(PLACEHOLDER_MLS_CUP_ID),
    "shootout": lambda: load_payloads(SHOOTOUT_ID),
    "missing_base": lambda: _without(FINAL_ID, "match_base"),
    "missing_events": lambda: _without(FINAL_ID, "match_events"),
    "missing_stats": lambda: _without(FINAL_ID, "match_stats"),
    "empty_events": _empty_events,
}


class FixtureClient(MLSApiClient):
    """
    MLSApiClient that serves saved payloads instead of calling the API.
    A payload set to None raises the same 404 client error the real API does.
    """

    def __init__(self, payloads: Dict[str, Optional[dict]]):
        super().__init__()
        self.payloads = payloads

    async def _make_request(self, endpoint, path, params=None, allow_404=False):
        if path.startswith("/matches/seasons/"):
            name = "schedule"
        elif endpoint == ApiEndpoint.SPORT and path.split("/")[-1] in self.payloads.get("other_match_infos", {}):
            return copy.deepcopy(self.payloads["other_match_infos"][path.split("/")[-1]])
        elif path.endswith("/key_events"):
            name = "match_events"
        elif path.startswith("/statistics/clubs/matches/"):
            name = "match_stats"
        elif endpoint == ApiEndpoint.VIDEO:
            name = "videos"
        elif endpoint == ApiEndpoint.SPORT:
            name = "match_info"
        elif endpoint == ApiEndpoint.MATCHES:
            name = "match_base"
            other = self.payloads.get("other_match_bases", {})
            if path in other:
                return copy.deepcopy(other[path])
        else:
            raise AssertionError(f"Unexpected request in test: {endpoint} {path}")

        payload = self.payloads.get(name)
        if payload is None:
            if allow_404:
                return {}
            raise MLSApiClientError(f"Client error 404: Requested resource does not exist\n{path}")
        return copy.deepcopy(payload)


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """Run each test in an empty directory so data/*.json from a real install isn't read."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(params=sorted(MATCH_STATES))
def state(request) -> str:
    return request.param


async def make_match(state: str):
    from match import Match

    payloads = MATCH_STATES[state]()
    match_id = payloads["match_info"]["sportecId"]
    return await Match.create(match_id, client=FixtureClient(payloads))
