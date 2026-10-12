"""Daily setup's scheduling decisions (mls_schedule.plan_match_jobs) and the controller around them."""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

import async_controller
import match_thread
from async_controller import AsyncController, schedule_time
from conftest import load_schedule_json
from mls_schedule import PlannedJob, plan_match_jobs
from models.schedule import MatchSchedule
from thread_manager import MatchThreads, ThreadManager

CENTRAL = ZoneInfo("America/Chicago")
LA_MATCH = "MLS-MAT-0009MQ"   # final; kicked off 2026-10-11 18:00 CDT
VAN_MATCH = "MLS-MAT-0009N5"  # scheduled; kicks off 2026-10-14 19:30 CDT


def central(*args) -> datetime:
    return datetime(*args, tzinfo=CENTRAL)


@pytest.fixture
def schedule():
    return [MatchSchedule(**m) for m in load_schedule_json()["schedule"]]


def threads_lookup(**by_id: MatchThreads):
    return by_id.get


def plan(schedule, now, threads=None, **kwargs):
    return plan_match_jobs(schedule, now, threads or threads_lookup(), **kwargs)


def summary(jobs):
    return [(j.kind, j.match_id, j.run_date.astimezone(CENTRAL).strftime("%m-%d %H:%M"), j.post) for j in jobs]


def late_kickoff(schedule, kickoff: datetime, status: str):
    """The LA match moved to a different kickoff and status."""
    match = next(m for m in schedule if m.match_id == LA_MATCH)
    return [match.model_copy(update={"planned_kickoff_time": kickoff.astimezone(timezone.utc), "match_status": status})]


# --- matchday ----------------------------------------------------------------

def test_matchday_daily_setup(schedule):
    """At the usual 01:30 run: match thread 30 min before kickoff, pre-match thread at 04:00."""
    jobs = plan(schedule, central(2026, 10, 14, 1, 30))
    assert summary(jobs) == [
        ("match", VAN_MATCH, "10-14 19:00", True),
        ("pre_match", VAN_MATCH, "10-14 04:00", True),
    ]


def test_restart_before_pre_match_catchup_ends(schedule):
    now = central(2026, 10, 14, 6, 0)
    assert summary(plan(schedule, now)) == [
        ("match", VAN_MATCH, "10-14 19:00", True),
        ("pre_match", VAN_MATCH, "10-14 06:00", True),
    ]
    posted = threads_lookup(**{VAN_MATCH: MatchThreads(slug="x", pre="p1")})
    assert summary(plan(schedule, now, posted)) == [("match", VAN_MATCH, "10-14 19:00", True)]


def test_restart_after_pre_match_catchup_ends(schedule):
    assert summary(plan(schedule, central(2026, 10, 14, 9, 0))) == [("match", VAN_MATCH, "10-14 19:00", True)]


def test_restart_after_match_thread_time(schedule):
    now = central(2026, 10, 14, 19, 15)
    jobs = plan(schedule, now)
    assert summary(jobs) == [("match", VAN_MATCH, "10-14 19:15", True)]
    assert jobs[0].run_date == now


def test_match_threads_only_team(schedule):
    """CITY 2 gets a match thread with no pre- or post-match thread."""
    jobs = plan(schedule, central(2026, 10, 14, 1, 30), match_threads_only=True)
    assert summary(jobs) == [("match", VAN_MATCH, "10-14 19:00", False)]


def test_match_tomorrow_is_not_scheduled(schedule):
    assert plan(schedule, central(2026, 10, 13, 1, 30)) == []


def test_no_matches(schedule):
    assert plan([], central(2026, 10, 14, 1, 30)) == []
    assert plan(schedule, central(2026, 10, 20, 1, 30)) == []


# --- resuming a match after midnight ------------------------------------------

def test_resume_match_in_progress_after_midnight(schedule):
    sched = late_kickoff(schedule, central(2026, 10, 11, 22, 30), "secondHalf")
    now = central(2026, 10, 12, 0, 30)
    posted = threads_lookup(**{LA_MATCH: MatchThreads(slug="x", match="m1")})
    assert summary(plan(sched, now, posted)) == [("match", LA_MATCH, "10-12 00:30", True)]
    # No match thread posted, or post-match thread already up: nothing to resume
    assert plan(sched, now) == []
    done = threads_lookup(**{LA_MATCH: MatchThreads(slug="x", match="m1", post="p1")})
    assert plan(sched, now, done) == []


def test_resume_keeps_match_threads_only(schedule):
    """Resuming a CITY 2 match must not post a post-match thread."""
    sched = late_kickoff(schedule, central(2026, 10, 11, 22, 30), "secondHalf")
    posted = threads_lookup(**{LA_MATCH: MatchThreads(slug="x", match="m1")})
    jobs = plan(sched, central(2026, 10, 12, 0, 30), posted, match_threads_only=True)
    assert summary(jobs) == [("match", LA_MATCH, "10-12 00:30", False)]


# --- post-match catch-up ------------------------------------------------------

def test_missing_post_match_thread_is_caught_up(schedule):
    now = central(2026, 10, 12, 1, 30)
    posted = threads_lookup(**{LA_MATCH: MatchThreads(slug="x", match="m1")})
    assert summary(plan(schedule, now, posted)) == [("post_match", LA_MATCH, "10-12 01:30", True)]


@pytest.mark.parametrize("threads, now, match_threads_only", [
    (MatchThreads(slug="x", match="m1", post="p1"), central(2026, 10, 12, 1, 30), False),  # already posted
    (None, central(2026, 10, 12, 1, 30), False),                                       # no match thread
    (MatchThreads(slug="x", match="m1"), central(2026, 10, 12, 1, 30), True),          # CITY 2
    (MatchThreads(slug="x", match="m1"), central(2026, 10, 12, 18, 30), False),        # > 24h ago
])
def test_no_post_match_catch_up(schedule, threads, now, match_threads_only):
    lookup = threads_lookup(**{LA_MATCH: threads}) if threads else threads_lookup()
    assert plan(schedule, now, lookup, match_threads_only=match_threads_only) == []


