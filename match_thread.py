import argparse
import asyncio
import logging
import asyncpraw, asyncpraw.models
import sys
import time
from typing import Optional, Union

import config
import match_markdown as md
from api_client import MLSApiClient
from match import Match
from thread_manager import MatchThreads, ThreadManager
import util
import discord as msg
from reddit_client import RedditClient, subreddit_name

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

# Minute from which MATCH_UPDATE_INTERVAL_LATE applies
LATE_MATCH_MINUTE = 80
# A failed post-match thread is retried this many times in total, this many seconds apart
POST_MATCH_ATTEMPTS = 3
POST_MATCH_RETRY_DELAY = 60


def match_thread_max_hours() -> float:
    """Hours after kickoff to stop updating a match thread that never goes final
    (e.g. a long weather delay or a status the bot doesn't recognize)."""
    return getattr(config, 'MATCH_THREAD_MAX_HOURS', 5)


def update_interval(match_obj: Match) -> float:
    """Seconds to wait between match thread updates. Late in the match
    (and in extra time) this is MATCH_UPDATE_INTERVAL_LATE, if set."""
    interval = getattr(config, 'MATCH_UPDATE_INTERVAL', 60)
    late_interval = getattr(config, 'MATCH_UPDATE_INTERVAL_LATE', interval)
    try:
        # minute_of_play looks like "33" or "90+4"
        minute = int(str(match_obj.minute_display).split('+')[0])
    except ValueError:
        return interval
    return late_interval if minute >= LATE_MATCH_MINUTE else interval

async def pre_match_thread(sportec_id: str, sub: str = prod_sub):
    """Post a pre-match/matchday thread.
    
    Args:
        sportec_id: Sportec ID for the match
        sub: Subreddit to post to
        
    Returns:
        The created pre-match thread
    """
    sub = subreddit_name(sub)
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
    sub = subreddit_name(sub)
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
                await msg.async_send('Found existing match thread')

            deadline = match_obj.get_kickoff_timestamp() + match_thread_max_hours() * 3600
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
                        await post_match_thread_with_retry(sportec_id, sub, thread)
                    elif not post:
                        message = f'No post-match thread for {sportec_id}'
                        await msg.async_send(message)
                    elif post_thread:
                        message = f'Found post-match thread for {sportec_id}. Skipping post-match thread.'
                        await msg.async_send(message, tag=True)
                    break
                if match_obj.is_abandoned():
                    status = match_obj.data.match_base.match_information.match_status
                    await msg.async_send(
                        f'Match {sportec_id} is {status}. Stopped match thread updates; '
                        f'no post-match thread posted.',
                        tag=True
                    )
                    break
                if time.time() > deadline:
                    await msg.async_send(
                        f'Match {sportec_id} still not final {match_thread_max_hours()}h after kickoff. '
                        f'Stopped match thread updates. If it has finished, post the post-match thread with '
                        f'`python match_thread.py -i {sportec_id} --post`.',
                        tag=True
                    )
                    break
                await asyncio.sleep(update_interval(match_obj))


async def post_match_thread_with_retry(
    sportec_id: str,
    sub: str = prod_sub,
    thread: Optional[Union[str, asyncpraw.models.Submission]] = None
) -> bool:
    """Post a post-match thread, retrying on failure. Returns True once one exists.
    Never posts a second one: each attempt first checks threads.json, which
    post_match_thread() updates as soon as the thread is submitted."""
    for attempt in range(1, POST_MATCH_ATTEMPTS + 1):
        threads = file_manager.get_threads(sportec_id)
        if threads and threads.post:
            return True
        try:
            await post_match_thread(sportec_id, sub, thread)
            return True
        except Exception as e:
            logger.exception(f'Post-match thread attempt {attempt}/{POST_MATCH_ATTEMPTS} for {sportec_id} failed')
            if attempt == POST_MATCH_ATTEMPTS:
                await msg.async_send(
                    f'Giving up on post-match thread for {sportec_id} after {attempt} attempts: {str(e)}\n'
                    f'Post it with `python match_thread.py -i {sportec_id} --post`.',
                    tag=True
                )
                return False
            await msg.async_send(
                f'Post-match thread attempt {attempt}/{POST_MATCH_ATTEMPTS} for {sportec_id} failed: {str(e)}. '
                f'Retrying in {POST_MATCH_RETRY_DELAY}s.',
                tag=True
            )
            await asyncio.sleep(POST_MATCH_RETRY_DELAY)
    return False


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

    sub = subreddit_name(sub)

    match_obj = await Match.create(sportec_id)
    title, markdown = md.post_match_thread(match_obj)
    async with RedditClient() as reddit:
        post_thread_obj: asyncpraw.models.Submission = await reddit.submit_thread(
            sub, title, markdown,
            mod=True, unsticky=thread
        )

        # Save the thread first so a retry after a later failure won't post another
        if threads is None:
            threads = MatchThreads(slug=match_obj.slug)
        threads.post = post_thread_obj.id_from_url(post_thread_obj.shortlink)
        await file_manager.add_threads(sportec_id, threads)

        if thread is not None:
            text = f'[Continue the discussion in the post-match thread.](https://www.reddit.com/r/{sub}/comments/{threads.post})'
            await reddit.add_comment(thread, text)

        await msg.async_send(f'Post-match thread posted! https://www.reddit.com/r/{sub}/comments/{threads.post}', tag=True)

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
