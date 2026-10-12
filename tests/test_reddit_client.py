import pytest

from reddit_client import subreddit_name


@pytest.mark.parametrize("sub", ["/r/stlouiscitysc", "stlouiscitysc"])
def test_subreddit_name(sub):
    assert subreddit_name(sub) == "stlouiscitysc"