def test_post_match_catch_up_waits_for_final_whistle(schedule):
    sched = late_kickoff(schedule, central(2026, 10, 11, 18, 0), "secondHalf")
    posted = threads_lookup(**{LA_MATCH: MatchThreads(slug="x", match="m1")})
    assert plan(sched, central(2026, 10, 12, 1, 30), posted) == []


def test_resumed_match_is_not_also_caught_up(schedule):
    """A final match that gets a resume job posts its post-match thread from the loop, not twice."""
    sched = late_kickoff(schedule, central(2026, 10, 11, 22, 30), "finalWhistle")
    posted = threads_lookup(**{LA_MATCH: MatchThreads(slug="x", match="m1")})
    assert [j.kind for j in plan(sched, central(2026, 10, 12, 0, 30), posted)] == ["match"]


# --- controller ---------------------------------------------------------------

@pytest.fixture
def controller(monkeypatch):
    sent = []

    async def fake_async_send(message, tag=False, **kwargs):
        sent.append(message)

    monkeypatch.setattr(async_controller.msg, "send", lambda message, tag=False, **kw: sent.append(message))
    monkeypatch.setattr(async_controller.msg, "async_send", fake_async_send)
    monkeypatch.setattr(match_thread, "file_manager", ThreadManager("threads.json"))
    controller = AsyncController("/r/test_sub")
    controller.sent = sent
    return controller


async def test_one_off_job_error_is_reported(controller):
    """One-off jobs are gone from the scheduler when the error listener runs."""
    reported = asyncio.Event()
    controller.scheduler.add_listener(lambda e: reported.set(), async_controller.EVENT_JOB_ERROR)

    async def boom():
        raise RuntimeError("reddit is down")

    controller.scheduler.start()
    controller._add_job(boom, "date", "pre_match_thread_X", run_date=datetime.now())
    try:
        await asyncio.wait_for(reported.wait(), 5)
    finally:
        controller.scheduler.shutdown(wait=False)
    assert "Error in job pre_match_thread_X: reddit is down" in controller.sent


async def test_match_thread_runs_once_per_match(controller, monkeypatch):
    calls = []
    release = asyncio.Event()

    async def fake_match_thread(sportec_id, sub, post=True):
        calls.append(sportec_id)
        await release.wait()

    monkeypatch.setattr(match_thread, "match_thread", fake_match_thread)
    first = asyncio.create_task(controller.create_match_thread("M1"))
    await asyncio.sleep(0)
    await controller.create_match_thread("M1")
    assert any("already running" in m for m in controller.sent)
    release.set()
    await first
    assert calls == ["M1"]
    assert controller.active_matches == set()


async def test_post_match_catch_up_defers_to_running_loop(controller, monkeypatch):
    calls = []

    async def fake_post(sportec_id, sub):
        calls.append(sportec_id)

    monkeypatch.setattr(match_thread, "post_match_thread_with_retry", fake_post)
    controller.active_matches.add("M1")
    await controller.create_post_match_thread("M1")
    await controller.create_post_match_thread("M2")
    assert calls == ["M2"]


async def test_pre_match_thread_not_posted_twice(controller, monkeypatch):
    calls = []

    async def fake_pre(sportec_id, sub):
        calls.append(sportec_id)

    monkeypatch.setattr(match_thread, "pre_match_thread", fake_pre)
    await match_thread.file_manager.add_threads("M1", MatchThreads(slug="x", pre="p1"))
    await controller.create_pre_match_thread("M1")
    await controller.create_pre_match_thread("M2")
    assert calls == ["M2"]


def test_planned_jobs_are_scheduled_by_id(controller):
    run = datetime.now() + timedelta(hours=1)
    controller.schedule_planned_job(PlannedJob("match", "M1", run, "match thread", post=False))
    controller.schedule_planned_job(PlannedJob("pre_match", "M1", run, "pre-match thread"))
    controller.schedule_planned_job(PlannedJob("post_match", "M0", run, "missing post-match thread"))
    # Scheduling the same job again replaces it rather than adding a duplicate
    controller.schedule_planned_job(PlannedJob("match", "M1", run, "match thread", post=False))
    jobs = {job.id: job for job in controller.scheduler.get_jobs()}
    assert sorted(jobs) == ["match_thread_M1", "post_match_thread_M0", "pre_match_thread_M1"]
    assert jobs["match_thread_M1"].args == ("M1", False)


def test_schedule_times(monkeypatch):
    flags = async_controller.FEATURE_FLAGS
    monkeypatch.setitem(flags, "schedule_times", {"daily_setup": "02:05", "selenium": "00:10"})
    assert schedule_time("daily_setup") == (2, 5)
    assert schedule_time("playwright") == (0, 10)   # old key name still works
    assert schedule_time("prune_threads") == (1, 25)  # falls back to the default
    monkeypatch.delitem(flags, "schedule_times")
    assert schedule_time("daily_setup") == (1, 30)


@pytest.mark.parametrize("hour, minute, catch_up", [(1, 29, False), (1, 30, True), (23, 0, True)])
def test_daily_setup_catch_up_on_start(controller, hour, minute, catch_up):
    controller.setup_jobs(now=datetime(2026, 10, 14, hour, minute))
    ids = {job.id for job in controller.scheduler.get_jobs()}
    assert {"daily_setup", "prune_threads", "injuries", "discipline", "widgets", "playwright"} <= ids
    assert ("daily_setup_catchup" in ids) == catch_up
