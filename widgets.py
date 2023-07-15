import praw

import discord as msg
from match import Match, get_match_data
import mls_schedule
from standings import get_clubs
import util
import widget_markdown as md

STL_CITY = 17012

UPCOMING_FILE = 'markdown/upcoming.md'
STANDINGS_FILE = 'markdown/western_conference.md'

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
    changed = write_markdown(markdown, UPCOMING_FILE)
    if changed:
        name = 'Upcoming Matches'
        update_text_widget(name, markdown)
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
        update_text_widget(name, markdown)
    return changed


def write_markdown(markdown: str, filename: str):
    """Write a file to markdown, and check if its content has changed."""
    with open(filename, 'w') as f:
        f.write(markdown)
    return util.file_changed(filename)


def read_markdown(filename: str):
    with open(filename, 'r') as f:
        return f.read()


def sidebar_edit(text: str):
    if text[:2] == '##':
        return text[1:]
    else:
        return text


def get_widgets(reddit, subreddit) -> list[praw.models.Widget]:
    """Returns a list of the widgets in a subreddit's sidebar"""
    if reddit is None:
        reddit = util.get_reddit()
    sub = reddit.subreddit(subreddit)
    return sub.widgets.sidebar


def update_text_widget(widget_name, text, subreddit='stlouiscitysc'):
    if text[0] == '#':
        # remove first line of text
        text = '\n'.join(text.split('\n')[1:])
    print(text)
    r = util.get_reddit()
    sidebar = get_widgets(r, subreddit)
    updated = False
    for w in sidebar:
        print(w.shortName)
        print(isinstance(w, praw.models.TextArea))
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


def update_image_widget(widget_name, image_path, subreddit='stlouiscitysc'):
    updated = False

    return updated


def update_sidebar(text=None, subreddit='stlouiscitysc'):
    r = util.get_reddit()
    sidebar = r.subreddit(subreddit).wiki['config/sidebar']
    if not sidebar.may_revise:
        message = f'Error: authenticated user cannot edit {subreddit} sidebar.'
        msg.send(f'{msg.user}\n{message}')
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
    sidebar.edit(new_text)
    msg.send(f'{msg.user} Edited sidebar!')
    return new_text


def main():
    u_changed = upcoming()
    s_changed = standings()
    if u_changed or s_changed:
        # update sidebar here
        update_sidebar()


if __name__ == '__main__':
    main()
