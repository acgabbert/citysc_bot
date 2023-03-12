import logging
import subprocess
import praw

import discord as msg
from match import Match, get_match_data
import mls_schedule
from standings import get_clubs
import util
import widget_markdown as md

STL_CITY = 17012

def get_upcoming(opta_id):
    """Returns a list of the next 5 upcoming matches
    Sorted in date order"""
    data = mls_schedule.get_schedule(team=opta_id)
    ids = mls_schedule.get_upcoming_matches(data)
    matches = []
    for id in ids:
        m = Match(id)
        get_match_data(m)
        matches.append(m)
    matches.sort()
    return matches


@util.time_dec(False)
def upcoming(opta_id=STL_CITY):
    """Get upcoming matches and write them to file in markdown format
    Also, update the widget"""
    matches = get_upcoming(opta_id)
    markdown = md.schedule(matches)
    changed = write_markdown(markdown, 'markdown/upcoming.md')
    if changed:
        name = 'Upcoming Matches'
        update_widget(name, markdown)
    return markdown


@util.time_dec(False)
def standings():
    """Get western conference standings and write them to file in markdown
    format
    Also, update the widget"""
    clubs = get_clubs()
    markdown = md.western_conference(clubs)
    changed = write_markdown(markdown, 'markdown/western_conference.md')
    if changed:
        name = 'Western Conference Standings'
        update_widget(name, markdown)
    return markdown


def write_markdown(markdown: str, filename: str):
    """Write a file to markdown, and check if its content has changed."""
    with open(filename, 'w') as f:
        f.write(markdown)
    changes = subprocess.run(f'git status {filename}', capture_output=True, shell=True, text=True).stdout
    logging.debug(changes)
    if 'Changes not staged' in changes:
        message = f'{filename} changed.'
        logging.info(message)
        msg.send(f'{msg.user}\n{message}')
        return True
    else:
        message = f'No changes to {filename}.'
        logging.info(message)
        msg.send(message)
        return False


def get_widgets(reddit, subreddit) -> list[praw.models.Widget]:
    """Returns a list of the widgets in a subreddit's sidebar"""
    if reddit is None:
        reddit = util.get_reddit()
    sub = reddit.subreddit(subreddit)
    return sub.widgets.sidebar


def update_widget(widget_name, text, subreddit='stlouiscitysc'):
    r = util.get_reddit()
    sidebar = get_widgets(r, subreddit)
    updated = False
    for w in sidebar:
        print(w.shortName)
        if w.shortName == widget_name:
            print('matched')
            try:
                mod = w.mod
                mod.update(text=text)
                updated = True
                break
            except Exception as e:
                message = (
                    f'Error while updating {widget_name} widget.\n'
                    f'{str(e)}\n'
                )
                msg.send(f'{msg.user}\n{message}')
    return updated


def update_sidebar():
    pass


def main():
    pass


if __name__ == '__main__':
    markdown = upcoming()
    print(markdown)
    markdown = standings()
    print(markdown)
