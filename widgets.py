import logging
import subprocess

import discord as msg
from match import Match, get_match_data
import mls_schedule
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


def upcoming(opta_id):
    matches = get_upcoming(STL_CITY)
    markdown = md.schedule(matches)
    return markdown


def standings():
    """Returns """


def write_markdown(markdown: str, filename: str):
    with open(filename, 'w') as f:
        f.write(markdown)
    changes = subprocess.run(f'git status {filename}', capture_output=True, shell=True, text=True).stdout
    logging.debug(changes)
    if 'Changes not staged' in changes:
        message = f'{filename} changed.'
        logging.info(message)
        msg.send(f'{msg.user}\n{message}')
    else:
        message = f'No changes to {filename}.'
        logging.info(message)
        msg.send(message)


if __name__ == '__main__':
    markdown = upcoming()
    print(markdown)
