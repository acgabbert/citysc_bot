import time
from typing import List

from models.schedule import MatchSchedule


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
