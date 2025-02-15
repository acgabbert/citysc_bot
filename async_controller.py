import argparse
import logging, logging.handlers
import asyncio
from datetime import datetime, timezone
import time

import discipline
import discord as msg
import injuries
import match_thread as thread
import mls_schedule
import mls_playwright
import widgets
from config import FEATURE_FLAGS, SUB, TEAMS as clubs

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
parser.add_argument('-s', '--sub', help='Subreddit; default = /r/u_citysc_bot')

class AsyncController:
    """Main controller class for scheduling and managing async tasks"""
    
    def __init__(self, subreddit: str):
        self.subreddit = subreddit
        self.running = True
        self.scheduler_tasks = []
        
    async def create_match_thread(self, opta_id: int, post: bool = True):
        """Create a match thread in an async context"""
        message = f'Posting match thread for {opta_id} on subreddit {self.subreddit}'
        root.info(message)
        msg.send(f'{msg.user}\n{message}')
        
        try:
            await thread.match_thread(opta_id, self.subreddit, post=post)
        except Exception as e:
            root.error(f"Error creating match thread: {str(e)}")
            msg.send(f"Error creating match thread for {opta_id}: {str(e)}")
    
    async def schedule_daily_tasks(self):
        """Schedule and manage daily tasks based on feature flags"""
        while self.running:
            now = datetime.now()
            next_run = now.replace(hour=1, minute=30, second=0, microsecond=0)
            if now >= next_run:
                next_run = next_run.replace(day=next_run.day + 1)
            
            delay = (next_run - now).total_seconds()
            await asyncio.sleep(delay)
            
            if FEATURE_FLAGS['enable_daily_setup']:
                await self.daily_setup()
            
            # Schedule other daily tasks
            tasks = []
            current_time = time.strftime('%H:%M')
            
            if FEATURE_FLAGS['enable_widgets'] and current_time == '00:45':
                tasks.append(mls_playwright.main())
            if FEATURE_FLAGS['enable_widgets'] and current_time == '01:00':
                tasks.append(widgets.main())
            if FEATURE_FLAGS['enable_injuries'] and current_time == '01:15':
                tasks.append(injuries.main())
            if FEATURE_FLAGS['enable_discipline'] and current_time == '01:15':
                tasks.append(discipline.main())
                
            if tasks:
                await asyncio.gather(*tasks)
    
    async def daily_setup(self):
        """Check for upcoming matches and schedule threads"""
        message = "Running daily setup..."
        root.info(message)
        msg.send(message)
        
        for team in clubs:
            try:
                # Get schedule data
                if team == 19202:  # CITY2
                    data = mls_schedule.get_schedule(team=team, comp='MLSNP')
                else:
                    data = mls_schedule.get_schedule(team=team, comp=None)
                
                # Check for upcoming matches
                match_id, match_time = mls_schedule.check_pre_match_sched(data)
                
                if match_id is not None:
                    match_time = datetime.fromtimestamp(match_time, tz=timezone.utc)
                    match_time = match_time.astimezone()
                    
                    msg.send(f'Match coming up: {match_id}, {match_time}')
                    
                    # Check if match is within next 24 hours
                    today = time.time() + 86400
                    if match_time.timestamp() < today and datetime.now().day == match_time.day:
                        # Schedule match thread for 30 mins before game
                        thread_time = match_time.timestamp() - 1800
                        
                        # Schedule the task
                        delay = thread_time - time.time()
                        if delay > 0:
                            self.scheduler_tasks.append(
                                asyncio.create_task(
                                    self.delayed_task(
                                        delay,
                                        self.create_match_thread,
                                        match_id,
                                        team != 19202  # Only post if not CITY2
                                    )
                                )
                            )
                            
                            match_time_str = time.strftime('%H:%M', time.localtime(thread_time))
                            message = f'Scheduled match thread for {match_time_str}. Team {team}, Opta ID {match_id}, Subreddit {self.subreddit}'
                            root.info(message)
                            msg.send(f'{msg.user}\n{message}')
                        
                        # Schedule pre-match thread if not CITY2
                        if datetime.now().hour < 4 and team != 19202:
                            pre_match_time = datetime.now().replace(hour=4, minute=0)
                            delay = pre_match_time.timestamp() - time.time()
                            
                            if delay > 0:
                                self.scheduler_tasks.append(
                                    asyncio.create_task(
                                        self.delayed_task(
                                            delay,
                                            thread.pre_match_thread,
                                            match_id,
                                            self.subreddit
                                        )
                                    )
                                )
                                
                                message = f'Scheduled pre-match thread for {pre_match_time.strftime("%H:%M")}. Team {team}, Opta ID {match_id}, Subreddit {self.subreddit}'
                                root.info(message)
                                msg.send(f'{msg.user}\n{message}')
                    
                    else:
                        message = f'No matches today for {team}.'
                        root.info(message)
                        msg.send(message)
            
            except Exception as e:
                root.error(f"Error in daily setup for team {team}: {str(e)}")
                msg.send(f"Error in daily setup for team {team}: {str(e)}")
    
    async def delayed_task(self, delay: float, coro, *args, **kwargs):
        """Helper to run a coroutine after a delay"""
        await asyncio.sleep(delay)
        await coro(*args, **kwargs)
    
    async def cleanup(self):
        """Clean up scheduled tasks"""
        for task in self.scheduler_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.scheduler_tasks, return_exceptions=True)
    
    async def run(self):
        """Main run loop"""
        message = f'Started controller at {time.time()}. Subreddit {self.subreddit}\n{str(FEATURE_FLAGS)}'
        root.info(message)
        msg.send(message)
        
        try:
            # Start daily task scheduler
            scheduler_task = asyncio.create_task(self.schedule_daily_tasks())
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(300)  # Sleep for 5 minutes
                
        except asyncio.CancelledError:
            self.running = False
            
        finally:
            scheduler_task.cancel()
            await self.cleanup()

async def main():
    args = parser.parse_args()
    subreddit = args.sub if args.sub else SUB
    if '/r/' not in subreddit:
        subreddit = f'/r/{subreddit}'
        
    controller = AsyncController(subreddit)
    
    try:
        await controller.run()
    except KeyboardInterrupt:
        controller.running = False
        root.error('Manual shutdown.')
    finally:
        await controller.cleanup()

if __name__ == '__main__':
    asyncio.run(main())