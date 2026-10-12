# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Reddit match-thread automation bot for St. Louis City SC (r/stlouiscitysc). It fetches live match data from the MLS API, manages pre/match/post-match Reddit threads, updates sidebar widgets, scrapes injury/discipline reports, and sends Discord webhook notifications.

## Running

```bash
# Main entry point — starts APScheduler, runs indefinitely
python async_controller.py
python async_controller.py -s /r/some_subreddit  # override subreddit

# Manual match thread (for testing or one-off runs)
python match_thread.py -i SPORTEC_ID            # full lifecycle
python match_thread.py -i SPORTEC_ID --pre      # pre-match only
python match_thread.py -i SPORTEC_ID --post     # post-match only
python match_thread.py -i SPORTEC_ID --no-post  # match thread, skip post-match
python match_thread.py -i SPORTEC_ID -s /r/test_sub
```

```bash
# Docker
docker compose build
docker compose up -d
docker compose logs -f
```

## Configuration

Copy `config-example.py` to `config.py` and fill in secrets (Reddit OAuth, Discord webhook URLs). Read settings added after the initial config with `getattr(config, NAME, default)` so older `config.py` files keep working. The `FEATURE_FLAGS` dict controls which scheduled jobs are enabled. `BOT_BASE_PATH` in `.env` sets the base path for Docker volume mounts.

## Architecture

**Scheduling layer** (`async_controller.py`): `AsyncController` runs an `AsyncIOScheduler` with cron-triggered jobs for daily setup, `threads.json` pruning, injuries, discipline, widgets, and Playwright screenshots. Its main loop touches a heartbeat file each minute for the Docker `HEALTHCHECK`. MLS NEXT Pro teams are routed through a separate API (`get_nextpro_schedule()`). Job execution/error callbacks send Discord notifications via sync `msg.send()`.

**Match thread lifecycle** (`match_thread.py`): Three phases — `pre_match_thread()` (24h before), `match_thread()` (30min before kickoff, polling loop during match at `MATCH_UPDATE_INTERVAL`/`MATCH_UPDATE_INTERVAL_LATE`), `post_match_thread()` (after final whistle). Each phase creates/edits Reddit threads and updates `ThreadManager` state.

**Match markdown** (`match_markdown.py`): Generates all Reddit thread markdown — headers, scorers, lineups, stats, injuries, discipline, and footers. `pre_match_thread()`, `match_thread()`, and `post_match_thread()` each return `(title, body)` tuples.

**API data** (`api_client.py` + `match.py`): `MLSApiClient` is an async context manager for MLS API calls. `Match` wraps it with match-specific logic (including reading injury/discipline data from JSON files). Both support session reuse via an optional `client` parameter to avoid creating multiple aiohttp sessions.

**State persistence** (`thread_manager.py`): `ThreadManager` reads/writes `data/threads.json` with atomic writes (tempfile + `os.replace`) and `asyncio.Lock` for concurrency safety. There is one instance, `match_thread.file_manager`, which `async_controller.py` shares; `prune()` drops entries older than `THREADS_MAX_AGE_DAYS`.

**Web scraping** (`injuries.py`, `discipline.py`): Sync functions that scrape the MLS website with BeautifulSoup. Run as APScheduler thread pool jobs (not on the async event loop). Have 30s timeouts and 3x retry.

**Widgets** (`widgets.py`): Image-only sidebar widget updates via Reddit API. Only `update_image_widget()` remains; it goes through `RedditClient`.

**Schedule helper** (`mls_schedule.py`): Single function `check_pre_match_sched()` used by `async_controller.py` to find upcoming matches within 48h.

**Pydantic models** (`models/`): Typed models for API responses — `ComprehensiveMatchData`, `MlsEvent`, `MatchSchedule`, `TeamStats`, `Club_Sport`, etc. `models/constants.py` has season/competition enums and `get_current_season()`.

## Key Async/Sync Boundary

This is the most important pattern to understand:

- **Async context**: `match_thread.py`, `api_client.py`, `match.py`, `thread_manager.py`, `reddit_client.py` — use `await`, `async with`, `async_send()`
- **Sync context**: `injuries.py`, `discipline.py`, `widgets.py`, APScheduler callbacks (`_job_executed`, `_job_error`) — use `msg.send()` (sync requests)
- **`ThreadManager`**: `save()`, `add_threads()`, `update_thread()`, `prune()` are async. `get_threads()` is sync (read-only, in-memory).
- **Discord**: `send()` is sync (requests), `async_send()` is async (aiohttp). Use the right one based on calling context.

## Data Directories

- `data/` — JSON persistence (threads.json, injuries.json, discipline.json)
- `png/` — Playwright screenshots
- `log/` — Rotating logs (debug.log, controller.log, error.log)
- `assets/` — Team logos

## Tests & CI

```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

Tests never hit the network or Reddit. `tests/conftest.py` loads `config-example.py` as `config`, runs each test in a temp directory, and provides `FixtureClient`, an `MLSApiClient` that serves saved responses from `tests/fixtures/<match_id>/` (a missing file behaves like the API's 404). `MATCH_STATES` covers pre-match, lineups-only, live, final, shootout and missing-endpoint states; add a state there when a new partial-data case shows up. `.github/workflows/ci.yml` runs ruff and pytest on every PR. See `docs/RECOMMENDATIONS.md` for the improvement roadmap.
