import argparse
import asyncio
from datetime import datetime
from PIL import Image

import discord as msg
from reddit_client import RedditClient
from config import SUB

parser = argparse.ArgumentParser(prog='widgets.py', usage='%(prog)s [options]', description='')
parser.add_argument('-s', '--sub', help='Subreddit')

"""
Image Widget names:
"Western Conference PNG"
"This Week PNG"
"Next Week PNG"
"""


async def update_image_widget(name, subreddit='stlouiscitysc'):
    now = datetime.now()
    widget_name = f'{name} PNG'
    image_path = f'png/{name}-{now.month}-{now.day}.png'
    try:
        im = Image.open(image_path)
    except Exception:
        msg.send(f'Failed to update widget {image_path}.')
        return False
    size = im.size # format (width, height) tuple
    async with RedditClient() as client:
        return await client.update_image_widget(widget_name, image_path, size, subreddit)


async def main():
    args = parser.parse_args()
    sub: str = args.sub or SUB
    for name in ['Western Conference', 'This Week', 'Next Week']:
        await update_image_widget(name, sub)


if __name__ == '__main__':
    asyncio.run(main())
