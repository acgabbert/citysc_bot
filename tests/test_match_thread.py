import pytest

import config
import match_thread
from conftest import make_match


@pytest.mark.parametrize("minute, expected", [
    (None, 60),
    ("33", 60),
    ("79", 60),
    ("80", 30),
    ("90+4", 30),
    ("120+1", 30),
])
async def test_update_interval(monkeypatch, minute, expected):
    monkeypatch.setattr(config, "MATCH_UPDATE_INTERVAL", 60, raising=False)
    monkeypatch.setattr(config, "MATCH_UPDATE_INTERVAL_LATE", 30, raising=False)
    match = await make_match("live")
    match.minute_display = minute
    assert match_thread.update_interval(match) == expected


async def test_update_interval_defaults(monkeypatch):
    """A config.py from before these settings existed keeps the old 60s interval."""
    monkeypatch.delattr(config, "MATCH_UPDATE_INTERVAL", raising=False)
    monkeypatch.delattr(config, "MATCH_UPDATE_INTERVAL_LATE", raising=False)
    match = await make_match("final")
    assert match_thread.update_interval(match) == 60


async def test_skip_unneeded_series_game(monkeypatch):
    sent = []

    async def fake_send(message, **kwargs):
        sent.append(message)

    monkeypatch.setattr(match_thread.msg, "async_send", fake_send)
    match = await make_match("playoff_series")
    assert await match_thread._skip_unneeded_series_game(match) is False

    match.series_winners = [match.home_id, match.home_id]
    assert await match_thread._skip_unneeded_series_game(match) is True
    assert sent == [
        f"Skipping threads for {match.sportec_id}: the series was already decided "
        "(San Diego FC wins the series 2-0 and advances to the Conference Semifinals)"
    ]


class FakeReddit:
    edits = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def edit_thread(self, thread, text):
        self.edits.append((thread, text))


@pytest.fixture
def thread_files(monkeypatch, isolated_cwd):
    from thread_manager import ThreadManager

    manager = ThreadManager(str(isolated_cwd / "threads.json"))
    monkeypatch.setattr(match_thread, "file_manager", manager)
    return manager


def fixture_api(monkeypatch, state):
    from conftest import MATCH_STATES, FixtureClient

    monkeypatch.setattr(match_thread, "MLSApiClient", lambda: FixtureClient(MATCH_STATES[state]()))


async def test_attach_series_threads(thread_files):
    from thread_manager import MatchThreads

    await thread_files.add_threads("MLS-MAT-00098S", MatchThreads(slug="g1", match="m1", post="p1"))
    await thread_files.add_threads("MLS-MAT-00098W", MatchThreads(slug="g2", match="m2"))
    match = await make_match("playoff_series")
    match_thread._attach_series_threads(match)
    assert match.series_threads == {"MLS-MAT-00098S": "p1", "MLS-MAT-00098W": "m2"}


async def test_update_post_match_thread(monkeypatch, thread_files):
    from thread_manager import MatchThreads

    FakeReddit.edits = []
    monkeypatch.setattr(match_thread, "RedditClient", FakeReddit)
    fixture_api(monkeypatch, "final")
    await thread_files.add_threads("MLS-MAT-0009MQ", MatchThreads(slug="x", post="post1"))

    await match_thread.update_post_match_thread("MLS-MAT-0009MQ")
    [(thread_id, text)] = FakeReddit.edits
    assert thread_id == "post1"
    assert text.startswith("## FT: St. Louis CITY SC 6-2 LA Galaxy")
    assert "[Match highlights](https://www.mlssoccer.com/video/highlights-st-louis-city-sc-vs-la-galaxy" in text


async def test_update_post_match_thread_without_thread(monkeypatch, thread_files):
    FakeReddit.edits = []
    monkeypatch.setattr(match_thread, "RedditClient", FakeReddit)
    fixture_api(monkeypatch, "final")
    await match_thread.update_post_match_thread("MLS-MAT-0009MQ")
    assert FakeReddit.edits == []
