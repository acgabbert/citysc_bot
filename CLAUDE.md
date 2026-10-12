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

**Scheduling layer** (`async_controller.py`): `AsyncController` runs an `AsyncIOScheduler` with cron-triggered jobs for daily setup, `threads.json` pruning, injuries, discipline, widgets, and Playwright screenshots. Its main loop touches a heartbeat file each minute for the Docker `HEALTHCHECK`. MLS NEXT Pro teams are routed through a separate API (`get_nextpro_schedule()`). Every job is added with `id=name`; job execution/error callbacks report `event.job_id` (one-off jobs are already gone from the scheduler when they fire) via sync `msg.send()`. Daily job times come from `FEATURE_FLAGS['schedule_times']`, falling back to `DEFAULT_SCHEDULE_TIMES`. `active_matches` stops a second match thread loop starting for the same match. Logging is configured in `configure_logging()`, called from `main()`, so the module imports cleanly in tests.

**Match thread lifecycle** (`match_thread.py`): Three phases — `pre_match_thread()` (24h before), `match_thread()` (30min before kickoff, polling loop during match at `MATCH_UPDATE_INTERVAL`/`MATCH_UPDATE_INTERVAL_LATE`), `post_match_thread()` (after final whistle, via `post_match_thread_with_retry()`). The loop also stops when `Match.is_abandoned()` or `MATCH_THREAD_MAX_HOURS` after kickoff. `post_match_thread()` saves the thread ID before commenting, so a retry never double-posts. Each phase creates/edits Reddit threads and updates `ThreadManager` state.

**Match markdown** (`match_markdown.py`): Generates all Reddit thread markdown — headers, scorers, lineups, stats, injuries, discipline, and footers. `pre_match_thread()`, `match_thread()`, and `post_match_thread()` each return `(title, body)` tuples.

**API data** (`api_client.py` + `match.py`): `MLSApiClient` is an async context manager for MLS API calls. `Match` wraps it with match-specific logic (including reading injury/discipline data from JSON files). Both support session reuse via an optional `client` parameter to avoid creating multiple aiohttp sessions.

**State persistence** (`thread_manager.py`): `ThreadManager` reads/writes `data/threads.json` with atomic writes (tempfile + `os.replace`) and `asyncio.Lock` for concurrency safety. There is one instance, `match_thread.file_manager`, which `async_controller.py` shares; `prune()` drops entries older than `THREADS_MAX_AGE_DAYS`.

**Web scraping** (`injuries.py`, `discipline.py`): Sync functions that scrape the MLS website with BeautifulSoup. Run as APScheduler thread pool jobs (not on the async event loop). Have 30s timeouts and 3x retry. If parsing fails (a page layout change), they keep the previous JSON file and send a tagged Discord alert. Pre-match threads look teams up in those files by the `optaId` the API returns on each club.

**Widgets** (`widgets.py`): Image-only sidebar widget updates via Reddit API. Only `update_image_widget()` remains; it goes through `RedditClient`.

**Schedule planning** (`mls_schedule.py`): `plan_match_jobs()` is a pure function that takes a team's schedule, the current time and a threads lookup and returns the `PlannedJob`s (match, pre-match, post-match catch-up) that `daily_setup()` schedules. Put scheduling decisions here, not in the controller, so `tests/test_scheduler.py` can cover them with fixed clocks. `check_pre_match_sched()` finds the next match within 48h.

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

Tests never hit the network or Reddit. `tests/conftest.py` loads `config-example.py` as `config`, runs each test in a temp directory, and provides `FixtureClient`, an `MLSApiClient` that serves saved responses from `tests/fixtures/<match_id>/` (a missing file behaves like the API's 404). `MATCH_STATES` covers pre-match, lineups-only, live, final, shootout and missing-endpoint states; add a state there when a new partial-data case shows up. `.github/workflows/ci.yml` runs ruff and pytest on every PR. `requirements.txt` is pinned: bump versions on purpose and re-run the tests. See `docs/RECOMMENDATIONS.md` for the improvement roadmap.
