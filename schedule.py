import mls_api as mls
import util

SCHEDULE_BASE = 'https://sportapi.mlssoccer.com/api/matches?culture=en-us'
# returns optaId and matchDate for all matches in 2023
SCHEDULE_LITE = 'https://sportapi.mlssoccer.com/api/matchesLite/2023?culture=en-us&competition=98&matchType=Regular'

def get_schedule(date_from='2022-12-31', date_to='2023-12-31', team=None):
    """Call the MLS API to get a schedule.
    Keyword arguments:
    date_from -- 
    date_to -- 
    team -- optaId of the team"""
    url = SCHEDULE_BASE + mls.DATE_FROM + date_from + mls.DATE_TO + date_to + mls.MLS_REGULAR
    print(url) 
    data, status = mls.call_api(url)
    return data


def craft_url(date_from, date_to, team):
    url = SCHEDULE_BASE
    return url


def get_lite_schedule():
    data, status = mls.call_api(SCHEDULE_LITE)
    return data


@util.time_dec
def main():
    data = get_schedule()
    for row in data:
        opta_id = row['optaId']
        home = row['home']['shortName']
        away = row['away']['shortName']
        slug = row['slug']
        comp = row['competition']['name']
        venue = row['venue']['name']
        sql = 'INSERT OR REPLACE INTO match(opta_id, home, away, slug, comp, venue) VALUES (?,?,?,?,?,?)'
        match_data = (opta_id, home, away, slug, comp, venue)
        util.db_query(sql, match_data)

if __name__ == '__main__':
    main()