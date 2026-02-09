# Codebase Audit: Prioritized Recommendations

This document is a prioritized audit of the `citysc_bot` codebase -- a Reddit match-thread automation bot for St. Louis City SC. Items are grouped by category and ordered by impact within each tier.

---

## Tier 1: Bugs & Correctness Issues

These are things that are broken or will produce wrong behavior at runtime.

### 1.1 Hardcoded season ID will break every year
**Files:** `async_controller.py:101`, `models/constants.py:14`, `standings.py:8`

`daily_setup()` hardcodes `MlsSeason.SEASON_2025.value`. When the 2026 season starts, the bot will silently query the wrong season. `standings.py` still hardcodes `seasonId: 2023`.

**Fix:** Derive the current season dynamically from the current date, or add a `CURRENT_SEASON` setting to `config.py`.

### 1.2 Logic bug in `async_controller.py:176` — match-resume condition is inverted
```python
elif match_time.timestamp() > now + 1800 and now - match_time.timestamp() < 10800:
```
The first condition (`match_time > now + 1800`) means the match hasn't started yet, but the intention is to detect a match that *has* started. This branch will never be true. It should be:
```python
elif match_time.timestamp() < now and now - match_time.timestamp() < 10800:
```

### 1.3 `ShotEventDetails.__str__` has a copy-paste bug
**File:** `models/event.py:66`
```python
case "rightLeg":
    shot_description += "left-footed shot"  # should be "right-footed shot"
```

### 1.4 `EventDetails` has a duplicate field declaration
**File:** `models/event.py:12-14`
```python
event_id: int
event_time: UtcDatetime   # first declaration
minute_of_play: Optional[str] = None
event_time: Optional[str] = None  # second — shadows the first
```
The second `event_time` overrides the first (which expected a `UtcDatetime`). This means the validated datetime is discarded. Pick one type and keep only that field.

### 1.5 `MatchScheduleDeprecated` validator is a no-op
**File:** `api_client.py:94`
```python
if self.appleStreamURL and not self.appleStreamURL:  # always False
```
The condition checks if `appleStreamURL` is both truthy and falsy simultaneously. It should probably be:
```python
if self.appleSubscriptionTier and not self.appleStreamURL:
```

### 1.6 Several API methods silently return `None` on validation errors
**Files:** `api_client.py:456-458`, `api_client.py:469-470`, `api_client.py:554-558`, `api_client.py:569-573`, `api_client.py:584-588`, `api_client.py:600-605`, `api_client.py:622-627`

When `ValidationError` is caught the code logs the error but falls through to an implicit `return None`. Callers like `get_all_match_data` then pass `None` into `ComprehensiveMatchData`, which can cascade into `AttributeError` or `TypeError` exceptions later.

**Fix:** Either raise the exception, or return a documented sentinel / empty result.

### 1.7 `match_sportec.py:get_feed()` returns `None` instead of an empty list
**File:** `match_sportec.py:293-298`
```python
def get_feed(self) -> List[str]:
    if not self.data.match_events.events:
        return []
    # missing return statement — falls through to None
```
The method has an early return for no events, but when events *do* exist it doesn't return anything.

### 1.8 `match_sportec.py:get_score()` silently overwrites result
**File:** `match_sportec.py:322-327`
```python
if self.data.match_base.match_information.result:
    result = f"..."  # set result with full team names
home_goals = ...
result = f"{home_goals}-{away_goals}"  # immediately overwritten
```
The first `result` assignment (with team names) is always overwritten by the second. The team-name variant should either use `return` or be removed.

### 1.9 `match_markdown_sportec.py:91` — wrong variable assigned on away lineup miss
```python
if len(starting_lineups[match_obj.away_id]) < 1:
    home_lineup = "Not yet available via mlssoccer.com."  # should be away_lineup
```

---

## Tier 2: Reliability & Robustness

### 2.1 `discord.py` uses synchronous `requests.post` in an async application
**File:** `discord.py:17`

Every Discord notification blocks the event loop. During a live match the bot sends dozens of Discord messages; each one stalls the entire scheduler and API polling. This is the single biggest performance bottleneck in the codebase.

**Fix:** Replace with `aiohttp` (already a dependency) and make `send()` async, or at minimum run it in an executor:
```python
await asyncio.get_event_loop().run_in_executor(None, msg.send, message)
```

### 2.2 `injuries.py` and `discipline.py` use synchronous `requests.get`
**Files:** `injuries.py:41`, `discipline.py:45`

Same issue — these block the event loop when called from the async scheduler.

### 2.3 New `MLSApiClient` session is created on every `Match.refresh()` call
**File:** `match_sportec.py:57-60`

