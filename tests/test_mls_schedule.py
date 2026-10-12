from datetime import datetime, timezone

import pytest

from conftest import load_schedule_json
from mls_schedule import check_pre_match_sched
from models.schedule import MatchSchedule


@pytest.fixture
def schedule():
    return [MatchSchedule(**m) for m in load_schedule_json()["schedule"]]


def ts(*args) -> int:
    return int(datetime(*args, tzinfo=timezone.utc).timestamp())


def test_finds_next_match_within_48h(schedule):
    # Day after STL-LA; next match is vs VAN, 2026-10-15 00:30 UTC (~2.5 days out)
    match_id, kickoff = check_pre_match_sched(schedule, date_from=ts(2026, 10, 13, 6, 0))
    assert match_id == "MLS-MAT-0009N5"
    assert kickoff == datetime(2026, 10, 15, 0, 30, tzinfo=timezone.utc)


def test_nothing_within_48h(schedule):
    assert check_pre_match_sched(schedule, date_from=ts(2026, 10, 12, 0, 0)) == (None, None)


def test_controller_lookback_finds_match_in_progress(schedule):
    """async_controller passes now - 3h so a match that already kicked off is still found."""
    now = ts(2026, 10, 12, 0, 0)  # STL-LA kicked off one hour earlier
    match_id, _ = check_pre_match_sched(schedule, date_from=now - 10800)
    assert match_id == "MLS-MAT-0009MQ"


def test_kickoff_exactly_at_date_from_is_excluded(schedule):
    # VAN kicks off exactly at date_from; the next match (MIN) is 68h later.
    assert check_pre_match_sched(schedule, date_from=ts(2026, 10, 15, 0, 30)) == (None, None)
    match_id, _ = check_pre_match_sched(schedule, date_from=ts(2026, 10, 15, 0, 29))
    assert match_id == "MLS-MAT-0009N5"


def test_empty_schedule():
    assert check_pre_match_sched([]) == (None, None)
