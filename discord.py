import aiohttp
import json
import logging
import requests

import config as conf

logger = logging.getLogger(__name__)

token = conf.DISCORD_TOKEN
url = conf.MLS_BOT_WEBHOOK
user = f'<@{conf.DISCORD_BOTADMINID}>'
HEADERS = {
    "User-Agent":"citysc_bot/v1.0",
    "Content-Type":"application/json"
}

def send(message, tag=False, url=conf.MLS_BOT_WEBHOOK, headers=HEADERS):
    message = f'[{conf.HOST}] {f"{user}: " if tag else ""}{message}'
    content = json.dumps({'content': message})
    try:
        r = requests.post(url, headers=headers, data=content, timeout=10)
        return r.content
    except requests.RequestException as e:
        logger.error(f"Discord webhook send failed: {e}")
        return None

async def async_send(message, tag=False, url=conf.MLS_BOT_WEBHOOK, headers=HEADERS):
    message = f'[{conf.HOST}] {f"{user}: " if tag else ""}{message}'
    content = json.dumps({'content': message})
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=content, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return await r.read()
    except Exception as e:
        logger.error(f"Discord async webhook send failed: {e}")
        return None

if __name__ == '__main__':
    send('mls bot test')
