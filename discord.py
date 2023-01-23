import requests
import json

import config as conf

token = conf.DISCORD_TOKEN
url = conf.MLS_BOT_WEBHOOK
user = f'<@{conf.DISCORD_BOTADMINID}>'
HEADERS = {
    "User-Agent":"MLS BOT/v0.1",
    "Content-Type":"application/json"
}

def send(message, url=conf.MLS_BOT_WEBHOOK, headers=HEADERS):
    message = f'[{conf.HOST}] {message}'
    content = json.dumps({'content': message})
    r = requests.post(url, headers=headers, data=content)
    return r.content

if __name__ == '__main__':
    send('mls bot test')
