import requests
import json

import private_config as priv

token = priv.DISCORD_TOKEN
url = priv.MLS_BOT_WEBHOOK
user = f'<@{priv.DISCORD_BOTADMINID}>'
HEADERS = {
    "User-Agent":"MLS BOT/v0.1",
    "Content-Type":"application/json"
}

def send(message, url=priv.MLS_BOT_WEBHOOK, headers=HEADERS):
    content = json.dumps({'content': message})
    r = requests.post(url, headers=headers, data=content)
    return r.content

if __name__ == '__main__':
    send('mls bot test')
