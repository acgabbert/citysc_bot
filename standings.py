import json

import mls_api as mls
import util

BASE_URL = 'https://sportapi.mlssoccer.com/api/standings/live?&isLive=true'
SEASON = '&seasonId='
COMP = '&competitionId='

def get_standings(**kwargs):
    """Get standings."""
    url = BASE_URL
    comp = COMP + mls.MLS[-2:]
    season = SEASON + '2023'
    for key, value in kwargs.items():
        if key == 'comp':
            comp = COMP + str(value)
        if key == 'season':
            season = SEASON + str(value)
            print(season)
    url += comp + season
    data, _ = mls.call_api(url)
    return data


def update_db(data):
    for team in data:
        try:
            id = int(team['club']['optaId'])
        except KeyError:
            # right now STL is blank (no id) in standings results
            continue
        points = team['statistics']['total_points']
        gp = team['statistics']['total_matches']
        gd = team['statistics']['total_goal_differential']
        sql = f'UPDATE team SET points={points}, gp={gp}, gd={gd} WHERE opta_id={id}'
        util.db_query(sql)
    return None


@util.time_dec(False)
def main():
    data = get_standings()
    update_db(data)


if __name__ == '__main__':
    main()
