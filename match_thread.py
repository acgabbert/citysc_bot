import time

import match
import match_markdown as md
import util


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
    while not match_obj.is_final:
        match_obj = match.get_stats(match_obj)
        match_obj = match.get_feed(match_obj)
        # edit existing thread
        time.sleep(60)


@util.time_dec(False)
def main():
    matches = get_upcoming_matches(date_from=1674627098)
    print(matches)


if __name__ == '__main__':
    main()