During a live match, `refresh()` is called every 60 seconds. Each call creates a brand-new `MLSApiClient` context manager, opening 6 `aiohttp` sessions and then closing them. This is wasteful and risks connection-pool exhaustion.

**Fix:** Pass the client into `Match` and keep it alive for the duration of the match, or create a module-level singleton.

### 2.4 No timeout or retry on web-scraping requests
**Files:** `injuries.py:41`, `discipline.py:45-48`

`requests.get()` is called with no timeout, no retry, and no error handling. If mlssoccer.com is slow or down, the call hangs indefinitely and blocks the scheduler.

### 2.5 `ThreadManager` file I/O has no locking
**File:** `thread_manager.py:57-63`

`save()` does an open-write-close without any file lock. If two async tasks trigger saves concurrently (unlikely but possible during catch-up logic), the file can be corrupted.

### 2.6 No null-safety in `_process_data`
**File:** `match_sportec.py:69-73`

`_process_data` unconditionally accesses `data.match_info.home`, `data.match_info.competition`, etc. If `match_info` is `None` (which is possible per `ComprehensiveMatchData`), this crashes with `AttributeError`.

---

## Tier 3: Code Quality & Maintainability

### 3.1 Large amount of dead/legacy code
The following modules appear to be superseded by the `*_sportec` versions but are still imported and partially used:
- `match.py` (legacy `Match` class, used only by `widgets.py`)
- `match_markdown.py` (legacy markdown, not used by the async controller)
- `mls_api.py` (legacy sync API client, used only by `standings.py` and `widgets.py`)
- `club.py`, `player.py`, `match_constants.py` (legacy data classes)

This creates confusion about which code path is canonical. Consider removing or deprecating these files and migrating `widgets.py` and `standings.py` to the new API client.

### 3.2 `print()` statements scattered throughout production code
**Files:** `injuries.py:68-90`, `match_markdown_sportec.py:140`, `match.py:576`, `reddit_client.py:231`, `discipline.py` (various)

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

### 3.7 Module-level `logging.basicConfig` in `match_sportec.py`
**File:** `match_sportec.py:16-20`

Calling `logging.basicConfig()` at import time with `stream=sys.stdout` overrides the root logger configuration set by `async_controller.py`. This can cause duplicate log output and unexpected routing to stdout.

---

## Tier 4: Missing Tests & Observability

### 4.1 No test suite
There are zero test files in the project. The Pydantic models, markdown generators, and schedule-checking logic are all highly testable with unit tests. A minimal test suite should cover:
1. `mls_schedule.check_pre_match_sched()` — core scheduling logic
2. Pydantic model parsing — ensure API responses deserialize correctly
3. `match_markdown_sportec` — verify generated markdown
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

### 5.1 Implement `update_injuries()` and `update_discipline()` in `match_sportec.Match`
**File:** `match_sportec.py:94-98`

Both methods are stubs (`pass`). The legacy `match.py` has working implementations that read from the JSON files. Port this logic to the new Match class.

### 5.2 Implement `generate_injuries()`, `generate_discipline()`, and `generate_previous_matchups()`
**File:** `match_markdown_sportec.py:168-175`

All three functions return `None`. The pre-match thread currently omits injury/discipline data that was available in the legacy system.

### 5.3 Implement `generate_scorers()`
**File:** `match_markdown_sportec.py:39-41`

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
Lines 180-192 repeat the `if sub: ... else: ...` pattern three times. Refactor to:
```python
target_sub = sub or SUB
for name in ['Western Conference', 'This Week', 'Next Week']:
    await update_image_widget(name, target_sub)
```

### 6.2 `widgets.py:144` — bare `except:` clause
```python
except:
    msg.send(f'Failed to update widget {image_path}.')
```
This catches `KeyboardInterrupt`, `SystemExit`, etc. Use `except Exception:` at minimum.

### 6.3 Typos in log messages
- `async_controller.py:119`: `"shceduling"` → `"scheduling"`
- `models/event.py:248`: `"Subsitution"` → `"Substitution"`
- `match_sportec.py:153`: docstring says `"linups"` → `"lineups"`

### 6.4 `match_markdown_sportec.py` limits stats to "Regular Season" only
**File:** `match_markdown_sportec.py:50-51`
```python
if not match_obj.competition in ["Regular Season"]:
    return None
```
This skips stats for playoffs, Leagues Cup, US Open Cup, etc. If this is intentional, add a comment; if not, broaden the check or remove it.

---

## Summary Table

| Tier | Category | Count |
|------|----------|-------|
| 1 | Bugs & Correctness | 9 |
| 2 | Reliability & Robustness | 6 |
| 3 | Code Quality & Maintainability | 7 |
| 4 | Tests & Observability | 3 |
| 5 | Feature Gaps | 6 |
| 6 | Low-Priority Cleanup | 4 |
| | **Total** | **35** |
