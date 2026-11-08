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
