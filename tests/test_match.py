from datetime import datetime, timezone

import pytest

from conftest import (
    FINAL_ID, MATCH_STATES, SERIES_EARLIER_IDS, SERIES_GAME_3_ID, FixtureClient, _series_payloads,
    load_fixture, make_match,
)
from match import Match

HOME = "MLS-CLU-00001L"  # St. Louis CITY SC
LA = "MLS-CLU-00000G"
HOU = "MLS-CLU-00000H"


async def test_every_accessor_survives_every_state(state):
    """The bot calls these on each refresh; none may raise, whatever data is missing."""
    match = await make_match(state)
    match.get_score()
    match.get_result_type()
    match.get_status_display()
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
    match.get_playoff_round()
    match.get_competition_display()
    match.get_series_status()
    match.get_series_status(include_current=False)
    match.is_unneeded_series_game()


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


async def test_status_display():
    assert (await make_match("pre_match")).get_status_display() == ""
    assert (await make_match("scheduled")).get_status_display() == ""
    assert (await make_match("live")).get_status_display() == "33'"
    halftime = await make_match("halftime")
    assert halftime.get_status_display() == "HT"
    assert halftime.minute_display == "46"  # still drives the update interval


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


SD = "MLS-CLU-000065"
POR = "MLS-CLU-00000P"


@pytest.mark.parametrize("round_name, round_number, round_group, expected", [
    # 2025 slugs
    ("match-round-wildcard", 1, "", "Wild Card"),
    ("match-round-bo3", 3, "game_2", "Round One, Game 2 of 3"),
    ("match-round-semis", 5, "", "Conference Semifinal"),
    ("match-round-finals", 6, "", "Conference Final"),
    # 2026 slugs: no roundGroup, so the game number comes from roundNumber
    ("best_of_3", 2, "", "Round One, Game 1 of 3"),
    ("best_of_3", 4, "", "Round One, Game 3 of 3"),
    ("match-round-cup", 7, "", "MLS Cup"),
    # Unknown slug: fall back to roundNumber
    ("something-new", 5, "", "Conference Semifinal"),
])
async def test_playoff_round_names(round_name, round_number, round_group, expected):
    payloads = MATCH_STATES["playoff_knockout"]()
    payloads["match_base"] = None  # so match_type ("Semifinals") can't supply a game number
    payloads["match_info"].update(roundName=round_name, roundNumber=round_number, roundGroup=round_group)
    match = await Match.create(payloads["match_info"]["sportecId"], client=FixtureClient(payloads))
    assert str(match.get_playoff_round()) == expected


async def test_no_playoff_round_outside_playoffs():
    """The U.S. Open Cup fixture has roundName 'Quarter-Finals' but isn't a playoff match."""
    for state in ("final", "shootout", "pre_match"):
        match = await make_match(state)
        assert match.get_playoff_round() is None
        assert match.get_series_status() is None
        assert match.get_competition_display() == match.competition


async def test_series_game_3():
    match = await make_match("playoff_series")
    # Game 1 SD 2-1, Game 2 POR on penalties
    assert match.series_winners == [SD, POR]
    assert match.get_series_score(include_current=False) == {SD: 1, POR: 1}
    assert match.get_series_score() == {SD: 2, POR: 1}
    assert match.get_winner_id() == SD
    assert match.get_series_status(include_current=False) == "Series tied 1-1"
    assert match.get_series_status() == (
        "San Diego FC wins the series 2-1 and advances to the Conference Semifinals"
    )
    assert not match.is_unneeded_series_game()


async def test_series_game_2_lead():
    payloads = _series_payloads(SERIES_EARLIER_IDS[1], SERIES_EARLIER_IDS[:1])
    # Only match_base is saved for Game 2; borrow Game 3's sport API data
    info = load_fixture(SERIES_GAME_3_ID, "match_info")
    info.update(sportecId=SERIES_EARLIER_IDS[1], roundNumber=3, roundGroup="game_2",
                home=info["away"], away=info["home"])
    payloads["match_info"] = info
    base = payloads["match_base"]["match_information"]
    base.update(match_status="secondHalf", minute_of_play="60")
    match = await Match.create(SERIES_EARLIER_IDS[1], client=FixtureClient(payloads))
    assert str(match.get_playoff_round()) == "Round One, Game 2 of 3"
    assert match.series_winners == [SD]
    assert match.get_series_status() == "San Diego FC leads the series 1-0"


async def test_game_3_after_2_0_series_is_unneeded():
    payloads = _series_payloads(SERIES_GAME_3_ID, SERIES_EARLIER_IDS)
    # Make SD win Game 2 outright
    game_2 = payloads["other_match_bases"][SERIES_EARLIER_IDS[1]]["match_information"]
    game_2.update(home_team_penalty_goals=2, away_team_penalty_goals=4)
    match = await Match.create(SERIES_GAME_3_ID, client=FixtureClient(payloads))
    assert match.series_winners == [SD, SD]
    assert match.is_unneeded_series_game()


async def test_series_unknown_when_earlier_game_missing():
    """If the drawn Game 2 can't be looked up, show no series status rather than a wrong one."""
    payloads = _series_payloads(SERIES_GAME_3_ID, SERIES_EARLIER_IDS[:1])
    match = await Match.create(SERIES_GAME_3_ID, client=FixtureClient(payloads))
    assert match.series_winners is None
    assert match.get_series_status() is None
    assert str(match.get_playoff_round()) == "Round One, Game 3 of 3"
    assert not match.is_unneeded_series_game()


async def test_knockout_winner_on_penalties():
    match = await make_match("playoff_knockout")
    assert match.get_winner_id() == match.home_id
    assert match.get_series_status() == "Vancouver Whitecaps FC advances to the Conference Final"
    assert match.get_series_status(include_current=False) is None


async def test_mls_cup_winner():
    match = await make_match("playoff_knockout")
    match.data.match_info.roundName = "match-round-cup"
    assert match.get_competition_display() == "MLS Cup"
    assert match.get_series_status() == "Vancouver Whitecaps FC wins MLS Cup!"
