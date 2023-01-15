import time
import logging, logging.handlers
from datetime import datetime, timedelta
import schedule
from multiprocessing import Process

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


class Main:
    @staticmethod
    def create_match_thread(opta_id):
        message = f'Posting match thread for {opta_id}'
        root.info(message)
        msg.send(f'{msg.user}\n{message}')
        p = Process(target=thread.match_thread, args=(opta_id,), daemon=True)
        p.start()


def get_next_match(date_from=None, opta_id=17012):
    """Get upcoming matches."""
    data = mls_schedule.get_schedule(team=opta_id, comp=None)
    id, t = mls_schedule.check_pre_match(data, date_from)
    if id is not None:
        message = f'Match coming up: {id}'
        root.info(message)
        msg.send(message)
        t = time.strftime('%H:%M', time.localtime(t))
        schedule.every().day.at(t).do(pre_match_thread, opta_id=id, t=t)
        message = f'Scheduled pre-match thread for {t}'
        root.info(message)
        msg.send(f'{msg.user}\n{message}')
    else:
        root.info('No upcoming matches.')
    return data


def pre_match_thread(opta_id: int, t: str):
    """
    """
    thread.pre_match_thread(opta_id)
    t = datetime.strptime(t, '%H:%M')
    t -= timedelta(hours=1)
    # schedule the match thread for tomorrow at the same time, minus one hour
    message = f'Posted pre-match thread for {opta_id}\nScheduled match thread for {t}'
    root.info(message)
    msg.send(f'{msg.user}\n{message}')
    schedule.every().day.at(t).do(match_thread, opta_id=opta_id)
    # once complete, cancel the job (i.e. only run once)
    return schedule.CancelJob


def match_thread(opta_id: int):
    """
    """
    Main.create_match_thread(opta_id)
    #message = f'Posting match thread for {opta_id}'
    #root.info(message)
    #msg.send(f'{msg.user}\n{message}')
    # this will run until the game is final
    #thread.match_thread(opta_id)
    # Process class initialization needs to be in a __main__ block
    #p = Process(target=thread.match_thread, args=(opta_id,))
    #p.start()

    # once complete, cancel the job (i.e. only run once)
    return schedule.CancelJob


def log_all_jobs():
    jobs = schedule.get_jobs()
    message = f'Currently scheduled jobs:\n{jobs}'
    root.info(message)
    msg.send(f'{message}')
    return jobs


@util.time_dec(True)
def main():
    root.info(f'Started {__name__} at {time.time()}')
    # on first run, check the schedule and get upcoming matches
    mls_schedule.main()
    get_next_match()
    # within get_upcoming_matches, we will schedule pre-match threads
    # pre-match threads will in turn schedule match threads
    # and post-match threads are posted directly after match threads
    # TODO write scheduled jobs to database to persist in case of failure
    schedule.every().day.at('05:00').do(get_next_match)
    schedule.every().day.at('05:30').do(log_all_jobs)
    running = True
    while running:
        try:
            schedule.run_pending()
            # while maintaining a match thread, I think we will be stuck in 
            # run_pending. this is not a problem if only creating match threads
            # for one team. however, if ever used for more than one team/game 
            # at a time, would need to find a different way to run things
            time.sleep(60)
        except KeyboardInterrupt:
            root.error(f'Manual shutdown.')
            running = False


if __name__ == '__main__':
    main()
