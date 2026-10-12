import copy

import pytest

from conftest import FINAL_ID, PRE_MATCH_ID, SHOOTOUT_ID, load_fixture, load_schedule_json
from models.event import CoachCardEvent, MatchEventResponse
from models.match import Match_Base, Match_Sport
from models.match_stats import MatchStats
from models.schedule import MatchSchedule

MATCH_IDS = [FINAL_ID, SHOOTOUT_ID]


@pytest.mark.parametrize("match_id", [FINAL_ID, SHOOTOUT_ID, PRE_MATCH_ID])
def test_match_info_parses(match_id):
    info = Match_Sport(**load_fixture(match_id, "match_info"))
    assert info.sportecId == match_id
    assert info.home.fullName == "St. Louis CITY SC"


@pytest.mark.parametrize("match_id", MATCH_IDS)
def test_match_base_parses(match_id):
    base = Match_Base(**load_fixture(match_id, "match_base"))
    assert base.match_information.match_status == "finalWhistle"
    assert any(p.starting for p in base.home.players)


@pytest.mark.parametrize("match_id", MATCH_IDS)
def test_match_stats_parses(match_id):
    raw = load_fixture(match_id, "match_stats")
    stats = MatchStats(**raw["match_statistics_list"][0]["match_statistics"])
    assert len(stats.team_statistics) == 2


@pytest.mark.parametrize("match_id", MATCH_IDS)
def test_match_events_parse_without_dropping_any(match_id):
    raw = load_fixture(match_id, "match_events")
    events = MatchEventResponse(**raw).events
    assert len(events) == len(raw["events"])


def test_coach_card_event():
    """card_coaches events used to fail validation for the whole events response."""
    events = MatchEventResponse(**load_fixture(SHOOTOUT_ID, "match_events")).events
    coach_cards = [e for e in events if isinstance(e, CoachCardEvent)]
    assert len(coach_cards) == 2
    assert str(coach_cards[0]) == "90+4': Yoann Damet (coach) receives a yellow card."


def test_unknown_event_type_is_skipped():
    raw = copy.deepcopy(load_fixture(FINAL_ID, "match_events"))
    count = len(raw["events"])
    raw["events"].insert(0, {"type": "some_new_type", "sub_type": "", "event": {"event_id": 1}})
    events = MatchEventResponse(**raw).events
    assert len(events) == count


def test_event_during_extra_time_break_gets_minute():
    events = MatchEventResponse(**load_fixture(SHOOTOUT_ID, "match_events")).events
    break_events = [e for e in events if e.event.game_section == "halfExtra"]
    assert break_events
    assert all(e.event.minute_of_play == "106" for e in break_events)


def test_schedule_parses():
    raw = load_schedule_json()
    schedule = [MatchSchedule(**m) for m in raw["schedule"]]
    assert len(schedule) == len(raw["schedule"])
    assert all(m.planned_kickoff_time.tzinfo is not None for m in schedule)
