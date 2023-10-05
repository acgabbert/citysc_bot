import time
import argparse
import logging
import praw
import sys

import config
import match
import match_markdown as md
import util
import discord as msg

logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser(prog='match_thread.py', usage='%(prog)s [options]', description='')
parser.add_argument('--pre', action='store_true', help='Create a pre-match thread')
parser.add_argument('--post', action='store_true', help='Create a pre-match thread')
parser.add_argument('-i', '--id', help='Match Opta ID')
parser.add_argument('-s', '--sub', help='Subreddit')

test_sub = config.TEST_SUB
prod_sub = 'stlouiscitysc'
threads_json = config.THREADS_JSON


def submit_thread(subreddit: str, title: str, text: str, mod: bool=False, new: bool=False, unsticky=None):
    """Submit a thread to the provided subreddit. """
    reddit = util.get_reddit()
    subreddit = reddit.subreddit(subreddit)
    # TODO implement PRAW exception handling? 
    thread = subreddit.submit(title, selftext=text, send_replies=False)
    if mod:
        time.sleep(10)
        thread_mod = thread.mod
        try:
            if new:
                thread_mod.suggested_sort(sort='new')
            thread_mod.sticky()
            if unsticky is not None:
                if type(unsticky) is str:
                    unsticky = praw.models.Submission(reddit=reddit, id=unsticky)
                if type(unsticky) is praw.models.Submission:
                    unsticky_mod = unsticky.mod
                    unsticky_mod.sticky(state=False)
        except Exception as e:
            message = f'Error in moderation clause. Thread {thread.id}'
            if unsticky is not None:
                message += f', unsticky {unsticky.id}'
            message += f'\n{str(e)}'
            logger.error(message)
            msg.send(message)
    return thread


def comment(pre_thread, text):
    reddit = util.get_reddit()
    comment = None
    if type(pre_thread) is str:
        pre_thread = praw.models.Submission(reddit=reddit, id=pre_thread)
    if type(pre_thread) is praw.models.Submission:
        comment = pre_thread.reply(text)
        time.sleep(10)
        comment_mod = comment.mod
        try:
            comment_mod.distinguish(sticky=True)
        except Exception as e:
            message = (
                f'Error in moderation clause. Comment {comment.id}\n'
                f'{str(e)}'
            )
            logger.error(message)
            msg.send(message)
    return comment


def pre_match_thread(opta_id, sub=prod_sub):
    """This function posts a pre-match/matchday thread
    Returns a PRAW submission object representing the pre-match thread"""
    # get a match object
    match_obj = match.Match(opta_id)
    match_obj = match.get_prematch_data(match_obj)
    # get post details for the match object
    title, markdown = md.pre_match_thread(match_obj)
    if '/r/' in sub:
        sub = sub[3:]
    # TODO implement PRAW exception handling here or in submit_thread
    thread = submit_thread(sub, title, markdown, new=True, mod=True)
    msg.send(f'{msg.user} Pre-match thread posted! https://www.reddit.com/r/{sub}/comments/{thread.id_from_url(thread.shortlink)}')
    # keep track of threads
    data = util.read_json(threads_json)
    if str(opta_id) not in data.keys():
        # add it as an empty dict
        data[str(opta_id)] = {}
        data[str(opta_id)]['slug'] = match_obj.slug
    data[str(opta_id)]['pre'] = thread.id_from_url(thread.shortlink)
    util.write_json(data, threads_json)
    return thread


