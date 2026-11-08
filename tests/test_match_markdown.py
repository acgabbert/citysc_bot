import pytest

import match_markdown as md
from conftest import make_match

GENERATORS = {
    "pre": md.pre_match_thread,
    "match": md.match_thread,
    "post": md.post_match_thread,
}


@pytest.mark.parametrize("thread_type", sorted(GENERATORS))
async def test_threads_render_in_every_state(state, thread_type):
    match = await make_match(state)
    title, body = GENERATORS[thread_type](match)
    assert match.home.fullName in title
    assert match.away.fullName in title
    assert "None" not in title
    assert body.startswith("## ")
    assert f"Match ID: {match.sportec_id}" in body


async def test_pre_match_thread():
    match = await make_match("pre_match")
    title, body = md.pre_match_thread(match)
    assert title == (
        "Matchday Thread: St. Louis CITY SC vs. Vancouver Whitecaps FC "
        "(Regular Season) [October 14, 2026]"
    )
    assert "## St. Louis CITY SC vs. Vancouver Whitecaps FC" in body
    assert "### Match Info" in body
    assert "- **Venue:** Energizer Park" in body
    assert "TV/Streaming: [Apple TV](https://tv.apple.com/" in body
    # No injuries/discipline files in the test directory
    assert "### Injury Report" not in body
    assert "### Discipline" not in body


async def test_pre_match_injuries_and_discipline(isolated_cwd):
    (isolated_cwd / "data").mkdir()
    (isolated_cwd / "data" / "injuries.json").write_text(
        '{"injuries": {"17012": ["Player A", "Player B"]}}'
    )
    (isolated_cwd / "data" / "discipline.json").write_text(
        '{"discipline": {"1708": {"Suspended": ["Player C"]}}}'
    )
    match = await make_match("pre_match")
    _, body = md.pre_match_thread(match)
    assert "### Injury Report" in body
    assert "**St. Louis CITY SC:** Player A, Player B" in body
    assert "### Discipline" in body
    assert "**Vancouver Whitecaps FC:** Suspended: Player C" in body


async def test_match_thread_before_lineups():
    match = await make_match("pre_match")
    _, body = md.match_thread(match)
    assert "## St. Louis CITY SC 0-0 Vancouver Whitecaps FC" in body
    assert body.count("Not yet available via mlssoccer.com.") == 2
    assert "⚽" not in body


async def test_match_thread_live():
    match = await make_match("live")
    _, body = md.match_thread(match)
    assert "## 33': St. Louis CITY SC 3-1 LA Galaxy" in body
    assert "⚽ **STL:** Carlo Holse (2', 7', 21')" in body
    assert "⚽ **LA:** Robert Taylor (31')" in body
    assert "### Lineups" in body


async def test_match_thread_halftime():
    match = await make_match("halftime")
    _, body = md.match_thread(match)
    assert "## HT: St. Louis CITY SC 3-1 LA Galaxy" in body
    assert "46'" not in body


async def test_post_match_thread_final():
    match = await make_match("final")
    title, body = md.post_match_thread(match)
    assert title.startswith("Post-Match Thread: St. Louis CITY SC vs. LA Galaxy")
    assert "## FT: St. Louis CITY SC 6-2 LA Galaxy" in body
    assert "Rafael Navarro (45' pen, 53')" in body
    assert "Chris Durkin (\U0001f504 Fallou Fall 72')" in body
    assert "*Subs:*" in body
    assert "### Match Stats:" in body
    assert "| STL | 6-2 | LA |" in body
    assert "| 58.47% | Ball Possession | 41.53% |" in body


async def test_post_match_thread_shootout():
    match = await make_match("shootout")
    _, body = md.post_match_thread(match)
    assert "## AET (Pens): St. Louis CITY SC 2-2 (4-2 pens) Houston Dynamo FC" in body
    assert "⚽ **STL:** Marcel Hartel (10', 51' pen)" in body
    # Cup matches get a stats table too
    assert "### Match Stats:" in body
    assert "| STL | 2-2 | HOU |" in body
    assert "| 54.17% | Ball Possession | 45.83% |" in body
    assert "?'" not in body


async def test_regular_season_has_no_round_line():
    match = await make_match("final")
    _, body = md.post_match_thread(match)
    assert body.split("\n")[1] == ""
    _, body = md.pre_match_thread(await make_match("pre_match"))
    assert "- **Competition:** Regular Season" in body
    assert "**Round:**" not in body


async def test_pre_match_thread_series():
    match = await make_match("playoff_series_scheduled")
    title, body = md.pre_match_thread(match)
    assert title == (
        "Matchday Thread: San Diego FC vs. Portland Timbers "
        "(MLS Cup Playoffs \u2013 Round One, Game 3 of 3) [November 09, 2025]"
    )
    assert "- **Competition:** MLS Cup Playoffs\n- **Round:** Round One, Game 3 of 3 (Series tied 1-1)" in body


async def test_match_thread_series_in_progress():
    match = await make_match("playoff_series_scheduled")
    title, body = md.match_thread(match)
    assert title.startswith("Match Thread: San Diego FC vs. Portland Timbers (MLS Cup Playoffs \u2013 Round One, Game 3 of 3)")
    assert body.startswith(
        "## San Diego FC 0-0 Portland Timbers\n"
        "**Round One, Game 3 of 3** | Series tied 1-1\n"
    )


async def test_post_match_thread_series_decided():
    match = await make_match("playoff_series")
    title, body = md.post_match_thread(match)
    assert title == (
        "Post-Match Thread: San Diego FC vs. Portland Timbers "
        "(MLS Cup Playoffs \u2013 Round One, Game 3 of 3) [November 09, 2025]"
    )
    assert body.startswith(
        "## FT: San Diego FC 4-0 Portland Timbers\n"
        "**Round One, Game 3 of 3** | San Diego FC wins the series 2-1 and advances to the Conference Semifinals\n"
    )
    assert "### Match Stats:" in body
    assert "| SD | 4-0 | POR |" in body


async def test_post_match_thread_knockout_shootout():
    match = await make_match("playoff_knockout")
    title, body = md.post_match_thread(match)
    assert "(MLS Cup Playoffs \u2013 Conference Semifinal)" in title
    assert body.startswith(
        "## AET (Pens): Vancouver Whitecaps FC 2-2 (4-3 pens) Los Angeles Football Club\n"
        "**Conference Semifinal** | Vancouver Whitecaps FC advances to the Conference Final\n"
    )
    # The pre-match thread never shows the result
    _, pre_body = md.pre_match_thread(match)
    assert "- **Round:** Conference Semifinal\n" in pre_body
    assert "advances" not in pre_body


async def test_2026_placeholders():
    title, body = md.pre_match_thread(await make_match("playoff_placeholder"))
    assert "(MLS Cup Playoffs \u2013 Round One, Game 1 of 3)" in title
    assert "- **Round:** Round One, Game 1 of 3\n" in body
    title, body = md.match_thread(await make_match("playoff_mls_cup_placeholder"))
    assert title.startswith("Match Thread: TBC Home vs. TBC Away (MLS Cup) [")
    assert "\n**MLS Cup**\n" in body


async def test_post_match_thread_without_stats():
    match = await make_match("missing_stats")
    _, body = md.post_match_thread(match)
    assert "### Match Stats:" not in body
    assert "### Lineups" in body
