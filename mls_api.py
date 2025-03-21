import requests
import json
import logging

import config
import discord as msg
import util


USER_AGENT = config.USER_AGENT_STR
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


class MlsObject:
    def __init__(self, opta_id):
        self.opta_id = opta_id
    
    def __str__(self):
        return str(self.opta_id)


def call_api(url: str, params=None):
    """Call the MLS API at the given url, and return the json data and status code.

    Positional arguments:
    url -- the url to call

    Keyword arguments:
    params -- a dict of the http query parameters
    """
    headers = {
        'user-agent': USER_AGENT,
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.5'
    }
    r = None
    if params is not None:
        r = requests.get(url, headers=headers, params=params)
    else:
        r = requests.get(url, headers=headers)
    if r.status_code != 200:
        message = f'{url}\n{params}\n{r.status_code}: {r.reason}'
        logging.error(message)
        msg.send(message)
        return None, r.status_code
    else:
        data = r.json()
        return data, r.status_code

@util.time_dec(False)
def main():
    params = {
        'match_game_id': 2261459,
        'include': ['club', 'player', 'player_match'],
        'order_by': ['-commentary_period', '-commentary_minute', '-commentary_second', '-commentary_timestamp', '-commentary_opta_id']
    }
    request_url = 'https://stats-api.mlssoccer.com/v1/commentaries'
    data, status = call_api(request_url, params)
    print(status)
    print(data)