def match_thread(opta_id, sub=prod_sub, pre_thread=None, thread=None, post=True):
    """This function posts a match thread. It maintains and updates the thread
    until the game is finished.
    
    pre_thread is the pre-match thread PRAW object so that it can be
    un-stickied
    
    thread is the current match thread PRAW object so that it can be maintained
    if still active"""
    # get a match object
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)

    # get reddit ids of any threads that may already exist for this match
    data = util.read_json(threads_json)
    if str(opta_id) not in data.keys():
        # add it as an empty dict
        data[str(opta_id)] = {}
        data[str(opta_id)]['slug'] = match_obj.slug
    else:
        gm = data[str(opta_id)]
        if 'pre' in gm.keys():
            pre_thread = gm['pre']
        if 'match' in gm.keys():
            thread = gm['match']

    if thread is None:
        title, markdown = md.match_thread(match_obj)
        if '/r/' in sub:
            sub = sub[3:]
        thread = submit_thread(sub, title, markdown, mod=True, new=True, unsticky=pre_thread)
        data[str(opta_id)]['match'] = thread.id_from_url(thread.shortlink)
        util.write_json(data, threads_json)
        if pre_thread is not None:
            text = f'[Continue the discussion in the match thread.](https://www.reddit.com/r/{sub}/comments/{thread.id_from_url(thread.shortlink)})'
            comment(pre_thread, text)
        msg.send(f'{msg.user} Match thread posted! https://www.reddit.com/r/{sub}/comments/{thread.id_from_url(thread.shortlink)}')
    else:
        # thread already exists in the json
        reddit = util.get_reddit()
        thread = praw.models.Submission(reddit=reddit, id=thread)
        msg.send(f'Found existing match thread')
    
    while not match_obj.is_final:
        time.sleep(60)
        before = time.time()
        try:
            match_obj = match.get_match_update(match_obj)
        except Exception as e:
            message = (
                f'Error while getting match update.\n'
                f'{str(e)}\n'
                f'Continuing while loop.'
            )
            logger.error(message)
            msg.send(f'{msg.user} {message}')
            continue
        after = time.time()
        logger.info(f'Match update took {round(after-before, 2)} secs')
        _, markdown = md.match_thread(match_obj)
        try:
            thread.edit(markdown)
        except Exception as e:
            message = (
                f'Error while editing match thread.\n'
                f'{str(e)}\n'
                f'Continuing while loop.'
            )
            logger.error(message)
            msg.send(f'{msg.user} {message}')
            continue
        
        logger.debug(f'Successfully updated {match_obj.opta_id} at minute {match_obj.minute}')
        if match_obj.is_final and post:
            # post a post-match thread before exiting the loop
            post_match_thread(opta_id, sub, thread)


def post_match_thread(opta_id, sub=prod_sub, thread=None):
    """This function posts a post-match thread"""
    # get reddit ids of any threads that may already exist for this match
    data = util.read_json(threads_json)
    if str(opta_id) in data.keys():
        gm = data[str(opta_id)]
        if 'match' in gm.keys():
            thread = gm['match']

    if '/r/' in sub:
        sub = sub[3:]

    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    title, markdown = md.post_match_thread(match_obj)
    post_thread = submit_thread(sub, title, markdown, mod=True, unsticky=thread)
    if thread is not None:
        text = f'[Continue the discussion in the post-match thread.](https://www.reddit.com/r/{sub}/comments/{post_thread.id_from_url(post_thread.shortlink)})'
        comment(thread, text)
    msg.send(f'{msg.user} Post-match thread posted! https://www.reddit.com/r/{sub}/comments/{post_thread.id_from_url(post_thread.shortlink)}')
    data = util.read_json(threads_json)
    if str(opta_id) not in data.keys():
        data[str(opta_id)] = {}
        data[str(opta_id)]['slug'] = match_obj.slug
    data[str(opta_id)]['post'] = post_thread.id_from_url(post_thread.shortlink)
    util.write_json(data, threads_json)
    return


@util.time_dec(False)
def main():
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    args = parser.parse_args()
    id = args.id
    sub = args.sub
    if id:
        if args.pre:
            # pre-match thread
            if sub:
                pre_match_thread(id, sub)
            else:
                pre_match_thread(id)
        elif args.post:
            # post-match thread
            if sub:
                post_match_thread(id, sub)
            else:
                post_match_thread(id)
        else:
            # match thread
            if sub:
                match_thread(id, sub)
            else:
                match_thread(id)


if __name__ == '__main__':
    main()
