import time
from datetime import datetime, timedelta
import schedule

import util
import match
import match_markdown as md
import match_thread as thread
import mls_schedule


def get_upcoming_matches(date_from=None, opta_id=17012):
    """Get upcoming matches from the local database."""
    if date_from is None:
        # check from +24h
        date_from = int(time.time()) + 86400
    # until +48h
    date_to = date_from + 86400
    sql = f'SELECT opta_id, time FROM match WHERE time > {date_from} AND time < {date_to}'
    if opta_id is not None:
        sql += f' AND (home = {opta_id} OR away = {opta_id})'
    matches = util.db_query(sql)
    if len(matches) > 0:
        for row in matches:
            id = row[0]
            t = row[1]
            match_obj = match.Match(id)
            #title, markdown = md.pre_match_thread(match_obj)
            t = time.strftime('%H:%M', time.localtime(t))
            print(f'Match coming up: {match_obj.opta_id}')
            schedule.every().day.at(t).do(pre_match_thread, opta_id=id, h_m=t)
    else:
        message = 'No upcoming matches.'
        print(message)
    return matches


def pre_match_thread(opta_id: int, h_m: str):
    """
    """
    thread.pre_match_thread(opta_id)
    t = datetime.strptime(h_m, '%H:%M')
    t -= timedelta(hours=1)
    # schedule the match thread for tomorrow at the same time, minus one hour
    schedule.every().day.at(t).do(match_thread, opta_id=opta_id)
    return schedule.CancelJob


def match_thread(opta_id: int):
    """
    """
    thread.match_thread(opta_id)
    return schedule.CancelJob


def main():
    schedule.every().day.at('04:00').do(mls_schedule.main)
    # within get_upcoming_matches, we will schedule pre-match threads
    # pre-match threads will in turn schedule match threads
    # and post-match threads are posted directly after match threads
    schedule.every().day.at('05:00').do(get_upcoming_matches)
    while True:
        schedule.run_pending()
        # while maintaining a match thread, we will be stuck in run_pending.
        # this is not a problem if only creating match threads for one team
        # however, if ever used for more than one team/game at a time, 
        # would need to find a different way to run things
        time.sleep(60)


if __name__ == '__main__':
    main()