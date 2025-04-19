import json
from datetime import datetime
from typing import List
import time

from api_client import MatchScheduleDeprecated
import discord as msg
import mls_api as mls
from models.schedule import MatchSchedule
import util

def check_pre_match(data: List[MatchScheduleDeprecated], date_from=None):
    """If there is a match between 24-48 hours from date_from, return its optaId and time."""
    if date_from is None:
        date_from = int(time.time()) + 86400
    # until +48h
    date_to = date_from + 86400
    for match in data:
        match_time = match.matchDate.timestamp()
        if match_time > date_from and match_time < date_to:
            return match.optaId, match.matchDate
    return None, None


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


def get_upcoming_matches(data):
    """Returns opta ID's of the next 5 upcoming matches.
    For the upcoming widget."""
    today = int(time.time())
    upcoming = []
    for row in data:
        id = row['optaId']
        match_time = util.iso_to_epoch(row['matchDate'])
        if match_time > today:
            upcoming.append(id)
            if len(upcoming) >= 5:
                break
    return upcoming


def get_apple_info(data):
    for row in data:
        print(f'{row["optaId"]}, {row["slug"]}: {row["appleSubscriptionTier"]}, {row["appleStreamURL"]}')
        for b in row['broadcasters']:
            print(f'- {b["broadcasterName"]}')


@util.time_dec(False)
def main():
    pass

if __name__ == '__main__':
    main()
