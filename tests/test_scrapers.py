import json

import pytest
from bs4 import BeautifulSoup

import discipline
import injuries

INJURY_PAGE = """
<div class="d3-l-col__col-12"><div class="mls-c-ranking-header__title">St. Louis City SC</div></div>
<ul><li>Player A - Out (knee)</li></ul>
"""
OLD_DATA = {"injuries": {"17012": ["Old Player"]}}


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(injuries.msg, "send", lambda message, tag=False, **kw: sent.append(message))
    return sent


@pytest.fixture
def data_dir(isolated_cwd):
    (isolated_cwd / "data").mkdir()
    return isolated_cwd / "data"


def page(monkeypatch, module, getter, html):
    monkeypatch.setattr(module, getter, lambda: BeautifulSoup(html, "html.parser"))


def test_injuries_written(monkeypatch, data_dir, alerts):
    page(monkeypatch, injuries, "get_injury_content", INJURY_PAGE)
    assert injuries.main() is True
    data = json.loads((data_dir / "injuries.json").read_text())
    assert data["injuries"] == {"17012": ["Player A - Out (knee)"]}


@pytest.mark.parametrize("html", ["<html></html>", "<div class='d3-l-col__col-12'>changed</div><p></p>"])
def test_injuries_keep_previous_data_when_page_changes(monkeypatch, data_dir, alerts, html):
    (data_dir / "injuries.json").write_text(json.dumps(OLD_DATA))
    page(monkeypatch, injuries, "get_injury_content", html)
    assert injuries.main() is False
    assert json.loads((data_dir / "injuries.json").read_text()) == OLD_DATA
    assert alerts


def test_discipline_keeps_previous_data_when_page_changes(monkeypatch, data_dir, alerts):
    old = {"updated": "x", "discipline": {"17012": {"Suspended": ["Old Player"]}}}
    (data_dir / "discipline.json").write_text(json.dumps(old))
    page(monkeypatch, discipline, "get_discipline_content", "<html></html>")
    assert discipline.main() is False
    assert json.loads((data_dir / "discipline.json").read_text()) == old
    assert alerts
