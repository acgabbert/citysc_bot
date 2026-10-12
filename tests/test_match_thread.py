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


# --- match thread loop -------------------------------------------------------

from types import SimpleNamespace  # noqa: E402

import match as match_module  # noqa: E402
from conftest import FINAL_ID, MATCH_STATES, FixtureClient  # noqa: E402
from thread_manager import MatchThreads, ThreadManager  # noqa: E402


class SequenceClient(FixtureClient):
    """Serves one match state per fetch, repeating the last one."""

    def __init__(self, states):
        super().__init__(MATCH_STATES[states[0]]())
        self.states = list(states)

    async def get_all_match_data(self, match_id):
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        self.payloads = MATCH_STATES[state]() if isinstance(state, str) else state
        return await super().get_all_match_data(match_id)


class FakeSubmission:
    def __init__(self, thread_id):
        self.id = thread_id
        self.shortlink = f"https://redd.it/{thread_id}"

    @staticmethod
    def id_from_url(url):
        return url.rsplit("/", 1)[-1]

    async def load(self):
        pass


class FakeReddit:
    def __init__(self):
        self.submitted = []   # titles
        self.edits = 0
        self.comments = []
        self.fail_submits = 0
        self.fail_comments = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def submit_thread(self, sub, title, text, **kwargs):
        if self.fail_submits:
            self.fail_submits -= 1
            raise RuntimeError("reddit is down")
        self.submitted.append(title)
        return FakeSubmission(f"t{len(self.submitted)}")

    async def edit_thread(self, thread, text):
        self.edits += 1

    async def add_comment(self, thread, text):
        if self.fail_comments:
            self.fail_comments -= 1
            raise RuntimeError("comment failed")
        self.comments.append(text)

    async def get_thread(self, thread_id):
        return FakeSubmission(thread_id)


@pytest.fixture
def bot(monkeypatch):
    """Wire match_thread to fake Reddit, Discord, clock and a temp threads.json.
    Set bot.states to the match states each API fetch returns, in order."""
    bot = SimpleNamespace(
        reddit=FakeReddit(), messages=[], sleeps=[], states=["final"],
        clock=1791759600.0,  # 2026-10-11T23:00Z, STL-LA kickoff
        file_manager=ThreadManager("threads.json"),
    )

    def client_factory(*args, **kwargs):
        return SequenceClient(bot.states)

    async def fake_send(message, tag=False, **kwargs):
        bot.messages.append(message)

    async def fake_sleep(seconds):
        bot.sleeps.append(seconds)
        bot.clock += seconds

    monkeypatch.setattr(match_thread, "MLSApiClient", client_factory)
    monkeypatch.setattr(match_module, "MLSApiClient", client_factory)
    monkeypatch.setattr(match_thread, "RedditClient", lambda: bot.reddit)
    monkeypatch.setattr(match_thread.msg, "async_send", fake_send)
    monkeypatch.setattr(match_thread, "asyncio", SimpleNamespace(sleep=fake_sleep))
    monkeypatch.setattr(match_thread, "time", SimpleNamespace(time=lambda: bot.clock))
    monkeypatch.setattr(match_thread, "file_manager", bot.file_manager)
    return bot


def abandoned():
    payloads = MATCH_STATES["live"]()
    payloads["match_base"]["match_information"]["match_status"] = "abandoned"
    return payloads


async def test_match_thread_posts_post_match_when_final(bot):
    bot.states = ["live", "live", "final"]
    await match_thread.match_thread(FINAL_ID, "test_sub")
    assert [t.split(":")[0] for t in bot.reddit.submitted] == ["Match Thread", "Post-Match Thread"]
    threads = bot.file_manager.get_threads(FINAL_ID)
    assert (threads.match, threads.post) == ("t1", "t2")
    assert bot.reddit.edits == 2


async def test_match_thread_stops_when_abandoned(bot):
    bot.states = ["live", "live", abandoned()]
    await match_thread.match_thread(FINAL_ID, "test_sub")
    assert len(bot.reddit.submitted) == 1
    assert bot.file_manager.get_threads(FINAL_ID).post is None
    assert any("is abandoned" in m for m in bot.messages)


async def test_match_thread_stops_at_time_cap(bot, monkeypatch):
    """A match stuck short of finalWhistle stops updating MATCH_THREAD_MAX_HOURS after kickoff."""
    monkeypatch.setattr(config, "MATCH_THREAD_MAX_HOURS", 1, raising=False)
    bot.states = ["live"]
    await match_thread.match_thread(FINAL_ID, "test_sub")
    assert len(bot.reddit.submitted) == 1
    assert bot.clock > 1791759600 + 3600
    assert bot.clock < 1791759600 + 3600 + 120
    assert any("--post" in m for m in bot.messages)


async def test_post_match_retries_after_failure(bot):
    bot.reddit.fail_submits = 1
    assert await match_thread.post_match_thread_with_retry(FINAL_ID, "test_sub") is True
    assert len(bot.reddit.submitted) == 1
    assert bot.sleeps == [match_thread.POST_MATCH_RETRY_DELAY]
    assert bot.file_manager.get_threads(FINAL_ID).post == "t1"


async def test_post_match_retry_never_double_posts(bot):
    """If the thread is submitted but a later step fails, the retry must not post another."""
    await bot.file_manager.add_threads(FINAL_ID, MatchThreads(slug="x", match="m1"))
    bot.reddit.fail_comments = 1
    assert await match_thread.post_match_thread_with_retry(FINAL_ID, "test_sub") is True
    assert len(bot.reddit.submitted) == 1


async def test_post_match_gives_up(bot):
    bot.reddit.fail_submits = 10
    assert await match_thread.post_match_thread_with_retry(FINAL_ID, "test_sub") is False
    assert len(bot.sleeps) == match_thread.POST_MATCH_ATTEMPTS - 1
    assert any("Giving up" in m for m in bot.messages)
