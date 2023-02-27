import time
import argparse
import logging
import json
import praw

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
threads_json = config.THREADS_JSON

def get_reddit():
    reddit = praw.Reddit(
        client_id=config.CLIENT_ID,
        client_secret=config.SECRET_TOKEN,
        password=config.PASSWORD,
        user_agent=config.USER_AGENT_STR,
        username=config.USERNAME
    )
    reddit.validate_on_submit = True
    return reddit


def get_threads():
    with open(threads_json, 'r') as f:
        data = json.loads(f.read())
        return data


def write_threads(data: dict):
    with open(threads_json, 'w') as f:
        f.write(json.dumps(data))
    return


def submit_thread(subreddit: str, title: str, text: str, mod: bool=False, unsticky=None):
    """Submit a thread to the provided subreddit. """
    reddit = get_reddit()
    subreddit = reddit.subreddit(subreddit)
    # TODO implement PRAW exception handling? 
    thread = subreddit.submit(title, selftext=text, send_replies=False)
    if mod:
        thread_mod = thread.mod
        try:
            thread_mod.suggested_sort(sort='new')
            thread_mod.sticky()
            if unsticky is not None:
                if type(unsticky) is str:
                    unsticky = praw.models.Submission(reddit=reddit, id=unsticky)
                if type(unsticky) is praw.models.Submission:
                    unsticky_mod = unsticky.mod
                    unsticky_mod.sticky(state=False)
        except:
            logger.error('Error in moderation clause.')
    return thread


def pre_match_thread(opta_id, sub=test_sub):
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
    thread = submit_thread(sub, title, markdown, True)
    # keep track of threads
    data = get_threads()
    if str(opta_id) not in data.keys():
        # add it as an empty dict
        data[str(opta_id)] = {}
    data[str(opta_id)]['pre'] = thread.id_from_url(thread.shortlink)
    with open(threads_json, 'w') as f:
        f.write(json.dumps(data))
    return thread


def match_thread(opta_id, sub=test_sub, pre_thread=None, thread=None):
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
    data = get_threads()
    if str(opta_id) not in data.keys():
        # add it as an empty dict
        data[str(opta_id)] = {}
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
        thread = submit_thread(sub, title, markdown, True, pre_thread)
    
        data[str(opta_id)]['match'] = thread.id_from_url(thread.shortlink)
        write_threads(data)
    else:
        # thread already exists in the json
        reddit = get_reddit()
        thread = praw.models.Submission(reddit=reddit, id=thread)
    
    while not match_obj.is_final:
        time.sleep(60)
        match_obj = match.get_match_update(match_obj)
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
        if match_obj.is_final:
            # post a post-match thread before exiting the loop
            post_match_thread(opta_id, sub, thread)


def post_match_thread(opta_id, sub=test_sub, pre_thread=None):
    """This function posts a post-match thread"""
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    title, markdown = md.post_match_thread(match_obj)
    post_thread = submit_thread(sub, title, markdown, True, pre_thread)
    if pre_thread is not None:
        text = f'[Post-match thread has been posted.](https://www.reddit.com/r/{sub}/comments/{post_thread.id_from_url(post_thread.shortlink)})'
    data = get_threads()
    if str(opta_id) not in data.keys():
        data[str(opta_id)] = {}
    data[str(opta_id)]['post'] = post_thread.id_from_url(post_thread)
    write_threads(data)
    return


@util.time_dec(False)
def main():
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
