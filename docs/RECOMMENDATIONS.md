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

### 3.2 `print()` statements scattered throughout production code
**Files:** `injuries.py:68-90`, `match_markdown.py:140`, `reddit_client.py:231`, `discipline.py` (various)

These go to stdout (captured in Docker logs) but provide no log-level filtering. Replace with `logger.debug()` or `logger.info()`.

### 3.3 Duplicate subreddit-prefix stripping logic
The pattern `if '/r/' in sub: sub = sub.split('/r/')[1]` appears in:
- `match_thread.py:40-41`
- `match_thread.py:99-100`
- `match_thread.py:182-183`
- `reddit_client.py:108-109`
- `reddit_client.py:201-202`
- `reddit_client.py:226-227`

Extract this to a single utility function.

### 3.4 Magic numbers throughout scheduling logic
**File:** `async_controller.py`
- `86400` (seconds in a day) — used at lines 98, 117
- `10800` (3 hours) — line 109, 176
- `1800` (30 minutes) — line 121, 176

Define named constants (e.g., `SECONDS_PER_DAY`, `PRE_MATCH_LEAD_TIME`).

### 3.5 Inconsistent error handling patterns
Some methods raise exceptions, some return `None`, some return empty collections, and some swallow exceptions silently. This makes callers fragile. Establish a consistent convention:
- API methods should raise on failure (or return documented empty results)
- Domain methods should propagate or handle explicitly

### 3.6 `util.get_reddit()` is a duplicate of `RedditClient`
**File:** `util.py:229-238`

This function creates a raw `asyncpraw.Reddit` instance without any of the retry/error-handling logic from `RedditClient`. It's used by `widgets.py`. Migrate those call sites to use `RedditClient` instead and remove this function.

### 3.7 Module-level `logging.basicConfig` in `match.py`
**File:** `match.py:16-20`

Calling `logging.basicConfig()` at import time with `stream=sys.stdout` overrides the root logger configuration set by `async_controller.py`. This can cause duplicate log output and unexpected routing to stdout.

---

## Tier 4: Missing Tests & Observability

### 4.1 No test suite
There are zero test files in the project. The Pydantic models, markdown generators, and schedule-checking logic are all highly testable with unit tests. A minimal test suite should cover:
1. `mls_schedule.check_pre_match_sched()` — core scheduling logic
2. Pydantic model parsing — ensure API responses deserialize correctly
3. `match_markdown` — verify generated markdown
4. `thread_manager` — JSON persistence round-trip

### 4.2 No CI/CD pipeline
No `.github/workflows/` or equivalent. Even a minimal pipeline that runs linting (`ruff` or `flake8`) and type checking (`mypy`) would catch many of the bugs listed above.

### 4.3 No structured logging or metrics
All logging is to rotating files and Discord. Consider adding:
- Structured JSON logging for machine parsing
- A simple health-check endpoint (e.g., via a tiny `aiohttp` server) so Docker can use `HEALTHCHECK`
- Counters for API calls, errors, and thread posts (even just logged periodically)

---

## Tier 5: Feature Gaps & Enhancements

### 5.1 Implement `update_injuries()` and `update_discipline()` in `match.Match`
**File:** `match.py:94-98`

Both methods are stubs (`pass`). Port logic to read from the injury/discipline JSON files into the new Match class.

### 5.2 Implement `generate_injuries()`, `generate_discipline()`, and `generate_previous_matchups()`
**File:** `match_markdown.py:168-175`

All three functions return `None`. The pre-match thread currently omits injury/discipline data that was available in the legacy system.

### 5.3 Implement `generate_scorers()`
**File:** `match_markdown.py:39-41`

The `generate_scorers()` function is a stub (`pass`). The match thread header doesn't currently show who scored.

### 5.4 Thread data cleanup / rotation
`threads.json` grows indefinitely over the season. Add a cleanup job that removes entries older than N days to prevent unbounded growth.

### 5.5 Configurable match-update interval
The 60-second polling interval in `match_thread.py:162` is hardcoded. Making it configurable (or reducing it during key moments like second-half injury time) would improve thread timeliness.

### 5.6 Add a README
The project has no `README.md`. A basic README with setup instructions, architecture overview, and configuration guide would significantly help onboarding and future maintenance.

---

## Tier 6: Low-Priority Cleanup

### 6.1 `widgets.py:main()` has repetitive conditional logic
Lines 82-94 repeat the `if sub: ... else: ...` pattern three times. Refactor to:
```python
target_sub = sub or SUB
for name in ['Western Conference', 'This Week', 'Next Week']:
    await update_image_widget(name, target_sub)
```

### 6.2 `widgets.py:71` — bare `except:` clause
```python
except:
    msg.send(f'Failed to update widget {image_path}.')
```
This catches `KeyboardInterrupt`, `SystemExit`, etc. Use `except Exception:` at minimum.

### 6.3 Typos in log messages
- `async_controller.py:119`: `"shceduling"` → `"scheduling"`
- `models/event.py:248`: `"Subsitution"` → `"Substitution"`
- `match.py:153`: docstring says `"linups"` → `"lineups"`

### 6.4 `match_markdown.py` limits stats to "Regular Season" only
**File:** `match_markdown.py:50-51`
```python
if not match_obj.competition in ["Regular Season"]:
    return None
```
This skips stats for playoffs, Leagues Cup, US Open Cup, etc. If this is intentional, add a comment; if not, broaden the check or remove it.

---

## Summary Table

| Tier | Category | Count |
|------|----------|-------|
| ~~1~~ | ~~Bugs & Correctness~~ | ~~9~~ (done) |
| ~~2~~ | ~~Reliability & Robustness~~ | ~~6~~ (done) |
| 3 | Code Quality & Maintainability | 6 (1 done) |
| 4 | Tests & Observability | 3 |
| 5 | Feature Gaps | 6 |
| 6 | Low-Priority Cleanup | 4 |
| | **Total** | **35** |
