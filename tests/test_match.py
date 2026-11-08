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
    match.get_seeds()
    match.get_attendance()
    match.get_cards()
    match.get_shootout()
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


async def test_series_games():
    match = await make_match("playoff_series")
    games = match.series_games
    assert [(g.game, g.match_id, g.home_goals, g.away_goals, g.home_pens, g.away_pens, g.winner_id)
            for g in games] == [
        (1, "MLS-MAT-00098S", 2, 1, None, None, SD),
        (2, "MLS-MAT-00098W", 2, 2, 3, 2, POR),
    ]
    assert games[1].home_id == POR
    # Unknown before the stats API has the match, and outside a series
    assert (await make_match("playoff_placeholder")).series_games is None
    assert (await make_match("final")).series_games is None


async def test_seeds():
    assert (await make_match("playoff_series")).get_seeds() == {SD: 1, POR: 8}
    # Placeholders have blank ranks; regular season matches never get seeds
    assert (await make_match("playoff_placeholder")).get_seeds() is None
    assert (await make_match("final")).get_seeds() is None


async def test_kickoff_time_tbd():
    match = await make_match("playoff_placeholder")
    assert match.is_time_tbd()
    assert match.get_local_time_string() == "TBD"
    match = await make_match("pre_match")
    assert not match.is_time_tbd()
    assert match.get_local_time_string() == "07:30 PM CDT"


async def test_attendance():
    assert (await make_match("final")).get_attendance() == 22423
    # The API reports 0 when it doesn't have a number
    assert (await make_match("shootout")).get_attendance() is None
    assert (await make_match("missing_base")).get_attendance() is None


async def test_shootout_kicks():
    match = await make_match("shootout")
    shootout = match.get_shootout()
    assert [(k.taker, k.scored, k.saved) for k in shootout[match.away_id]] == [
        ("Guilherme Santos", False, True),
        ("Ondřej Lingr", True, False),
        ("Duane Holmes", True, False),
        ("Héctor Herrera", False, True),
    ]
    assert sum(k.scored for k in shootout[match.home_id]) == 4
    # Extra time, but no shootout
    assert (await make_match("final")).get_shootout() is None


async def test_cards():
    match = await make_match("shootout")
    cards = match.get_cards()
    ennali = next(p.person_id for p in match.data.match_base.away.players if p.last_name == "Ennali")
    assert cards[ennali] == ["\U0001f7e829'", "\U0001f7e8\U0001f7e5109'"]
    # Coach cards aren't player cards
    assert sum(len(c) for c in cards.values()) == 8
    assert (await make_match("empty_events")).get_cards() == {}


async def test_load_highlights():
    payloads = MATCH_STATES["final"]()
    match = await Match.create(FINAL_ID, client=FixtureClient(payloads))
    url = await match.load_highlights(FixtureClient(payloads))
    # The full highlights, not a goal clip or the match snapshot
    assert url == match.highlights_url == (
        "https://www.mlssoccer.com/video/highlights-st-louis-city-sc-vs-la-galaxy-october-11-2026"
    )


async def test_load_highlights_not_out_yet():
    match = await make_match("shootout")  # no videos.json
    assert await match.load_highlights(FixtureClient(MATCH_STATES["shootout"]())) is None
    # Only goal clips so far
    payloads = MATCH_STATES["final"]()
    payloads["videos"]["items"] = [i for i in payloads["videos"]["items"] if i["slug"].startswith("goal-")]
    assert await match.load_highlights(FixtureClient(payloads)) is None


async def test_load_highlights_api_error():
    class FailingClient(FixtureClient):
        async def get_videos(self, match_id):
            raise RuntimeError("boom")

    match = await make_match("final")
    assert await match.load_highlights(FailingClient({})) is None


def _with_next_matches(payloads):
    from conftest import load_sd_schedule

    payloads["schedule"] = load_sd_schedule()
    payloads["other_match_infos"] = {
        mid: load_fixture(mid, "match_info") for mid in ("MLS-MAT-00098W", "MLS-MAT-00099J")
    }
    return payloads


def _series_game_payloads(game: int, home_goals: int, away_goals: int):
    """Game 1 or 2 of the SD-POR series, finished, with Game 3's sport API data borrowed."""
    match_id = SERIES_EARLIER_IDS[game - 1]
    payloads = _with_next_matches(_series_payloads(match_id, SERIES_EARLIER_IDS[:game - 1]))
    info = load_fixture(SERIES_GAME_3_ID, "match_info")
    kickoff = {1: "2025-10-27T01:30:00Z", 2: "2025-11-02T01:30:00Z"}[game]
    info.update(sportecId=match_id, roundNumber=game + 1, roundGroup=f"game_{game}", matchDate=kickoff)
    if game == 2:
        info.update(home=info["away"], away=info["home"])
    payloads["match_info"] = info
    payloads["match_base"]["match_information"].update(
        match_status="finalWhistle", home_team_goals=home_goals, away_team_goals=away_goals,
        home_team_penalty_goals=None, away_team_penalty_goals=None,
    )
    return payloads


async def test_next_match_is_next_series_game():
    payloads = _series_game_payloads(1, 2, 1)
    match = await Match.create(SERIES_EARLIER_IDS[0], client=FixtureClient(payloads))
    next_match = await match.load_next_match(FixtureClient(payloads))
    assert next_match.sportec_id == "MLS-MAT-00098W"
    assert str(next_match.get_playoff_round()) == "Round One, Game 2 of 3"
    assert match.next_match_tbd is None


async def test_next_match_skips_unneeded_game_3():
    # SD (away) wins Game 2 to go up 2-0; Game 3 is still on the schedule
    payloads = _series_game_payloads(2, 0, 1)
    match = await Match.create(SERIES_EARLIER_IDS[1], client=FixtureClient(payloads))
    assert match.get_series_status() == (
        "San Diego FC wins the series 2-0 and advances to the Conference Semifinals"
    )
    next_match = await match.load_next_match(FixtureClient(payloads))
    assert next_match.sportec_id == "MLS-MAT-00099J"


async def test_next_match_after_series():
    payloads = _with_next_matches(MATCH_STATES["playoff_series"]())
    match = await Match.create(SERIES_GAME_3_ID, client=FixtureClient(payloads))
    next_match = await match.load_next_match(FixtureClient(payloads))
    assert next_match.sportec_id == "MLS-MAT-00099J"
    assert next_match.get_competition_display() == "MLS Cup Playoffs – Conference Semifinal"


async def test_no_next_match():
    # Nothing on the schedule (e.g. after elimination), or the lookup fails
    match = await make_match("final")
    assert await match.load_next_match(FixtureClient(MATCH_STATES["final"]())) is None

    class FailingClient(FixtureClient):
        async def get_schedule(self, season, **kwargs):
            raise RuntimeError("boom")

    assert await match.load_next_match(FailingClient({})) is None


async def test_next_match_schedule_query():
    """The schedule API returns 400 for match_date[gte] without match_date[lte]."""
    calls = []

    class RecordingClient(FixtureClient):
        async def get_schedule(self, season, **kwargs):
            calls.append((season, kwargs))
            return []

    match = await make_match("playoff_series")
    await match.load_next_match(RecordingClient({}))
    season, kwargs = calls[0]
    assert season == "MLS-SEA-0001K9"
    assert kwargs["match_date_gte"] == "2025-11-10"
    assert kwargs["match_date_lte"] == "2026-01-09"
