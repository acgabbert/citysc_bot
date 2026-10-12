import argparse
import asyncio
import logging, logging.handlers
import os
import sys
import tempfile
import time

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timedelta

from api_client import MLSApiClient, MLSApiClientError
import discipline
import discord as msg
import injuries
import match_thread as thread
import mls_schedule
import mls_playwright
from models.constants import get_current_season
import widgets
import config
from config import FEATURE_FLAGS, SUB, TEAMS
from util import names

root = logging.getLogger()


def configure_logging() -> None:
    """Log to rotating files in log/ and to stdout (for `docker compose logs`)."""
    fh = logging.handlers.RotatingFileHandler('log/debug.log', maxBytes=1000000, backupCount=10)
    fh.setLevel(logging.DEBUG)
    fh2 = logging.handlers.RotatingFileHandler('log/controller.log', maxBytes=1000000, backupCount=5)
    fh2.setLevel(logging.INFO)
    er = logging.handlers.RotatingFileHandler('log/error.log', maxBytes=2000000, backupCount=2)
    er.setLevel(logging.ERROR)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    for handler in (fh, fh2, er, sh):
        handler.setFormatter(formatter)
        root.addHandler(handler)
    root.setLevel(logging.INFO)


parser = argparse.ArgumentParser(prog='async_controller.py', usage='%(prog)s [options]', description='')
parser.add_argument('-s', '--sub', help=f'Subreddit; default = {SUB}')
# Threads are tracked in match_thread.file_manager, the only ThreadManager:
# a second instance would miss threads posted after startup and undo prunes.

# St. Louis CITY 2 (MLS NEXT Pro) gets match threads only: no pre- or post-match threads
CITY2_OPTA_ID = 19202

# Default daily job times (local, 24h). FEATURE_FLAGS['schedule_times'] overrides them.
DEFAULT_SCHEDULE_TIMES = {
    'playwright': '00:45',
    'widgets': '01:00',
    'injuries': '01:15',
    'discipline': '01:15',
    'prune_threads': '01:25',
    'daily_setup': '01:30',
}

# Touched every HEARTBEAT_INTERVAL seconds while the event loop is running;
# the Docker HEALTHCHECK reports unhealthy when it goes stale.
HEARTBEAT_FILE = os.path.join(tempfile.gettempdir(), 'citysc_bot.heartbeat')
HEARTBEAT_INTERVAL = 60


def write_heartbeat() -> None:
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(str(time.time()))
    except OSError as e:
        root.warning(f'Could not write heartbeat file {HEARTBEAT_FILE}: {e}')


def schedule_time(job: str) -> tuple[int, int]:
    """(hour, minute) to run a daily job, from FEATURE_FLAGS['schedule_times'] if set there."""
    times = FEATURE_FLAGS.get('schedule_times', {})
    # 'selenium' is the old name for the playwright screenshot job
    value = times.get(job) or (times.get('selenium') if job == 'playwright' else None)
    value = value or DEFAULT_SCHEDULE_TIMES[job]
    hour, minute = value.split(':')
    return int(hour), int(minute)


