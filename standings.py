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
            season = SEASON + str(season)
    url += comp + season
    data, _ = mls.call_api(url)
    return data


def main():
    get_standings()


if __name__ == '__main__':
    main()
