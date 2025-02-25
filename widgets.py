import argparse
import asyncio
import asyncpraw.models
import asyncpraw.models
from datetime import datetime
from PIL import Image
from typing import Optional

import discord as msg
from match import Match
import mls_schedule
from reddit_client import RedditClient
import util
import widget_markdown as md
from config import SUB, TEST_SUB
from match import Match
from standings import get_clubs

STL_CITY = 17012

UPCOMING_FILE = 'markdown/upcoming.md'
STANDINGS_FILE = 'markdown/western_conference.md'

parser = argparse.ArgumentParser(prog='widgets.py', usage='%(prog)s [options]', description='')
parser.add_argument('-s', '--sub', help='Subreddit')

"""
Image Widget names:
"Western Conference PNG"
"This Week PNG"
"Next Week PNG"
"""

def get_upcoming(opta_id):
    """Returns a list of the next 5 upcoming matches
    Sorted in date order"""
    data = mls_schedule.get_schedule(team=opta_id, comp=None)
    ids = mls_schedule.get_upcoming_matches(data)
    matches = []
    for id in ids:
        m = Match.create_prematch(id)
        matches.append(m)
    matches.sort()
    return matches


@util.time_dec(False)
def upcoming(opta_id=STL_CITY):
    """Get upcoming matches and write them to file in markdown format
    Also, update the widget"""
    matches = get_upcoming(opta_id)
    markdown = md.schedule(matches)
    changed = write_markdown(markdown, UPCOMING_FILE)
    if changed:
        name = 'Upcoming Matches'
        update_widget(name, markdown)
    return changed


@util.time_dec(False)
def standings():
    """Get western conference standings and write them to file in markdown
    format
    Also, update the widget"""
    clubs = get_clubs()
    markdown = md.western_conference(clubs)
    changed = write_markdown(markdown, STANDINGS_FILE)
    if changed:
        name = 'Western Conference Standings'
        update_widget(name, markdown)
    return changed


def write_markdown(markdown: str, filename: str):
    """Write a file to markdown, and check if its content has changed."""
    with open(filename, 'w') as f:
        f.write(markdown)
    return util.file_changed(filename)


def read_markdown(filename: str):
    with open(filename, 'r') as f:
        retval = f.read()
        if retval[0] == '#':
            # remove first line of text
            retval = '\n'.join(retval.split('\n')[1:])
        return retval


def sidebar_edit(text: str):
    if text[:2] == '##':
        return text[1:]
    else:
        return text


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


def update_sidebar(text=None, subreddit='stlouiscitysc'):
    r = util.get_reddit()
    sidebar = r.subreddit(subreddit).wiki['config/sidebar']
    if not sidebar.may_revise:
        message = f'Error: authenticated user cannot edit {subreddit} sidebar.'
        msg.send(message, tag=True)
        return None
    old_text = sidebar.content_md
    begin_split = '[comment]: # (start of bot content)'
    end_split = '[comment]: # (end of bot content)'
    before, content = old_text.split(begin_split)
    content, after = content.split(end_split)
    if text is None:
        # TODO sidebar_edit call is probably no longer needed
        upcoming = sidebar_edit(read_markdown(UPCOMING_FILE))
        western_conf = sidebar_edit(read_markdown(STANDINGS_FILE))
        text = f'{upcoming}\n{western_conf}\n'
    new_text = f'{before}{begin_split}\n\n{text}{end_split}\n\n{after}'
    sidebar.edit(content=new_text)
    msg.send('Edited sidebar!')
    return new_text


async def main():
    args = parser.parse_args()
    sub: Optional[str] = args.sub
    #u_changed = upcoming()
    #s_changed = standings()
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
    #if u_changed or s_changed:
        # update sidebar here
        #update_sidebar()


if __name__ == '__main__':
    asyncio.run(main())
