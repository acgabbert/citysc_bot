import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, List, Optional

from models.schedule import MatchSchedule
from thread_manager import MatchThreads

# Match threads go up this long before kickoff
MATCH_THREAD_LEAD_TIME = timedelta(minutes=30)
# A match that kicked off less than this long ago may still be in progress
MATCH_IN_PROGRESS_WINDOW = timedelta(hours=3)
# Pre-match threads go up at this local hour on matchday...
PRE_MATCH_HOUR = 4
# ...and are caught up (e.g. after a restart) until this hour
PRE_MATCH_CATCHUP_END_HOUR = 9
# A finished match with a match thread but no post-match thread gets one if it kicked off this recently
POST_MATCH_CATCHUP_WINDOW = timedelta(hours=24)


def check_pre_match_sched(data: List[MatchSchedule], date_from=None):
    """If there is a match within 48 hours from date_from, return its sportec ID and time."""
    if date_from is None:
        date_from = int(time.time())
    # until +48h
    date_to = date_from + (86400 * 2)
    for match in data:
        match_time = match.planned_kickoff_time.timestamp()
        if match_time > date_from and match_time < date_to:
            return match.match_id, match.planned_kickoff_time
    return None, None


@dataclass(frozen=True)
class PlannedJob:
    """A thread job daily setup should schedule."""
    kind: str           # 'match', 'pre_match' or 'post_match'
    match_id: str
    run_date: datetime
    reason: str
    post: bool = True   # match jobs only: post a post-match thread when the match ends


def plan_match_jobs(
    schedule: List[MatchSchedule],
    now: datetime,
    get_threads: Callable[[str], Optional[MatchThreads]],
    match_threads_only: bool = False,
) -> List[PlannedJob]:
    """
    Decide which thread jobs to schedule for one team.

    Args:
        schedule: The team's matches around today
        now: The current time (timezone-aware); "today" and hours are local time
        get_threads: Looks up threads already posted for a match ID
        match_threads_only: True for teams that get no pre- or post-match threads
    """
    local_now = now.astimezone()
    jobs: List[PlannedJob] = []
    post = not match_threads_only

    # Look back far enough to find a match that's already in progress
    date_from = int((now - MATCH_IN_PROGRESS_WINDOW).timestamp())
    match_id, match_time = check_pre_match_sched(schedule, date_from=date_from)

    if match_id is not None:
        local_time = match_time.astimezone()
        if match_time < now + timedelta(days=1) and local_now.date() == local_time.date():
            thread_time = match_time - MATCH_THREAD_LEAD_TIME
            if thread_time < now:
                jobs.append(PlannedJob('match', match_id, now, 'match thread is overdue', post))
            else:
                jobs.append(PlannedJob('match', match_id, thread_time, 'match thread', post))

            if not match_threads_only:
                if local_now.hour < PRE_MATCH_HOUR:
                    pre_match_time = local_now.replace(hour=PRE_MATCH_HOUR, minute=0, second=0, microsecond=0)
                    jobs.append(PlannedJob('pre_match', match_id, pre_match_time, 'pre-match thread'))
                elif local_now.hour < PRE_MATCH_CATCHUP_END_HOUR:
                    threads = get_threads(match_id)
                    if threads is None or not threads.pre:
                        jobs.append(PlannedJob('pre_match', match_id, now, 'catch-up pre-match thread'))

        elif match_time < now and now - match_time < MATCH_IN_PROGRESS_WINDOW:
            # Kicked off yesterday (local time) and may still be going
            threads = get_threads(match_id)
            if threads and threads.match and not threads.post:
                jobs.append(PlannedJob('match', match_id, now, 'resume match thread', post))

    if not match_threads_only:
        planned = {job.match_id for job in jobs}
        for match in schedule:
            kickoff = match.planned_kickoff_time
            if match.match_id in planned or kickoff is None or match.match_status != 'finalWhistle':
                continue
            if not timedelta(0) < now - kickoff <= POST_MATCH_CATCHUP_WINDOW:
                continue
            threads = get_threads(match.match_id)
            if threads and threads.match and not threads.post:
                jobs.append(PlannedJob('post_match', match.match_id, now, 'missing post-match thread'))

    return jobs
