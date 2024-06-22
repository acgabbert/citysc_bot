import aiohttp
import asyncio
import logging

import discord as msg
import util
from mls_api import MlsObject

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
HEADERS = {
    'user-agent': USER_AGENT,
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.5',
    'sec-fetch-mode': 'cors'
}
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

async def call_api(url: str, params=None):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url, params=params) as response:
            status = response.status
            reason = response.reason
            if status != 200:
                message = f'{url}\n{params}\n{status}: {reason}'
                logging.error(message)
                msg.send(message)
                return None, status
            else:
                data = await response.json()
                return data, status

@util.time_dec(False)
async def main():
    params = {
        'match_game_id': 2261459,
        'include': ['club', 'player', 'player_match'],
        'order_by': ['-commentary_period', '-commentary_minute', '-commentary_second', '-commentary_timestamp', '-commentary_opta_id']
    }
    request_url = 'https://stats-api.mlssoccer.com/v1/commentaries'
    data, status = await call_api(request_url, params)
    print(status)
    print(data)


if __name__ == '__main__':
    asyncio.run(main())