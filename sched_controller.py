import time
import sched
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

scheduler = sched.scheduler(time.time, time.sleep)

"""List of club opta IDs that we want to make threads for"""
clubs = [17012, 3500, 5431]

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


def daily_setup():
    global scheduler
    for team in clubs:
        data = mls_schedule.get_schedule(team=team, comp=None)
        # TODO refactor check_pre_match to check for any match in the next 48 hours
        id, t = mls_schedule.check_pre_match_sched(data)
        if id is not None:
            # there is a match in less than 48 hours
            today = time.time() + 86400
            tomo = today + 86400
            if t < today:
                # schedule a match thread for 1h before gametime
                t -= 3600
                scheduler.enterabs(t, 1, Main.create_match_thread, argument=(id,))
                t = time.strftime('%H:%M', time.localtime(t))
                message = f'Scheduled match thread for {t}. Team {team}, Opta ID {id}'
                root.info(message)
                msg.send(f'{msg.user}\n{message}')
            if t < tomo:
                # schedule a pre-match thread for 24h before gametime
                t -= 86400
                scheduler.enterabs(t, 1, thread.pre_match_thread, argument=(id,))
                t = time.strftime('%H:%M', time.localtime(t))
                message = f'Scheduled pre-match thread for {t}. Team {team}, Opta ID {id}'
                root.info(message)
                msg.send(f'{msg.user}\n{message}')
        else:
            message = f'No upcoming matches for {team}.'
            root.info(message)
            msg.send(message)
    q = scheduler.queue
    if len(q) > 0:
        message = 'Currently scheduled jobs:\n'
        for job in q:
            message += f'- {repr(job)}\n'
        root.info(message)
        msg.send(message)
    scheduler.run()


def main():
    root.info(f'Started {__name__} at {time.time()}')
    daily_setup()
    schedule.every().day.at('05:10').do(widgets.upcoming)
    schedule.every().day.at('05:15').do(widgets.standings)
    schedule.every().day.at('05:30').do(daily_setup)
    running = True
    while running:
        try:
            schedule.run_pending()
            time.sleep(300)
        except KeyboardInterrupt:
            root.error('Manual shutdown.')
            running = False

if __name__ == '__main__':
    main()
