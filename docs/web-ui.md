# Web UI for citysc_bot

## Context

The bot currently has no visibility into its runtime state without SSH-ing into the server and reading log files or `threads.json` manually. A lightweight web dashboard would provide at-a-glance status, log viewing, and job management through a browser.

## Approach

**FastAPI** with **Jinja2 templates** + **HTMX** for interactivity, using **Pico CSS** for zero-class styling. The web server runs in the same asyncio event loop as the scheduler via `uvicorn.Server.serve()`, replacing the current `while True: await asyncio.sleep(300)` keepalive loop. No authentication (localhost/private network access).

## New Dependencies

```
fastapi
uvicorn[standard]
jinja2
sse-starlette
```

## File Structure

```
web/
  __init__.py
  app.py                    # FastAPI app factory
  routes/
    __init__.py
    dashboard.py            # GET / — overview + auto-refresh status
    threads.py              # GET /threads — thread viewer
    logs.py                 # GET /logs — log viewer + SSE tailing
    jobs.py                 # GET /jobs — job list + trigger/pause/resume
    matches.py              # GET /matches — match browser via API
  templates/
    base.html               # Layout: nav, Pico CSS, HTMX
    dashboard.html
    threads.html
    logs.html
    jobs.html
    matches.html
    partials/
      log_lines.html        # HTMX partial for log content
      status.html           # HTMX partial for dashboard auto-refresh
      job_list.html         # HTMX partial for job actions
  static/
    style.css               # Minimal custom styles
```

## Routes

| Method | Path | Type | Description |
|--------|------|------|-------------|
| GET | `/` | Page | Dashboard: system status, next jobs, recent log entries |
| GET | `/status` | HTMX partial | Auto-refresh dashboard section (every 30s) |
| GET | `/threads` | Page | All threads from `ThreadManager.threads` with Reddit links |
| GET | `/threads/{sportec_id}` | Page | Single thread detail |
| GET | `/logs` | Page | Log viewer with file selector and filter |
| GET | `/logs/content` | HTMX partial | Filtered log content (query params: `file`, `lines`, `filter`) |
| GET | `/logs/tail` | SSE | Real-time log tailing via Server-Sent Events |
| GET | `/jobs` | Page | All scheduled jobs with next run times |
| POST | `/jobs/{job_id}/trigger` | Action | Manually trigger a job |
| POST | `/jobs/{job_id}/pause` | Action | Pause a scheduled job |
| POST | `/jobs/{job_id}/resume` | Action | Resume a paused job |
| GET | `/matches` | Page | Upcoming/recent matches from MLS API |
| GET | `/matches/{sportec_id}` | Page | Match detail (score, events, lineups) |

## Key Integration: `async_controller.py`

The main change — replace the sleep loop with uvicorn:

```python
# In AsyncController.run():
async def run(self, port: int = 8000):
    # ... existing startup ...
    self.setup_jobs()
    self.scheduler.start()

    # Start web UI in same event loop
    from web.app import create_app
    app = create_app(self, file_manager)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, loop="none")
    server = uvicorn.Server(config)
    await server.serve()  # replaces while True: await asyncio.sleep(300)
```

`loop="none"` tells uvicorn to use the existing event loop. `server.serve()` keeps the process alive (same role as the sleep loop). On SIGINT, uvicorn exits `serve()`, then the `finally` block shuts down the scheduler.

## App Factory: `web/app.py`

```python
def create_app(controller, file_manager):
    app = FastAPI(title="citysc_bot")
    app.state.controller = controller
    app.state.file_manager = file_manager
    app.state.scheduler = controller.scheduler
    # mount static, register routers, configure templates
    return app
```

Route handlers access shared state via `request.app.state`. This is safe because everything runs in one asyncio event loop — no concurrent access issues.

## Files to Modify

1. **`async_controller.py`** — import uvicorn + web app, add `--port` arg, replace sleep loop with `server.serve()`
2. **`requirements.txt`** — add fastapi, uvicorn[standard], jinja2, sse-starlette
3. **`Dockerfile`** — add `COPY --chown=1000:1000 web/ ./web/` and `EXPOSE 8000`
4. **`docker-compose.yml`** — add `ports: ["8000:8000"]`

## Implementation Order

### Phase 1: Foundation
1. Add dependencies to `requirements.txt`
2. Create `web/` directory structure with `__init__.py` files
3. Create `web/app.py` (app factory)
4. Create `web/templates/base.html` (Pico CSS + HTMX layout)
5. Create `web/routes/dashboard.py` + `dashboard.html` (minimal dashboard)
6. Modify `async_controller.py` to start uvicorn
7. Verify scheduler + web server coexist locally

### Phase 2: Core Views
8. Thread viewer (`threads.py` + `threads.html`)
9. Log viewer (`logs.py` + `logs.html` + `partials/log_lines.html`)
10. Job list (`jobs.py` + `jobs.html`, read-only first)

### Phase 3: Interactivity
11. SSE log tailing endpoint
12. Job actions (trigger/pause/resume) with HTMX
13. Match browser (`matches.py` + `matches.html`)

### Phase 4: Deployment
14. Update Dockerfile and docker-compose.yml
15. Test in Docker

## Verification

1. `pip install fastapi uvicorn[standard] jinja2 sse-starlette`
2. Run `python async_controller.py` — verify both scheduler starts AND `http://localhost:8000` serves the dashboard
3. Check `/threads` shows data from `threads.json`
4. Check `/logs` displays log file content, filter works
5. Check `/jobs` lists scheduled jobs with correct next run times
6. Test job trigger/pause/resume via the UI
7. Open `/logs` with SSE tailing, trigger a job, verify new log lines appear in real-time
8. Test in Docker: `docker-compose up --build`, verify port 8000 accessible

## Also: Save Plan to `docs/`

During implementation, save a copy of this plan to `docs/web-ui.md` as requested.
