import requests
import json
import logging

import discord as msg
import util

logging.basicConfig(filename='log/mls_api.log', format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
filename = 'assets/standings.json'
BASE_URL = 'https://sportapi.mlssoccer.com/api/'
schedule = 'https://sportapi.mlssoccer.com/api/matches?culture=en-us&'
standings = 'https://sportapi.mlssoccer.com/api/standings/live?isLive=true&'
commentary = 'https://stats-api.mlssoccer.com/v1/commentaries?'
mls = '&competitionId=98'
# format: YYYY-MM-DD
date_from = '&dateFrom='
date_to = '&dateTo='
season = '&seasonId='
match = '&match_game_id='
commentary_tail = '?&match_game_id=2261459&include=club&include=player&include=player_match&order_by=-commentary_period&order_by=-commentary_minute&order_by=-commentary_second&order_by=-commentary_timestamp&order_by=-commentary_opta_id&page=0&page_size=500'
'''
with open(filename, 'w') as f:
    for j in r.json():
        data.append(j)
    string = json.dumps(data, indent=4)
    f.write(string)

def get_data(url: str):
    r = requests.get(url)
    return r.json()
data = None
with open(filename, 'r') as f:
    data = json.load(f)
'''

def call_api(url):
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
