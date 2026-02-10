import argparse
import asyncio
import logging
import asyncpraw, asyncpraw.models
import sys
import time
from typing import Optional, Union

import config
import match_markdown_sportec as md
from api_client import MLSApiClient
from match_sportec import Match
from thread_manager import MatchThreads, ThreadManager
import util
import discord as msg
from reddit_client import RedditClient

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(prog='match_thread.py', usage='%(prog)s [options]', description='')
parser.add_argument('--pre', action='store_true', help='Create a pre-match thread')
parser.add_argument('--post', action='store_true', help='Create a post-match thread')
parser.add_argument('--no-post', action='store_true', help='Create a match thread with no post-match thread')
parser.add_argument('-i', '--id', help='Match Sportec ID')
parser.add_argument('-s', '--sub', help='Subreddit')

test_sub = config.TEST_SUB
prod_sub = config.SUB
file_manager = ThreadManager(config.THREADS_JSON)

async def pre_match_thread(sportec_id: str, sub: str = prod_sub):
    """Post a pre-match/matchday thread.
    
    Args:
        sportec_id: Sportec ID for the match
        sub: Subreddit to post to
        
    Returns:
        The created pre-match thread
    """
    if '/r/' in sub:
        sub = sub.split('/r/')[1]
    # get a match object
    match_obj = await Match.create(sportec_id)

    # get post details for the match object
    title, markdown = md.pre_match_thread(match_obj)
    
    async with RedditClient() as reddit:
        thread: asyncpraw.models.Submission = await reddit.submit_thread(sub, title, markdown, new=True, mod=True)
        await msg.async_send(f'Pre-match thread posted! https://www.reddit.com/r/{sub}/comments/{thread.id_from_url(thread.shortlink)}', tag=True)
    
        # keep track of threads
        threads = file_manager.get_threads(str(sportec_id))
        if not threads:
            threads = MatchThreads(slug=match_obj.slug)
        
        threads.pre = thread.id_from_url(thread.shortlink)
        await file_manager.add_threads(sportec_id, threads)

        return thread


async def match_thread(
    sportec_id: str,
    sub: str = prod_sub,
    pre_thread: Optional[Union[str, asyncpraw.models.Submission]] = None,
    thread: Optional[Union[str, asyncpraw.models.Submission]] = None,
    post: bool = True
) -> None:
    """Post and maintain a match thread.
    
    Args:
        sportec_id: Sportec ID for the match
        sub: Subreddit to post to
        pre_thread: Pre-match thread to unsticky
        thread: Existing match thread to update
        post: Whether to create a post-match thread when done
    """
    async with MLSApiClient() as api_client:
        # get a match object
        match_obj = await Match.create(sportec_id, client=api_client)

        # get reddit ids of any threads that may already exist for this match
        threads = file_manager.get_threads(sportec_id)
        if threads is None:
            threads = MatchThreads(slug=match_obj.slug)

        post_thread = None

        if pre_thread is None and threads.pre:
            pre_thread = threads.pre
        if thread is None and threads.match:
            thread = threads.match
        if threads.post:
            post_thread = threads.post

        async with RedditClient() as reddit:
            if thread is None:
                title, markdown = md.match_thread(match_obj)
                if '/r/' in sub:
                    sub = sub.split('/r/')[1]
                thread = await reddit.submit_thread(
                    sub, title, markdown,
                    mod=True, new=True, unsticky=pre_thread
                )

                threads.match = thread.id_from_url(thread.shortlink)
                await file_manager.add_threads(sportec_id, threads)

                if pre_thread is not None:
                    text = f'[Continue the discussion in the match thread.](https://www.reddit.com/r/{sub}/comments/{thread.id_from_url(thread.shortlink)})'
                    await reddit.add_comment(pre_thread, text)
                await msg.async_send(f'Match thread posted! https://www.reddit.com/r/{sub}/comments/{thread.id_from_url(thread.shortlink)}', tag=True)

                if not post:
                    await msg.async_send(f'No post-match thread for {thread.id_from_url(thread.shortlink)}')
            else:
                # thread already exists in the json
                thread = await reddit.get_thread(thread)
                await thread.load()
                await msg.async_send(f'Found existing match thread')

            while True:
                before = time.time()
                try:
                    await match_obj.refresh(client=api_client)
                    after = time.time()
                    logger.info(f'Match update took {round(after-before, 2)} secs')
                    _, markdown = md.match_thread(match_obj)
                    try:
                        await reddit.edit_thread(thread, markdown)
                        logger.debug(f'Successfully updated {match_obj.sportec_id} at minute {match_obj.minute_display}')
                    except Exception as e:
                        message = (
                            f'Error while editing match thread.\n'
                            f'{str(e)}\n'
                            f'Continuing while loop.'
                        )
                        logger.error(message)
                        await msg.async_send(message, tag=True)

                except Exception as e:
                    message = (
                        f'Error while getting match update.\n'
                        f'{str(e)}\n'
                        f'Continuing while loop.'
                    )
                    logger.error(message)
                    await msg.async_send(message, tag=True)

                if match_obj.is_final():
                    await msg.async_send('Match is finished, final update made', tag=True)
                    if post and not post_thread:
                        # post a post-match thread before exiting the loop
                        await post_match_thread(sportec_id, sub, thread)
                    elif not post:
                        message = f'No post-match thread for {sportec_id}'
                        await msg.async_send(message)
                    elif post_thread:
                        message = f'Found post-match thread for {sportec_id}. Skipping post-match thread.'
                        await msg.async_send(message, tag=True)
                    break
                await asyncio.sleep(60)


