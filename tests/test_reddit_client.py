from types import SimpleNamespace

import asyncprawcore.exceptions
import pytest

import reddit_client
from reddit_client import RedditClient, RedditClientError, RedditServerError, subreddit_name


@pytest.mark.parametrize("sub", ["/r/stlouiscitysc", "stlouiscitysc"])
def test_subreddit_name(sub):
    assert subreddit_name(sub) == "stlouiscitysc"


@pytest.fixture
def no_sleep(monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    monkeypatch.setattr(reddit_client.asyncio, "sleep", fake_sleep)
    return sleeps


def flaky(errors):
    """An operation that raises each of errors in turn, then returns 'ok'."""
    calls = []

    async def operation():
        calls.append(1)
        if len(calls) <= len(errors):
            raise errors[len(calls) - 1]
        return "ok"

    operation.calls = calls
    return operation


def server_error():
    return asyncprawcore.exceptions.ServerError(SimpleNamespace(status=503))


def rate_limited():
    return asyncprawcore.exceptions.TooManyRequests(SimpleNamespace(status=429, headers={}, text=""))


def network_error():
    return asyncprawcore.exceptions.RequestException(OSError("connection reset"), (), {})


@pytest.mark.parametrize("make_error", [server_error, rate_limited, network_error])
async def test_retries_transient_errors(no_sleep, make_error):
    operation = flaky([make_error(), make_error()])
    assert await RedditClient()._execute_with_retry(operation) == "ok"
    assert len(operation.calls) == 3
    assert no_sleep == [5, 10]


async def test_gives_up_after_max_retries(no_sleep):
    operation = flaky([network_error()] * 3)
    with pytest.raises(RedditServerError):
        await RedditClient()._execute_with_retry(operation)
    assert len(operation.calls) == 3


async def test_does_not_retry_client_errors(no_sleep):
    operation = flaky([ValueError("bad request")])
    with pytest.raises(RedditClientError):
        await RedditClient()._execute_with_retry(operation)
    assert len(operation.calls) == 1
    assert no_sleep == []


async def test_does_not_retry_network_errors_when_not_idempotent(no_sleep):
    """A submit that timed out may have gone through; retrying could post twice."""
    operation = flaky([network_error()])
    with pytest.raises(RedditClientError):
        await RedditClient()._execute_with_retry(operation, idempotent=False)
    assert len(operation.calls) == 1


async def test_retries_server_errors_when_not_idempotent(no_sleep):
    operation = flaky([server_error()])
    assert await RedditClient()._execute_with_retry(operation, idempotent=False) == "ok"
