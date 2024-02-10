import argparse
import time
import sched
import logging, logging.handlers
from datetime import datetime
import schedule
from multiprocessing import Process

import discord as msg
import injuries
import match_thread as thread
import mls_schedule
import mls_selenium
import widgets

fh = logging.handlers.RotatingFileHandler('log/debug.log', maxBytes=1000000, backupCount=10)
fh.setLevel(logging.DEBUG)
fh2 = logging.handlers.RotatingFileHandler('log/controller.log', maxBytes=1000000, backupCount=5)
fh2.setLevel(logging.INFO)
er = logging.handlers.RotatingFileHandler('log/error.log', maxBytes=2000000, backupCount=2)
er.setLevel(logging.ERROR)
fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
fh2.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
er.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(fh)
root.addHandler(fh2)
root.addHandler(er)

parser = argparse.ArgumentParser(prog='sched_controller.py', usage='%(prog)s [options]', description='')
parser.add_argument('-s', '--sub', help='Subreddit; default = /r/citysc_bot_test')

scheduler = sched.scheduler(time.time, time.sleep)

"""List of club opta IDs that we want to make threads for
- 17012: St. Louis City SC
- 19202: St. Louis City SC 2
"""
clubs = [17012, 19202]

class Main:
    """Use this class to start a match thread in a separate process, 
    in order to not stop controller.main while we wait for the match
    thread to complete."""
    # TODO maybe move this class to match_thread?
    @staticmethod
    def create_match_thread(opta_id, sub, post=True):
        message = f'Posting match thread for {opta_id} on subreddit {sub}'
        root.info(message)
        msg.send(f'{msg.user}\n{message}')
        p = Process(target=thread.match_thread, args=(opta_id,sub), kwargs={'post': post}, daemon=True)
        p.start()


def daily_setup(sub):
    """This function runs daily and is the core component of the bot.
    It will first check, for each team, if there is a match in the next 48 hours.
    If so, it will schedule a pre-match or match thread, whichever is appropriate.
    Then, it will hold in `scheduler.run()` until all threads are posted.
    """
    global scheduler
    for team in clubs:
        data = None
        if team == 19202:
            data = mls_schedule.get_schedule(team=team, comp='MLSNP')
        else:
            data = mls_schedule.get_schedule(team=team, comp=None)
        # TODO refactor check_pre_match to check for any match in the next 48 hours
        id, t = mls_schedule.check_pre_match_sched(data)
        if id is not None:
            # there is a match in less than 48 hours
            today = time.time() + 86400
            # TODO and clause makes it so this only will work if run day of
            if t < today and datetime.now().day == datetime.fromtimestamp(t).day:
                # there is a match today (next 24 hours)
                # schedule a match thread for 30m before gametime
                t -= 1800
                if team == 19202:
                    scheduler.enterabs(t, 1, Main.create_match_thread, argument=(id,sub,False))
                else:
                    scheduler.enterabs(t, 1, Main.create_match_thread, argument=(id,sub))
                match_time = time.strftime('%H:%M', time.localtime(t))
                message = f'Scheduled match thread for {match_time}. Team {team}, Opta ID {id}, Subreddit {sub}'
                root.info(message)
                msg.send(f'{msg.user}\n{message}')
                # schedule a matchday/pre-match thread for 4:00am
                # right now static checking for if the team is CITY2 to skip matchday threads
                if datetime.now().hour < 4 and team != 19202:
                    t = int(datetime.now().replace(hour=4, minute=0).timestamp())
                    scheduler.enterabs(t, 1, thread.pre_match_thread, argument=(id, sub))
                    prematch_time = time.strftime('%H:%M', time.localtime(t))
                    message = f'Scheduled pre-match thread for {prematch_time}. Team {team}, Opta ID {id}, Subreddit {sub}'
                    root.info(message)
                    msg.send(f'{msg.user}\n{message}')
            else:
                message = f'No matches today for {team}.'
                root.info(message)
                msg.send(message)
    q = scheduler.queue
    if len(q) > 0:
        message = 'Currently scheduled jobs:\n'
        for job in q:
            message += f'- {repr(job)}\n'
        root.info(message)
        msg.send(message)
    else:
        message = 'No scheduled jobs.'
        root.info(message)
        msg.send(message)
    scheduler.run()
    message = 'Sending control back to main.'
    root.info(message)
    msg.send(message)


def main(sub):
    message = f'Started {__name__} at {time.time()}. Subreddit {sub}'
    root.info(message)
    msg.send(message)
    daily_setup(sub)
    schedule.every().day.at('00:45').do(mls_selenium.main)
    schedule.every().day.at('01:00').do(widgets.main)
    schedule.every().day.at('01:15').do(injuries.main)
    schedule.every().day.at('01:30').do(daily_setup, sub)
    running = True
    while running:
        try:
            schedule.run_pending()
            time.sleep(300)
        except KeyboardInterrupt:
            root.error('Manual shutdown.')
            running = False

if __name__ == '__main__':
    args = parser.parse_args()
    sub = args.sub
    if sub:
        if '/r/' not in sub:
            sub = f'/r/{sub}'
    else:
        sub = '/r/u_citysc_bot'
    main(sub)
