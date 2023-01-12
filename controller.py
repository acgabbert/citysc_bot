import time
import logging, logging.handlers
import sys
from datetime import datetime, timedelta
import schedule

import util
import discord as msg
import match
import match_thread as thread
import mls_schedule

fh = logging.handlers.RotatingFileHandler('log/debug.log', maxBytes=1000000, backupCount=10)
fh.setLevel(logging.DEBUG)
fh2 = logging.handlers.RotatingFileHandler('log/controller.log', maxBytes=1000000, backupCount=5)
fh2.setLevel(logging.INFO)
er = logging.handlers.RotatingFileHandler('log/error.log', maxBytes=2000000, backupCount=2)
er.setLevel(logging.WARNING)
fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
fh2.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
er.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(fh)
root.addHandler(fh2)
root.addHandler(er)


def get_upcoming_matches(date_from=None, opta_id=17012):
    """Get upcoming matches from the local sqlite database."""
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
            root.info(f'Match coming up: {match_obj.opta_id}')
            schedule.every().day.at(t).do(pre_match_thread, opta_id=id, t=t)
            msg.send(f'{msg.user}\nScheduled pre-match thread for {t}')
    else:
        root.info('No upcoming matches.')
    return matches


def pre_match_thread(opta_id: int, t: str):
    """
    """
    thread.pre_match_thread(opta_id)
    t = datetime.strptime(t, '%H:%M')
    t -= timedelta(hours=1)
    # schedule the match thread for tomorrow at the same time, minus one hour
    msg.send(f'{msg.user}\nScheduled match thread for {t}')
    schedule.every().day.at(t).do(match_thread, opta_id=opta_id)
    return schedule.CancelJob


def match_thread(opta_id: int):
    """
    """
    # this will run until the game is final
    thread.match_thread(opta_id)
    return schedule.CancelJob


def all_jobs():
    message = f'Currently scheduled jobs:\n{schedule.get_jobs()}'
    root.info(message)
    #msg.send(f'{msg.user}\n{message}')
    return schedule.get_jobs()


@util.time_dec(True)
def main():
    root.info(f'Started {__name__} at {time.time()}')
    # update the schedule every day
    schedule.every().day.at('04:00').do(mls_schedule.main)
    # within get_upcoming_matches, we will schedule pre-match threads
    # pre-match threads will in turn schedule match threads
    # and post-match threads are posted directly after match threads
    schedule.every().day.at('05:00').do(get_upcoming_matches)
    schedule.every().day.at('05:30').do(all_jobs)
    running = True
    while running:
        try:
            schedule.run_pending()
            # while maintaining a match thread, we will be stuck in run_pending.
            # this is not a problem if only creating match threads for one team
            # however, if ever used for more than one team/game at a time, 
            # would need to find a different way to run things
            time.sleep(60)
        except KeyboardInterrupt:
            root.error(f'Manual shutdown.')
            running = False


if __name__ == '__main__':
    main()