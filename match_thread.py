import time
import argparse

import config
import match
import match_markdown as md
import reddit_interactor as reddit
import util

parser = argparse.ArgumentParser(prog='match_thread.py', usage='%(prog)s [options]', description='')
parser.add_argument('--pre', action='store_true', help='Create a pre-match thread')
parser.add_argument('--post', action='store_true', help='Create a pre-match thread')
parser.add_argument('-i', '--id', help='Match Opta ID')

subreddit = config.TEST_SUB


def get_upcoming_matches(date_from=None, opta_id=None):
    """Get upcoming matches from the local database."""
    if date_from is None:
        date_from = int(time.time()) + 86400
    date_to = date_from + 86400
    sql = f'SELECT * FROM match WHERE time > {date_from} AND time < {date_to}'
    if opta_id is not None:
        sql += f' AND (home = {opta_id} OR away = {opta_id})'
    matches = util.db_query(sql)
    if len(matches) > 0:
        for row in matches:
            id = row[0]
            match_obj = match.Match(id)
            title, markdown = md.pre_match_thread(match_obj)
            print(f'Match coming up: {match_obj.opta_id}; {title}')
    return matches


def pre_match_thread(opta_id):
    global subreddit
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    title, markdown = md.pre_match_thread(match_obj)
    _, thing_id = reddit.submit(subreddit, title, markdown)
    return thing_id


def match_thread(opta_id):
    global subreddit
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    # check if thing_id already exists in the database
    # post a thread and populate its thing_id to match_obj and the database
    sql = f'SELECT thing_id FROM match WHERE opta_id = {opta_id}'
    try:
        thing_id = util.db_query(sql)[0][0]
    except IndexError:
        # match does not exist at all in database
        thing_id = None
    if thing_id is None:
        # no thread exists, post a new one
        title, markdown = md.match_thread(match_obj)
        _, thing_id = reddit.submit(config.TEST_SUB, title, markdown, thing_id)
        # populate its thing_id to match_obj and the database
        sql = f'UPDATE match SET thing_id="{thing_id}" WHERE opta_id = {opta_id}'
        util.db_query(sql)
    
    while not match_obj.is_final:
        time.sleep(60)
        match_obj = match.get_stats(match_obj)
        match_obj = match.get_feed(match_obj)
        title, markdown = md.match_thread(match_obj)
        # edit existing thread with thing_id
        reddit.submit(subreddit, title, markdown, thing_id)
        # update the database?
    if match_obj.is_final:
        # post a post-match thread
        pass


@util.time_dec(False)
def main():
    args = parser.parse_args()
    id = args.id
    if args.id:
        if args.pre:
            # pre-match thread
            pre_match_thread(id)
        elif args.post:
            # post-match thread
            pass
        else:
            # match thread
            match_thread(id)
    #matches = get_upcoming_matches(date_from=1674627098)
    #print(matches)


if __name__ == '__main__':
    main()
