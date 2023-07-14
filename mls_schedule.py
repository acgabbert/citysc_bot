import json
from datetime import datetime
import time

import discord as msg
import mls_api as mls
import util

BASE_URL = 'https://sportapi.mlssoccer.com/api/matches'
PARAMS = {
    'culture': 'en-us',
    'date_from': '2022-12-31',
    'date_to': '2023-12-31',
    'competition': 98,
    'clubOptaId': 17012
}
# returns optaId and matchDate for all matches in 2023
LITE_URL = 'https://sportapi.mlssoccer.com/api/matchesLite/2023'
SCHEDULE_LITE = 'https://sportapi.mlssoccer.com/api/matchesLite/2022?culture=en-us&competition=98&matchType=Regular'
MATCH_RESULT = 'https://stats-api.mlssoccer.com/v1/matches?&include=away_club_match&include=home_club_match'
GAME_ID = '&match_game_id='
NEXTPRO_URL = 'https://sportapi.mlsnextpro.com/api/matches'

def get_schedule(**kwargs):
    """
    Keyword Args:
        date_from (str): a date in the form YYYY-MM-DD
        date_to (str): a date in the form YYYY-MM-DD
        team (int): a club opta_id
        comp (int): a competition id (e.g. MLS=98)
    """
    url = BASE_URL
    params = PARAMS.copy()
    for key, value in kwargs.items():
        if key == 'date_from':
            params[key] = value
        if key == 'date_to':
            params[key] = value
        # TODO figure out how we want to handle comp here
        if key == 'comp':
            if value is None:
                params.pop('competition')
            elif value == 'MLSNP':
                params.pop('competition')
                url = NEXTPRO_URL
            else:
                params['competition'] = value
        if key == 'team':
            if value is None:
                del params['clubOptaId']
            else:
                params['clubOptaId'] = value
    data, _ = mls.call_api(url, params)
    util.write_json(data, f'assets/schedule-{params["clubOptaId"]}.json')
    return data


def get_lite_schedule():
    data, _ = mls.call_api(SCHEDULE_LITE)
    return data


def check_pre_match(data, date_from=None):
    """If there is a match between 24-48 hours from date_from, return its optaId and time."""
    if date_from is None:
        date_from = int(time.time()) + 86400
    # until +48h
    date_to = date_from + 86400
    for match in data:
        match_time = util.iso_to_epoch(match['matchDate'])
        if match_time > date_from and match_time < date_to:
            return match['optaId'], match_time
    return None, None


def check_pre_match_sched(data, date_from=None):
    """If there is a match within 48 hours from date_from, return its optaId and time."""
    if date_from is None:
        date_from = int(time.time())
    # until +48h
    date_to = date_from + (86400 * 2)
    for match in data:
        match_time = util.iso_to_epoch(match['matchDate'])
        if match_time > date_from and match_time < date_to:
            return match['optaId'], match_time
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
    data = get_schedule(comp=None)
    get_apple_info(data)

if __name__ == '__main__':
    main()
