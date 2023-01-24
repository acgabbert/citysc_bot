import time
import logging, logging.handlers
from datetime import datetime, timedelta
import schedule
from multiprocessing import Process

import util
import discord as msg
import widgets
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
    """Use this class to start a match thread in a separate process, 
    in order to not stop controller.main while we wait for the match
    thread to complete."""
    # TODO maybe move this class to match_thread?
    @staticmethod
    def create_match_thread(opta_id):
        message = f'Posting match thread for {opta_id}'
        root.info(message)
        msg.send(f'{msg.user}\n{message}')
        p = Process(target=thread.match_thread, args=(opta_id,), daemon=True)
        p.start()

@util.time_dec(True)
def get_next_match(opta_id, date_from=None):
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

@util.time_dec(True)
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

@util.time_dec(True)
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
    message = 'Currently scheduled jobs:\n'
    for job in jobs:
        message += '- ' + repr(job) + '\n'
    root.info(message)
    msg.send(f'{message}')
    return jobs


@util.time_dec(True)
def main():
    root.info(f'Started {__name__} at {time.time()}')
    # on first run, check the schedule and get upcoming matches
    get_next_match(17012)
    get_next_match(596)
    # within get_upcoming_matches, we will schedule pre-match threads
    # pre-match threads will in turn schedule match threads
    # and post-match threads are posted directly after match threads
    # TODO write scheduled jobs to a file to persist in case of failure
    schedule.every().day.at('05:00').do(get_next_match, 17012)
    # USMNT
    schedule.every().day.at('05:05').do(get_next_match, 596)
    schedule.every().day.at('05:10').do(widgets.upcoming)
    schedule.every().day.at('05:15').do(widgets.standings)
    schedule.every().day.at('05:30').do(log_all_jobs)
    log_all_jobs()
    running = True
    while running:
        try:
            schedule.run_pending()
            time.sleep(60)
        except KeyboardInterrupt:
            root.error(f'Manual shutdown.')
            running = False


if __name__ == '__main__':
    main()
