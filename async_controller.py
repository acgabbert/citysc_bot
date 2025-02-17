import argparse
import asyncio
import logging, logging.handlers
import time

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job
from datetime import datetime, timezone

import discipline
import discord as msg
import injuries
import match_thread as thread
import mls_schedule
import mls_playwright
import widgets
from config import FEATURE_FLAGS, SUB, TEAMS

# Configure logging
fh = logging.handlers.RotatingFileHandler('log/debug.log', maxBytes=1000000, backupCount=10)
fh.setLevel(logging.DEBUG)
fh2 = logging.handlers.RotatingFileHandler('log/controller.log', maxBytes=1000000, backupCount=5)
fh2.setLevel(logging.INFO)
er = logging.handlers.RotatingFileHandler('log/error.log', maxBytes=2000000, backupCount=2)
er.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
fh2.setFormatter(formatter)
er.setFormatter(formatter)

root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(fh)
root.addHandler(fh2)
root.addHandler(er)

parser = argparse.ArgumentParser(prog='async_controller.py', usage='%(prog)s [options]', description='')
parser.add_argument('-s', '--sub', help=f'Subreddit; default = {SUB}')

class AsyncController:
    """Main controller class for scheduling and managing async tasks"""
    
    def __init__(self, subreddit: str):
        self.subreddit = subreddit
        self.scheduler = AsyncIOScheduler()
        
        # Add job listeners for logging
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
    
    def _job_executed(self, event: JobEvent):
        """Log successful job execution"""
        job: Job = self.scheduler.get_job(event.job_id)
        message = f'Job {job.name} executed successfully'
        root.info(message)
        msg.send(message)
    
    def _job_error(self, event: JobEvent):
        """Log job execution errors"""
        job: Job = self.scheduler.get_job(event.job_id)
        message = f'Error in job {job.name}: {str(event.exception)}'
        root.error(message)
        msg.send(message, tag=True)
        
    async def create_match_thread(self, opta_id: int, post: bool = True):
        """Create a match thread in an async context"""
        message = f'Posting match thread for {opta_id} on subreddit {self.subreddit}'
        root.info(message)
        msg.send(message, tag=True)
        
        try:
            await thread.match_thread(opta_id, self.subreddit, post=post)
        except Exception as e:
            root.error(f"Error creating match thread: {str(e)}")
            msg.send(f"Error creating match thread for {opta_id}: {str(e)}")
    
    async def daily_setup(self):
        """Check for upcoming matches and schedule threads"""
        message = "Running daily setup..."
        root.info(message)
        msg.send(message)
        
        for team in TEAMS:
            try:
                # Get schedule data
                if team == 19202:  # CITY2
                    data = mls_schedule.get_schedule(team=team, comp='MLSNP')
                else:
                    data = mls_schedule.get_schedule(team=team, comp=None)
                
                # Check for upcoming matches
                match_id, match_time = mls_schedule.check_pre_match_sched(data)
                
                if match_id is not None:
                    match_datetime = datetime.fromtimestamp(match_time)
                    msg.send(f'Match coming up: {match_id}, {match_datetime}')
                    
                    # Check if match is within next 24 hours
                    today = time.time() + 86400
                    if match_time < today and datetime.now().day == match_datetime.day:
                        # Schedule match thread for 30 mins before game
                        thread_time = datetime.fromtimestamp(match_time - 1800)
                        
                        self.scheduler.add_job(
                            self.create_match_thread,
                            'date',
                            run_date=thread_time,
                            args=[match_id, team != 19202],  # Only post if not CITY2
                            name=f'match_thread_{match_id}',
                            replace_existing=True
                        )
                        
                        message = f'Scheduled match thread for {thread_time.strftime("%H:%M")}. Team {team}, Opta ID {match_id}'
                        root.info(message)
                        msg.send(message)
                        
                        # Schedule pre-match thread if not CITY2
                        if datetime.now().hour < 4 and team != 19202:
                            pre_match_time = datetime.now().replace(hour=4, minute=0)
                            
                            self.scheduler.add_job(
                                thread.pre_match_thread,
                                'date',
                                run_date=pre_match_time,
                                args=[match_id, self.subreddit],
                                name=f'pre_match_thread_{match_id}',
                                replace_existing=True
                            )
                            
                            message = f'Scheduled pre-match thread for {pre_match_time.strftime("%H:%M")}. Team {team}, Opta ID {match_id}'
                            root.info(message)
                            msg.send(message)
                    
                    else:
                        message = f'No matches today for {team}.'
                        root.info(message)
                        msg.send(message)
            
            except Exception as e:
                root.error(f"Error in daily setup for team {team}: {str(e)}")
                msg.send(f"Error in daily setup for team {team}: {str(e)}")
    
    def setup_jobs(self):
        """Setup all scheduled jobs based on feature flags"""
        if FEATURE_FLAGS['enable_widgets']:
            self.scheduler.add_job(
                mls_playwright.main,
                CronTrigger(hour=0, minute=45),
                name='mls_playwright'
            )
            self.scheduler.add_job(
                widgets.main,
                CronTrigger(hour=1, minute=0),
                name='widgets'
            )
            
        if FEATURE_FLAGS['enable_injuries']:
            self.scheduler.add_job(
                injuries.main,
                CronTrigger(hour=1, minute=15),
                name='injuries'
            )
            
        if FEATURE_FLAGS['enable_discipline']:
            self.scheduler.add_job(
                discipline.main,
                CronTrigger(hour=1, minute=15),
                name='discipline'
            )
            
        if FEATURE_FLAGS['enable_daily_setup']:
            self.scheduler.add_job(
                self.daily_setup,
                CronTrigger(hour=1, minute=30),
                name='daily_setup'
            )
    
    async def run(self):
        """Main run loop"""
        message = f'Started controller at {time.time()}. Subreddit {self.subreddit}\n{str(FEATURE_FLAGS)}'
        root.info(message)
        msg.send(message, tag=True)
        
        try:
            self.setup_jobs()
            self.scheduler.start()
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(300)
                
        except (KeyboardInterrupt, asyncio.CancelledError):
            message = "Shutting down scheduler..."
            root.info(message)
            msg.send(message)
            
        finally:
            self.scheduler.shutdown()

async def main():
    args = parser.parse_args()
    subreddit = args.sub if args.sub else SUB
    if '/r/' not in subreddit:
        subreddit = f'/r/{subreddit}'
        
    controller = AsyncController(subreddit)
    await controller.run()

if __name__ == '__main__':
    asyncio.run(main())