async def post_match_thread(
    sportec_id: str,
    sub: str = prod_sub,
    thread: Optional[Union[str, asyncpraw.models.Submission]] = None
) -> None:
    """Post a post-match thread.
    
    Args:
        sportec_id: Sportec ID for the match  
        sub: Subreddit to post to
        thread: Match thread to unsticky
    """
    # get reddit ids of any threads that may already exist for this match
    threads = file_manager.get_threads(sportec_id)
    if thread is None and threads and threads.match:
        thread = threads.match

    if '/r/' in sub:
        sub = sub.split('/r/')[1]

    match_obj = await Match.create(sportec_id)
    title, markdown = md.post_match_thread(match_obj)
    async with RedditClient() as reddit:
        post_thread_obj: asyncpraw.models.Submission = await reddit.submit_thread(
            sub, title, markdown,
            mod=True, unsticky=thread
        )

        if thread is not None:
            text = f'[Continue the discussion in the post-match thread.](https://www.reddit.com/r/{sub}/comments/{post_thread_obj.id_from_url(post_thread_obj.shortlink)})'
            await reddit.add_comment(thread, text)
        
        await msg.async_send(f'Post-match thread posted! https://www.reddit.com/r/{sub}/comments/{post_thread_obj.id_from_url(post_thread_obj.shortlink)}', tag=True)

        if threads is None:
            threads = MatchThreads(slug=match_obj.slug)
        threads.post = post_thread_obj.id_from_url(post_thread_obj.shortlink)
        await file_manager.add_threads(sportec_id, threads)

@util.time_dec(False)
async def main():
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    args = parser.parse_args()
    id: Optional[str] = args.id
    sub: Optional[str] = args.sub
    post: bool = not args.no_post
    if id:
        if args.pre:
            # pre-match thread
            if sub:
                await pre_match_thread(id, sub)
            else:
                await pre_match_thread(id)
        elif args.post:
            # post-match thread
            if sub:
                await post_match_thread(id, sub)
            else:
                await post_match_thread(id)
        else:
            # match thread
            if sub:
                await match_thread(id, sub, post=post)
            else:
                await match_thread(id, post=post)


if __name__ == '__main__':
    asyncio.run(main())
