# Codebase Audit: Prioritized Recommendations

This document is a prioritized audit of the `citysc_bot` codebase -- a Reddit match-thread automation bot for St. Louis City SC. Items are grouped by category and ordered by impact within each tier.

---

## ~~Tier 1: Bugs & Correctness Issues~~ (All resolved)

All 9 issues in this tier have been fixed.

- [x] **1.1** Hardcoded season ID — Added `get_current_season()` helper to `models/constants.py`; updated `async_controller.py` and `standings.py`.
- [x] **1.2** Inverted match-resume condition — Fixed condition in `async_controller.py:176`.
- [x] **1.3** Copy-paste "left-footed" for rightLeg — Fixed in `models/event.py`.
- [x] **1.4** Duplicate `event_time` field — Consolidated to single `Optional[UtcDatetime]` in `models/event.py`.
- [x] **1.5** No-op validator (`x and not x`) — Fixed to check `appleSubscriptionTier` in `api_client.py`.
- [x] **1.6** Silent `None` returns on ValidationError — Added `raise` after logging in 7 API methods in `api_client.py`.
- [x] **1.7** `get_feed()` missing return — Added return statement in `match.py`.
- [x] **1.8** `get_score()` dead code overwrite — Removed unreachable team-name assignment in `match.py`.
- [x] **1.9** Wrong variable on away lineup miss — Fixed to assign `away_lineup` in `match_markdown.py`.

---

## ~~Tier 2: Reliability & Robustness~~ (All resolved)

- [x] **2.1** Sync `discord.py` — Added `async_send()` using aiohttp for async callers; sync `send()` retained for APScheduler callbacks.
- [x] **2.2** Sync `injuries.py`/`discipline.py` — These run as APScheduler thread pool jobs (not on the event loop), so sync is correct by design.
- [x] **2.3** Session per `refresh()` — `Match.create()` and `Match.refresh()` now accept optional `client` param for session reuse.
- [x] **2.4** No timeout/retry on scraping — Added 30s timeout and 3x retry to `injuries.py` and `discipline.py`.
- [x] **2.5** `ThreadManager` no locking — Added atomic writes (tempfile + `os.replace`) and `asyncio.Lock`.
- [x] **2.6** No null-safety in `_process_data` — Added guards for `match_info` and `match_base` being `None`.

---

## Tier 3: Code Quality & Maintainability

### ~~3.1 Large amount of dead/legacy code~~ (Resolved)
Deleted 8 legacy modules (`match.py`, `match_markdown.py`, `mls_api.py`, `match_constants.py`, `club.py`, `player.py`, `widget_markdown.py`, `standings.py`). Cleaned up `widgets.py`, `mls_schedule.py`, `models/club.py`, and `api_client.py` to remove all dead imports, functions, and constants.

### ~~3.2 `print()` statements scattered throughout production code~~ (Resolved)
`injuries.py` and `reddit_client.py` now use the logger. The remaining `print()` calls are in CLI entry points (`__main__` / `main()`), where printing is intended.

### ~~3.3 Duplicate subreddit-prefix stripping logic~~ (Resolved)
`reddit_client.subreddit_name()` replaces the six copies.

### ~~3.4 Magic numbers throughout scheduling logic~~ (Resolved)
`async_controller.py` now uses `SECONDS_PER_DAY`, `MATCH_THREAD_LEAD_TIME`, `MATCH_IN_PROGRESS_WINDOW` and `CITY2_OPTA_ID`.

### 3.5 Inconsistent error handling patterns
Some methods raise exceptions, some return `None`, some return empty collections, and some swallow exceptions silently. This makes callers fragile. Establish a consistent convention:
- API methods should raise on failure (or return documented empty results)
- Domain methods should propagate or handle explicitly

### ~~3.6 `util.get_reddit()` is a duplicate of `RedditClient`~~ (Resolved)
Removed, along with the unused widget helpers in `widgets.py` that called it.

### ~~3.7 Module-level `logging.basicConfig` in `match.py`~~ (Resolved)
Removed. `async_controller.py` now adds its own stdout handler so `docker compose logs` still shows INFO-level output.

---

## Tier 4: Missing Tests & Observability

### ~~4.1 No test suite~~ (Resolved)
`tests/` covers model parsing, `Match`, `match_markdown`, `check_pre_match_sched()` and `ThreadManager`, using real MLS API responses saved in `tests/fixtures/` (pre-match, final, extra time + shootout) plus derived states (a playoff match, lineups only, mid-match, missing `match_base`/`match_events`/stats).

### ~~4.2 No CI/CD pipeline~~ (Resolved)
`.github/workflows/ci.yml` runs `ruff check .` and `pytest` on every PR and push to `main`. Ruff is limited to correctness rules (`E9`, `F`, `PLE`) for now; type checking (`mypy`) is not set up yet.

### 4.3 No structured logging or metrics
The Docker health check is done: the controller touches a heartbeat file every minute and the `HEALTHCHECK` marks the container unhealthy when it goes stale. Still open:
- Structured JSON logging for machine parsing
- Counters for API calls, errors, and thread posts (even just logged periodically)

---

## Tier 5: Feature Gaps & Enhancements

### ~~5.1 Implement `update_injuries()` and `update_discipline()` in `match.Match`~~ (Resolved)

### 5.2 Implement `generate_previous_matchups()`
**File:** `match_markdown.py`

`generate_injuries()` and `generate_discipline()` are done. `generate_previous_matchups()` still returns `None`.

### ~~5.3 Implement `generate_scorers()`~~ (Resolved)

### ~~5.4 Thread data cleanup / rotation~~ (Resolved)
Entries record when they were first saved; a daily `prune_threads` job removes ones older than `THREADS_MAX_AGE_DAYS` (default 30). The controller now shares `match_thread`'s `ThreadManager` instead of keeping a second copy.

### ~~5.5 Configurable match-update interval~~ (Resolved)
`MATCH_UPDATE_INTERVAL` (default 60s) and `MATCH_UPDATE_INTERVAL_LATE` (from the 80th minute on) in `config.py`.

### ~~5.6 Add a README~~ (Resolved)
Added `README.md`.

---

## ~~Tier 6: Low-Priority Cleanup~~ (All resolved)

### ~~6.1 `widgets.py:main()` has repetitive conditional logic~~ (Resolved)

### ~~6.2 `widgets.py` — bare `except:` clause~~ (Resolved)

### ~~6.3 Typos in log messages~~ (Resolved)

### ~~6.4 `match_markdown.py` limits stats to "Regular Season" only~~ (Resolved)
The filter is gone: playoff and cup matches get a stats table whenever the stats API has data. The U.S. Open Cup fixture confirms it does for cup matches.

---

## Summary Table

| Tier | Category | Count |
|------|----------|-------|
| ~~1~~ | ~~Bugs & Correctness~~ | ~~9~~ (done) |
| ~~2~~ | ~~Reliability & Robustness~~ | ~~6~~ (done) |
| 3 | Code Quality & Maintainability | 7 (6 done) |
| 4 | Tests & Observability | 3 (2 done, 1 partial) |
| 5 | Feature Gaps | 6 (5 done, 1 open) |
| ~~6~~ | ~~Low-Priority Cleanup~~ | ~~4~~ (done) |
| | **Total** | **35** |