class AsyncController:
    """Main controller class for scheduling and managing async tasks"""

    def __init__(self, subreddit: str):
        self.subreddit = subreddit
        self.scheduler = AsyncIOScheduler()
        # Match IDs whose match thread loop is running, so a resume can't start a second one
        self.active_matches: set[str] = set()

        # Add job listeners for logging
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

    # Jobs are added with id=name. One-off jobs are removed from the scheduler
    # before these listeners run, so use event.job_id rather than get_job().
    def _job_executed(self, event: JobEvent):
        """Log successful job execution"""
        message = f'Job {event.job_id} executed successfully'
        root.info(message)
        msg.send(message)

    def _job_error(self, event: JobEvent):
        """Log job execution errors"""
        message = f'Error in job {event.job_id}: {str(event.exception)}'
        root.error(f'{message}\n{event.traceback or ""}')
        msg.send(message, tag=True)

    def _add_job(self, func, trigger, name: str, **kwargs) -> None:
        self.scheduler.add_job(func, trigger, id=name, name=name, replace_existing=True, **kwargs)

    async def create_match_thread(self, sportec_id: str, post: bool = True):
        """Create a match thread in an async context"""
        if sportec_id in self.active_matches:
            message = f'Match thread for {sportec_id} is already running'
            root.info(message)
            await msg.async_send(message)
            return

        message = f'Posting match thread for {sportec_id} on subreddit {self.subreddit}'
        root.info(message)
        await msg.async_send(message, tag=True)

        self.active_matches.add(sportec_id)
        try:
            await thread.match_thread(sportec_id, self.subreddit, post=post)
        except Exception as e:
            root.exception(f"Error creating match thread: {str(e)}")
            await msg.async_send(f"Error creating match thread for {sportec_id}: {str(e)}", tag=True)
        finally:
            self.active_matches.discard(sportec_id)

    async def create_pre_match_thread(self, sportec_id: str):
        """Post a pre-match thread unless one already exists. Errors go to _job_error."""
        threads = thread.file_manager.get_threads(sportec_id)
        if threads and threads.pre:
            root.info(f'Pre-match thread for {sportec_id} already exists')
            return
        await thread.pre_match_thread(sportec_id, self.subreddit)

    async def create_post_match_thread(self, sportec_id: str):
        """Catch up a missing post-match thread, unless the match thread loop will post it."""
        if sportec_id in self.active_matches:
            root.info(f'Match thread for {sportec_id} is running and will post the post-match thread')
            return
        await thread.post_match_thread_with_retry(sportec_id, self.subreddit)

    def schedule_planned_job(self, job: mls_schedule.PlannedJob) -> None:
        if job.kind == 'match':
            self._add_job(self.create_match_thread, 'date', f'match_thread_{job.match_id}',
                          run_date=job.run_date, args=[job.match_id, job.post])
        elif job.kind == 'pre_match':
            self._add_job(self.create_pre_match_thread, 'date', f'pre_match_thread_{job.match_id}',
                          run_date=job.run_date, args=[job.match_id])
        elif job.kind == 'post_match':
            self._add_job(self.create_post_match_thread, 'date', f'post_match_thread_{job.match_id}',
                          run_date=job.run_date, args=[job.match_id])
        else:
            raise ValueError(f'Unknown job kind {job.kind}')

    async def daily_setup(self):
        """Check for upcoming matches and schedule threads"""
        message = "Running daily setup..."
        root.info(message)
        await msg.async_send(message)

        for team in TEAMS:
            try:
                async with MLSApiClient() as client:
                    from_date = date.today() - timedelta(days=5)
                    to_date = date.today() + timedelta(days=5)
                    data = await client.get_schedule(
                        season=get_current_season(),
                        match_date_gte=from_date.isoformat(),
                        match_date_lte=to_date.isoformat(),
                        team_id=names[team].sportec_id
                    )

                jobs = mls_schedule.plan_match_jobs(
                    data,
                    now=datetime.now().astimezone(),
                    get_threads=thread.file_manager.get_threads,
                    match_threads_only=team == CITY2_OPTA_ID,
                )
                for job in jobs:
                    self.schedule_planned_job(job)
                    message = (
                        f'Scheduled {job.reason} for {job.match_id} at '
                        f'{job.run_date.astimezone().strftime("%H:%M")}. Team {team}'
                    )
                    root.info(message)
                    await msg.async_send(message)
                if not jobs:
                    message = f'No matches today for {team}.'
                    root.info(message)
                    await msg.async_send(message)

            except MLSApiClientError as e:
                root.exception(f"Error fetching data for team {team}: {str(e)}")
                await msg.async_send(f"Error fetching data for team {team}: {str(e)}")
            except Exception as e:
                root.exception(f"Error in daily setup for team {team}: {str(e)}")
                await msg.async_send(f"Error in daily setup for team {team}: {str(e)}", True)

    async def prune_threads(self):
        """Remove old entries from threads.json"""
        max_age = getattr(config, 'THREADS_MAX_AGE_DAYS', 30)
        removed = await thread.file_manager.prune(max_age)
        root.info(f'Pruned {removed} thread entries older than {max_age} days')

    async def update_widgets(self):
        await widgets.main(self.subreddit)

    def _add_daily_job(self, func, name: str) -> None:
        hour, minute = schedule_time(name)
        self._add_job(func, CronTrigger(hour=hour, minute=minute), name)

    def setup_jobs(self, now: datetime = None):
        """Setup all scheduled jobs based on feature flags"""
        if FEATURE_FLAGS['enable_widgets']:
            self._add_daily_job(mls_playwright.main, 'playwright')
            self._add_daily_job(self.update_widgets, 'widgets')

        if FEATURE_FLAGS['enable_injuries']:
            self._add_daily_job(injuries.main, 'injuries')

        if FEATURE_FLAGS['enable_discipline']:
            self._add_daily_job(discipline.main, 'discipline')

        if FEATURE_FLAGS['enable_daily_setup']:
            self._add_daily_job(self.daily_setup, 'daily_setup')
            self._add_daily_job(self.prune_threads, 'prune_threads')

            # If today's daily setup time has passed (e.g. after a restart), run it now
            now = now or datetime.now()
            hour, minute = schedule_time('daily_setup')
            if (now.hour, now.minute) >= (hour, minute):
                self._add_job(self.daily_setup, 'date', 'daily_setup_catchup', run_date=now)

    async def run(self):
        """Main run loop"""
        message = f'Started controller at {time.time()}. Subreddit {self.subreddit}\n{str(FEATURE_FLAGS)}'
        root.info(message)
        await msg.async_send(message, tag=True)

        try:
            self.setup_jobs()
            self.scheduler.start()

            # Keep running until interrupted
            while True:
                write_heartbeat()
                await asyncio.sleep(HEARTBEAT_INTERVAL)

        except (KeyboardInterrupt, asyncio.CancelledError):
            message = "Received interrupt "
            root.info(message)
            msg.send(message)

        finally:
            message = "Shutting down scheduler..."
            root.info(message)
            msg.send(message)
            self.scheduler.shutdown()

async def main():
    configure_logging()
    args = parser.parse_args()
    subreddit = args.sub if args.sub else SUB
    if '/r/' not in subreddit:
        subreddit = f'/r/{subreddit}'

    controller = AsyncController(subreddit)
    await controller.run()

if __name__ == '__main__':
    asyncio.run(main())
