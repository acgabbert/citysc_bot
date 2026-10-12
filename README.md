# citysc_bot

Reddit match-thread bot for [r/stlouiscitysc](https://www.reddit.com/r/stlouiscitysc). It watches St. Louis CITY SC's schedule and, for each match:

- posts a pre-match thread the morning of the match,
- posts a match thread 30 minutes before kickoff and keeps it updated with the score, scorers, lineups and stats,
- posts a post-match thread after the final whistle.

It also updates the subreddit's sidebar image widgets, scrapes MLS injury and discipline reports for the pre-match thread, and sends status messages to a Discord webhook. CITY 2 (MLS NEXT Pro) matches get a match thread only.

## Setup

Requires Python 3.13 (the version the Docker image uses).

```bash
pip install -r requirements.txt
playwright install chromium   # browser for the sidebar widget screenshots
cp config-example.py config.py
mkdir -p data log png
```

Then fill in `config.py`.

## Configuration

`config.py` is a Python module; `config-example.py` lists every setting. The main ones:

| Setting | What it does |
|---|---|
| `CLIENT_ID`, `SECRET_TOKEN`, `USERNAME`, `PASSWORD`, `USER_AGENT_STR` | Reddit script-app credentials. The account must be a moderator to sticky threads. |
| `SUB`, `TEST_SUB` | Subreddit to post to, and a test subreddit for manual runs. |
| `TEAMS` | Opta IDs of the teams to follow. |
| `FEATURE_FLAGS` | Turns scheduled jobs on or off: `enable_widgets`, `enable_injuries`, `enable_discipline`, `enable_daily_setup`, plus `enable_inline_logos` for club logos in thread headers. |
| `MLS_BOT_WEBHOOK`, `DISCORD_BOTADMINID` | Discord webhook for status messages, and the role to tag on errors. |
| `THREADS_JSON`, `THREADS_MAX_AGE_DAYS` | Where thread IDs are stored, and how long entries are kept (default 30 days). |
| `MATCH_UPDATE_INTERVAL`, `MATCH_UPDATE_INTERVAL_LATE` | Seconds between match thread updates, and from the 80th minute on (defaults 60 and 30). |

Settings added after your `config.py` was written fall back to their defaults.

## Running

```bash
# Run the scheduler (runs until stopped)
python async_controller.py
python async_controller.py -s /r/some_subreddit   # post somewhere else

# One-off threads, e.g. for testing
python match_thread.py -i SPORTEC_ID              # match thread, then post-match
python match_thread.py -i SPORTEC_ID --pre        # pre-match only
python match_thread.py -i SPORTEC_ID --post       # post-match only
python match_thread.py -i SPORTEC_ID --no-post    # match thread without post-match
python match_thread.py -i SPORTEC_ID -s /r/test_sub
```

Sportec IDs look like `MLS-MAT-0009MQ`.

Daily jobs (server local time): widget screenshots 00:45, widget upload 01:00, injuries and discipline 01:15, `threads.json` cleanup 01:25, schedule check 01:30. The schedule check queues the day's pre-match and match threads.

### Docker

Set `BOT_BASE_PATH` in `.env` to a directory holding `config.py` and the `assets`, `markdown`, `log`, `png` and `data` directories (default `/opt/citysc_bot`), then:

```bash
docker compose build
docker compose up -d
docker compose logs -f
```

The container reports `unhealthy` in `docker ps` if the scheduler's event loop stops running for more than five minutes.

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

Tests don't touch the network or Reddit: they run against MLS API responses saved in `tests/fixtures/`. CI runs both commands on every pull request.

## Layout

| File | Purpose |
|---|---|
| `async_controller.py` | Entry point: schedules the daily jobs and the match threads. |
| `match_thread.py` | Posts the pre-match, match and post-match threads and runs the live update loop. |
| `match_markdown.py` | Builds each thread's title and body. |
| `match.py`, `api_client.py`, `models/` | MLS API client, the `Match` wrapper and typed response models. |
| `reddit_client.py` | Reddit client with retries. |
| `thread_manager.py` | Saves the Reddit thread IDs for each match in `data/threads.json`. |
| `injuries.py`, `discipline.py` | Scrape the MLS injury and discipline reports. |
| `widgets.py`, `mls_playwright.py` | Screenshot standings and schedule pages and upload them as sidebar widgets. |

`CLAUDE.md` has more on the architecture; `docs/RECOMMENDATIONS.md` tracks planned improvements.
