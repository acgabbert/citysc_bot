import requests
import json
import logging

import discord as msg
import util

logging.basicConfig(filename='log/mls_api.log', format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
filename = 'assets/standings.json'
BASE_URL = 'https://sportapi.mlssoccer.com/api/'
standings = 'https://sportapi.mlssoccer.com/api/standings/live?isLive=true&'
commentary = 'https://stats-api.mlssoccer.com/v1/commentaries?'
MLS = '&competition=98'
MLS_REGULAR = MLS + '&matchType=Regular'
MLS_CUP = MLS + '&matchType=Cup'
USOPEN_CUP = '&competition=557'
CONCACAF_CL = '&competition=549'
LEAGUES_CUP = '&competition=1045'
ALL_STAR_GAME = '&competition=355'
FRIENDLY = '&competition=34'
# format: YYYY-MM-DD
DATE_FROM = '&dateFrom='
DATE_TO = '&dateTo='
SEASON = '&seasonId='
match = '&match_game_id='
commentary_tail = '?&match_game_id=2261459&include=club&include=player&include=player_match&order_by=-commentary_period&order_by=-commentary_minute&order_by=-commentary_second&order_by=-commentary_timestamp&order_by=-commentary_opta_id&page=0&page_size=500'


def call_api(url: str):
    """Call the MLS API at the given url, and return the json data and status code.
    Keyword arguments:
    url -- the url to call"""
    headers = {
        'user-agent': USER_AGENT,
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.5',
        'sec-fetch-mode': 'cors'
    }
    r = requests.get(url, headers=headers)
    print(r.request.headers)
    if r.status_code != 200:
        message = f'{r.status_code}: {r.reason}'
        logging.error(message)
        msg.send(message)
        return None, r.status_code
    else:
        data = r.json()
        return data, r.status_code

@util.time_dec
def main():
    request_url = 'https://stats-api.mlssoccer.com/v1/commentaries?&match_game_id=2261459&include=club&include=player&include=player_match&order_by=-commentary_period&order_by=-commentary_minute&order_by=-commentary_second&order_by=-commentary_timestamp&order_by=-commentary_opta_id&page=0&page_size=500'
    data, status = call_api(request_url)
    print(status)
    return None

if __name__ == '__main__':
    main()
