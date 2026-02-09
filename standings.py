from datetime import datetime

import mls_api as mls
import util
from club import Club

BASE_URL = 'https://sportapi.mlssoccer.com/api/standings/live?&isLive=true'
PARAMS = {
    'isLive': 'true',
    'seasonId': datetime.now().year,
    'competitionId': 98
}
SEASON = '&seasonId='
COMP = '&competitionId='

def get_standings(**kwargs):
    """Get standings."""
    url = BASE_URL
    comp = COMP + mls.MLS[-2:]
    season = SEASON + str(datetime.now().year)
    for key, value in kwargs.items():
        if key == 'comp':
            comp = COMP + str(value)
        if key == 'season':
            season = SEASON + str(value)
            #print(season)
    url += comp + season
    data, _ = mls.call_api(url)
    return data


def get_clubs():
    data = get_standings()
    clubs = []
    for team in data:
        adder = Club(team['club']['optaId'])
        adder.conference = team['group_id']
        adder.position = team['position']
        adder.points = team['statistics']['total_points']
        adder.gd = team['statistics']['total_goal_differential']
        adder.gp = team['statistics']['total_matches']
        clubs.append(adder)
    return clubs


@util.time_dec(False)
def main():
    data = get_standings()
    print(data)


if __name__ == '__main__':
    main()
