import time
from typing import List, Optional

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


def kickoff_tbd(data: List[MatchSchedule], match_id: str) -> Optional[str]:
    """The schedule's match_date_time_status ("Time tbd", "Day and time tbd")
    if the league hasn't set the kickoff time for match_id, else None. While
    it's unset, planned_kickoff_time is a placeholder."""
    for match in data:
        if match.match_id == match_id:
            status = match.match_date_time_status or ''
            return status if 'tbd' in status.lower() else None
    return None
