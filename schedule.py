import mls_api as mls
import util

BASE_URL = 'https://sportapi.mlssoccer.com/api/matches?culture=en-us'
# returns optaId and matchDate for all matches in 2023
SCHEDULE_LITE = 'https://sportapi.mlssoccer.com/api/matchesLite/2023?culture=en-us&competition=98&matchType=Regular'


def get_schedule(**kwargs):
    """asdf
    Keyword Args:
        date_from (str): a date in the form YYYY-MM-DD
        date_to (str): a date in the form YYYY-MM-DD
    """
    url = BASE_URL
    date_from = '2022-12-31'
    date_to = '2023-12-31'
    comp = mls.MLS_REGULAR
    team = None
    for key, value in kwargs.items():
        if key == 'date_from':
            date_from = mls.DATE_FROM + value
        if key == 'date_to':
            date_to = mls.DATE_TO + value
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
        home = row['home']['shortName']
        away = row['away']['shortName']
        slug = row['slug']
        comp = row['competition']['name']
        venue = row['venue']['name']
        sql = 'INSERT OR REPLACE INTO match(opta_id, home, away, slug, comp, venue) VALUES (?,?,?,?,?,?)'
        match_data = (opta_id, home, away, slug, comp, venue)
        util.db_query(sql, match_data)
    return None


@util.time_dec(False)
def main():
    data = get_schedule(team=421)
    print(data)

if __name__ == '__main__':
    main()