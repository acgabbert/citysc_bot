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
