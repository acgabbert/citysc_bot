import pytest

from reddit_client import subreddit_name


@pytest.mark.parametrize("sub", ["/r/stlouiscitysc", "stlouiscitysc"])
def test_subreddit_name(sub):
    assert subreddit_name(sub) == "stlouiscitysc"


async def test_get_image_data_uploads_widget_media():
    """asyncpraw 8 takes a WidgetMedia, not a path, in upload_image."""
    from unittest.mock import AsyncMock, MagicMock

    import asyncpraw.models

    from reddit_client import RedditClient

    widgets = MagicMock()
    widgets.mod.upload_image = AsyncMock(return_value="https://img/x.png")
    data = await RedditClient.get_image_data(None, widgets, "png/x.png", (300, 200))

    (media,), _ = widgets.mod.upload_image.call_args
    assert isinstance(media, asyncpraw.models.WidgetMedia)
    assert media.name == "x.png"
    assert data == [{"width": 300, "height": 200, "url": "https://img/x.png", "linkUrl": ""}]


def _widget_client(monkeypatch, short_names, upload_error=None):
    from unittest.mock import AsyncMock, MagicMock

    import reddit_client
    from reddit_client import RedditClient

    sent = []
    monkeypatch.setattr(reddit_client.msg, "send", lambda m, **kw: sent.append(m))

    sidebar = []
    for name in short_names:
        w = MagicMock(shortName=name)
        w.mod.update = AsyncMock()
        sidebar.append(w)

    async def iter_sidebar():
        for w in sidebar:
            yield w

    widgets = MagicMock()
    widgets.sidebar = iter_sidebar
    widgets.mod.upload_image = AsyncMock(return_value="https://img/x.png", side_effect=upload_error)

    client = RedditClient.__new__(RedditClient)
    client.get_widgets = AsyncMock(return_value=widgets)
    return client, sent


async def test_update_image_widget_error_sends_one_message(monkeypatch):
    client, sent = _widget_client(monkeypatch, ["Western Conference PNG"], AttributeError("boom"))
    assert await client.update_image_widget("Western Conference PNG", "png/x.png", (1, 1), "sub") is False
    assert len(sent) == 1
    assert sent[0].startswith("Error while updating Western Conference PNG widget.")


async def test_update_image_widget_missing_widget(monkeypatch):
    client, sent = _widget_client(monkeypatch, ["Other PNG"])
    assert await client.update_image_widget("Western Conference PNG", "png/x.png", (1, 1), "sub") is False
    assert len(sent) == 1
    assert sent[0].startswith("No widgets matching name")


async def test_update_image_widget_success(monkeypatch):
    client, sent = _widget_client(monkeypatch, ["Western Conference PNG"])
    assert await client.update_image_widget("Western Conference PNG", "png/x.png", (1, 1), "sub") is True
    assert sent == ["Updated Western Conference PNG widget on subreddit sub!"]
