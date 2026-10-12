from datetime import datetime, timezone

import pytest

from conftest import FINAL_ID, MATCH_STATES, FixtureClient, make_match
from match import Match

HOME = "MLS-CLU-00001L"  # St. Louis CITY SC
LA = "MLS-CLU-00000G"
HOU = "MLS-CLU-00000H"


async def test_every_accessor_survives_every_state(state):
    """The bot calls these on each refresh; none may raise, whatever data is missing."""
    match = await make_match(state)
    match.get_score()
    match.get_result_type()
    match.get_goalscorers()
    match.get_subs()
    match.get_feed()
    match.get_events()
    match.get_starting_lineups()
    match.get_broadcasters()
    match.get_utc_datetime()
    match.get_local_date_string()
    match.get_local_time_string()
    match.get_data_string()
    match.is_started()
    match.is_final()


async def test_pre_match():
    match = await make_match("pre_match")
    assert len(match.data.errors) == 3
    assert not match.is_started()
    assert match.get_score() == "0-0"
    assert match.get_utc_datetime() is None
    assert match.get_goalscorers() == {}
    assert match.get_starting_lineups() == {}
    assert match.get_local_date_string() == "October 14, 2026"
    assert match.get_local_time_string().startswith("07:30 PM")
    assert [b.broadcasterName for b in match.get_broadcasters()] == ["Apple TV"]


async def test_scheduled_with_lineups():
    match = await make_match("scheduled")
    assert not match.is_started()
    assert match.get_result_type() == ""
    assert len(match.home_starters) == 11
    assert len(match.away_starters) == 11
    assert match.get_goalscorers() == {}


async def test_live():
    match = await make_match("live")
    assert match.is_started()
    assert not match.is_final()
    assert match.minute_display == "33"
    assert match.get_score() == "3-1"
    assert match.get_result_type() == ""
    assert match.get_goalscorers() == {
        HOME: ["Carlo Holse (2', 7', 21')"],
        LA: ["Robert Taylor (31')"],
    }


async def test_final():
    match = await make_match("final")
    assert match.is_final()
    assert match.get_score() == "6-2"
    assert match.get_result_type() == "FT"
    assert match.get_utc_datetime() == datetime(2026, 10, 11, 23, 0, tzinfo=timezone.utc)
    assert match.get_goalscorers() == {
        HOME: [
            "Carlo Holse (2', 7', 21')",
            "Rafael Navarro (45' pen, 53')",
            "Lukas MacNaughton (45+7')",
        ],
        LA: ["Robert Taylor (31')", "João Klauss (71')"],
    }
    subs = match.get_subs()
    assert len(subs[HOME]) == 5
    assert len(subs[LA]) == 5


async def test_shootout():
    match = await make_match("shootout")
    assert match.get_score() == "2-2 (4-2 pens)"
    assert match.get_result_type() == "AET (Pens)"
    # Shootout kicks are 'goals' events too, but must not be listed as scorers.
    assert match.get_goalscorers() == {
        HOME: ["Marcel Hartel (10', 51' pen)"],
        HOU: ["Mateusz Bogusz (11')", "José Artur (42')"],
    }


async def test_missing_base():
    """#84: match_base can be None while other endpoints have data."""
    match = await make_match("missing_base")
    assert match.get_score() == "0-0"
    assert match.get_utc_datetime() is None
    assert match.get_goalscorers() == {}
    assert match.get_subs() == {}


async def test_missing_events():
    """#81: match_events can be None while match_base has data."""
    match = await make_match("missing_events")
    assert match.get_score() == "6-2"
    assert match.get_result_type() == "FT"
    assert match.get_goalscorers() == {}
    assert match.get_feed() == []


async def test_empty_events_still_final():
    match = await make_match("empty_events")
    assert match.get_result_type() == "FT"


async def test_refresh_moves_through_states():
    """Mirrors the match thread loop: one Match object refreshed as data appears."""
    client = FixtureClient(MATCH_STATES["pre_match"]())
    client.payloads["match_info"]["sportecId"] = FINAL_ID
    match = await Match.create(FINAL_ID, client=client)
    assert match.get_score() == "0-0"

    for state, score in [("scheduled", "0-0"), ("live", "3-1"), ("final", "6-2")]:
        client.payloads = MATCH_STATES[state]()
        await match.refresh(client=client)
        assert match.get_score() == score
    assert match.is_final()
    assert match.home_goals == 6


async def test_create_raises_without_match_info():
    payloads = MATCH_STATES["final"]()
    payloads["match_info"] = None
    with pytest.raises(ValueError):
        await Match.create(FINAL_ID, client=FixtureClient(payloads))


async def test_injuries_and_discipline_files(isolated_cwd):
    (isolated_cwd / "data").mkdir()
    (isolated_cwd / "data" / "injuries.json").write_text('{"injuries": {"17012": ["Player A"]}}')
    (isolated_cwd / "data" / "discipline.json").write_text('{"discipline": {"1708": {"Suspended": ["Player B"]}}}')
    match = await make_match("pre_match")
    assert match.injuries == {"17012": ["Player A"]}
    assert match.discipline == {"1708": {"Suspended": ["Player B"]}}


async def test_corrupt_injuries_file(isolated_cwd):
    (isolated_cwd / "data").mkdir()
    (isolated_cwd / "data" / "injuries.json").write_text("not json")
    match = await make_match("pre_match")
    assert match.injuries == {}
