import argparse
import asyncio
import asyncpraw.models
from datetime import datetime
from PIL import Image
from typing import Optional

import discord as msg
from reddit_client import RedditClient
import util
from config import SUB

parser = argparse.ArgumentParser(prog='widgets.py', usage='%(prog)s [options]', description='')
parser.add_argument('-s', '--sub', help='Subreddit')

"""
Image Widget names:
"Western Conference PNG"
"This Week PNG"
"Next Week PNG"
"""


async def get_sidebar_widgets(reddit, subreddit) -> asyncpraw.models.SubredditWidgets:
    """Returns a list of the widgets in a subreddit's sidebar"""
    if reddit is None:
        reddit = util.get_reddit()
    sub = await reddit.subreddit(subreddit)
    return sub.widgets


async def get_image_data(widget, image_path, size):
    image_url = await widget.mod.upload_image(image_path)
    image_data = [{'width': size[0], 'height': size[1], 'url': image_url, 'linkUrl': ''}]
    return image_data


async def update_widget(widget_name, data, subreddit='stlouiscitysc'):
    # TODO refactor this with the new client!
    r = util.get_reddit()
    widget_obj = await get_sidebar_widgets(r, subreddit)
    updated = False
    async for w in widget_obj.sidebar():
        if w.shortName == widget_name:
            try:
                mod: asyncpraw.models.WidgetModeration = w.mod
                if isinstance(data, str):
                    await mod.update(text=data)
                else:
                    image_data = await get_image_data(widget_obj, data[0], data[1])
                    await mod.update(data=image_data)
                updated = True
                msg.send(f'Updated {widget_name} widget!')
                break
            except Exception as e:
                message = (
                    f'Error while updating {widget_name} widget.\n'
                    f'{str(e)}\n'
                )
                msg.send(message, tag=True)
    await r.close()
    return updated


async def update_image_widget(name, subreddit='stlouiscitysc'):
    now = datetime.now()
    widget_name = f'{name} PNG'
    image_path = f'png/{name}-{now.month}-{now.day}.png'
    try:
        im = Image.open(image_path)
    except:
        msg.send(f'Failed to update widget {image_path}.')
        return False
    size = im.size # format (width, height) tuple
    async with RedditClient() as client:
        return await client.update_image_widget(widget_name, image_path, size, subreddit)


async def main():
    args = parser.parse_args()
    sub: Optional[str] = args.sub
    if sub:
        print(f'updating widget for sub {sub}')
        await update_image_widget('Western Conference', sub)
    else:
        await update_image_widget('Western Conference', SUB)
    if sub:
        await update_image_widget('This Week', sub)
    else:
        await update_image_widget('This Week', SUB)
    if sub:
        await update_image_widget('Next Week', sub)
    else:
        await update_image_widget('Next Week', SUB)


if __name__ == '__main__':
    asyncio.run(main())
