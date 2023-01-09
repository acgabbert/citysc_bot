import time
import argparse

import match
import match_markdown as md
import util

parser = argparse.ArgumentParser(prog='match_thread.py', usage='%(prog)s [options]', description='')
parser.add_argument('--pre', action='store_true', help='Create a pre-match thread')
parser.add_argument('--post', action='store_true', help='Create a pre-match thread')
parser.add_argument('-i', '--id', help='Match Opta ID')


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

def match_thread(opta_id):
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    # check if thing_id already exists in the database
    # post a thread and populate its thing_id to match_obj and the database
    sql = f'SELECT thing_id FROM match WHERE opta_id = {opta_id}'
    thing_id = util.db_query(sql)[0][0]
    if thing_id is not None:
        # a match thread exists
        pass
    else:
        # post a thread
        # populate its thing_id to match_obj and the database
        pass
    while not match_obj.is_final:
        match_obj = match.get_stats(match_obj)
        match_obj = match.get_feed(match_obj)
        # edit existing thread
        time.sleep(60)
    if match_obj.is_final:
        # post a post-match thread
        pass


@util.time_dec(False)
def main():
    args = parser.parse_args()
    if args.id:
        if args.pre:
            # pre-match thread
            pass
        elif args.post:
            # post-match thread
            pass
        else:
            # match thread
            #match_thread(id)
            pass
    print(args.id)
    if args.pre:
        print('prematch')
    if args.post:
        print('postmatch')
    #matches = get_upcoming_matches(date_from=1674627098)
    #print(matches)


if __name__ == '__main__':
    main()
