import json
from datetime import datetime

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
    params = PARAMS.copy()
    for key, value in kwargs.items():
        if key == 'date_from':
            params[key] = value
        if key == 'date_to':
            params[key] = value
        # TODO figure out how we want to handle comp here
        if key == 'comp':
            if value is None:
                del params['competition']
            else:
                params['competition'] = value
        if key == 'team':
            if value is None:
                del params['clubOptaId']
            else:
                params['clubOptaId'] = value
    data, _ = mls.call_api(url, params)
    return data


def get_lite_schedule():
    data, _ = mls.call_api(SCHEDULE_LITE)
    return data


def update_db(data):
    """Update the database with schedule data."""
    count_sql = 'SELECT COUNT() FROM match'
    before_count = util.db_query(count_sql)
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

    after_count = util.db_query(count_sql)
    if before_count != after_count:
        msg.send(f'Database updated. Before: {before_count}. After: {after_count}')
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
    i = 0
    p = 50
    # process rows 50 at a time
    for i in range(0, len(matches), p):
        url = MATCH_RESULT
        temp_list = matches[i:i+p]
        for id in temp_list:
            url += GAME_ID + str(id[0])
        print(url)
        results = mls.call_api(url)[0]
        for row in results:
            opta_id = row['opta_id']
            is_final = 1 if row['is_final'] else 0
            home_score = 0 if row['home_club_match']['score'] is None else row['home_club_match']['score']
            away_score = 0 if row['away_club_match']['score'] is None else row['away_club_match']['score']
            sql = f'UPDATE match SET is_final={is_final}, home_score={home_score}, away_score={away_score} WHERE opta_id={opta_id}'
            result = (opta_id, is_final, home_score, away_score)
            print(result)
            util.db_query(sql)


@util.time_dec(False)
def main():
    data = get_schedule()
    update_db(data)

if __name__ == '__main__':
    main()
