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
