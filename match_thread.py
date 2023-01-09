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


@util.time_dec(False)
def main():
    matches = get_upcoming_matches(date_from=1674627098)
    print(matches)


if __name__ == '__main__':
    main()
