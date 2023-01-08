import json
from datetime import datetime

import mls_api as mls
import util

BASE_URL = 'https://sportapi.mlssoccer.com/api/matches?culture=en-us'
# returns optaId and matchDate for all matches in 2023
SCHEDULE_LITE = 'https://sportapi.mlssoccer.com/api/matchesLite/2022?culture=en-us&competition=98&matchType=Regular'
MATCH_RESULT = 'https://stats-api.mlssoccer.com/v1/matches?&include=away_club_match&include=home_club_match'
GAME_ID = '&match_game_id='

def get_schedule(**kwargs):
    """asdf
    Keyword Args:
        date_from (str): a date in the form YYYY-MM-DD
        date_to (str): a date in the form YYYY-MM-DD
        team (int): a club opta_id
    """
    url = BASE_URL
    date_from = '2022-12-31'
    date_to = '2023-12-31'
    comp = mls.MLS_REGULAR
    team = None
    for key, value in kwargs.items():
        if key == 'date_from':
            date_from = value
        if key == 'date_to':
            date_to = value
        # TODO figure out how we want to handle comp here
        if key == 'comp':
            comp = value
        if key == 'team':
            team = f'&clubOptaId={value}'
    url = BASE_URL + mls.DATE_FROM + date_from + mls.DATE_TO + date_to
    if team is not None:
        url += team
    if comp is None:
        pass
    else:
        url += comp
    print(url)
    data, status = mls.call_api(url)
    return data


def craft_url(date_from, date_to, team):
    url = BASE_URL
    return url


def get_lite_schedule():
    data, status = mls.call_api(SCHEDULE_LITE)
    return data


def update_db(data):
    """Update the database with schedule data."""
    for row in data:
        opta_id = row['optaId']
        try:
            home = int(row['home']['optaId'])
        except KeyError:
            home = -1
        try:
            away = int(row['away']['optaId'])
        except KeyError:
            away = -1
        match_time = row['matchDate']
        # the next two lines of code only work with python 3.11 or higher
        match_time = datetime.fromisoformat(match_time)
        # this will convert the UTC time to local time
        match_time = match_time.astimezone(tz=None)
        match_time = int(match_time.strftime('%s'))
        comp = row['competition']['name']
        venue = row['venue']['name']
        match_data = (opta_id, home, away, match_time, venue, comp)
        # if the match already exists, update the following values
        sql = f'UPDATE match SET home={home}, away={away}, time={match_time}, venue="{venue}", comp="{comp}" WHERE opta_id={opta_id}'
        util.db_query(sql)
        # if it doesn't exist, insert a new row
        sql = 'INSERT OR IGNORE INTO match(opta_id, home, away, time, venue, comp) VALUES (?,?,?,?,?,?)'
        util.db_query(sql, match_data)
    return None


def process_results(matches):
    url = MATCH_RESULT
    for id in matches:
        url += GAME_ID + str(id[0])
    print(url)
    results = mls.call_api(url)[0]
    for row in results:
        pass


def update_results():
    # get all match ids
    sql = 'SELECT opta_id FROM match'
    matches = util.db_query(sql)
    url = MATCH_RESULT
    i = 0
    for id in matches:
        url += GAME_ID + str(id[0])
        i += 1
        if i == 10:
            break
    print(url)
    results = mls.call_api(url)[0]
    # TODO problem this query replaces other values with null
    for row in results:
        opta_id = row['opta_id']
        is_final = row['is_final']
        home_score = row['home_club_match']['score']
        away_score = row['away_club_match']['score']
        sql = f'UPDATE match SET is_final={is_final}, home_score={home_score}, away_score={away_score} WHERE opta_id={opta_id}'
        result = (opta_id, is_final, home_score, away_score)
        print(result)
        util.db_query(sql)


@util.time_dec(False)
def main():
    data = get_schedule(comp=None)
    update_db(data)
    util.write_json(data, 'assets/schedule.json')
    #update_results()

if __name__ == '__main__':
    main()
