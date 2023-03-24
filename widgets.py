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
    return util.file_changed(filename)


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
        if w.shortName == widget_name:
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


def update_sidebar(text=None, subreddit='stlouiscitysc'):
    r = util.get_reddit()
    sidebar = r.subreddit(subreddit).wiki['config/sidebar']
    if not sidebar.may_revise:
        message = f'Error: authenticated user cannot edit {subreddit} sidebar.'
        msg.send(f'{msg.user}\n{message}')
        return None
    old_text = sidebar.content_md
    begin_split = '[comment]: # (start of bot content)\n\n'
    end_split = '[comment]: # (end of bot content)\n\n'
    before, content = old_text.split(begin_split)
    content, after = content.split(end_split)
    if text is None:
        # TODO read from files to get content (text) here???
        # only run this entire func if changed
        pass
    new_text = f'{before}{begin_split}{text}{end_split}{after}'
    sidebar.edit(new_text)
    return new_text


def main():
    pass


if __name__ == '__main__':
    markdown = upcoming()
    print(markdown)
    markdown = standings()
    print(markdown)
