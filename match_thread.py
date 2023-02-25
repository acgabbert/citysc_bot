import time
import argparse
import logging
import json

import config
import match
import match_markdown as md
import reddit_interactor as reddit
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


def pre_match_thread(opta_id, sub=test_sub):
    """This function posts a pre-match/matchday thread"""
    match_obj = match.Match(opta_id)
    match_obj = match.get_prematch_data(match_obj)
    title, markdown = md.pre_match_thread(match_obj)
    response, thing_id = reddit.submit(sub, title, markdown)
    if response.status_code == 200:
        message = f'Posted {title} on {sub} with thing_id {thing_id}'
        logger.info(message)
        msg.send(f'{msg.user} {message}')
    else:
        message = f'Error posting {title} on {sub}.\n{response.status_code}'
        logger.error(message)
        msg.send(f'{msg.user} {message}')
        return
    data = {}
    with open(threads_json, 'r') as f:
        data = json.loads(f.read())
    if opta_id not in data.keys():
        data[opta_id] = {}
    data[opta_id]['pre'] = thing_id
    with open(threads_json, 'w') as f:
        f.write(json.dumps(data))
    return thing_id


def match_thread(opta_id, sub=test_sub):
    """This function posts a match thread.
    It maintains the thread until the game is finished
    in order to present up-to-date match events and stats"""
    # initialize an empty Match object with the opta_id
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    
    try:
        # need to check for a thing_id here, in wherever we decide to keep track of them
        thing_id = None
        #thing_id = util.db_query(sql)[0][0]
    except IndexError:
        thing_id = None
    if thing_id is None:
        # no thread exists, post a new one
        title, markdown = md.match_thread(match_obj)
        response, thing_id = reddit.submit(sub, title, markdown, thing_id)
        reddit.set_sort_order(thing_id)
        if response.status_code == 200 and response.json()['success']:
            message = f'Posted {title} on {sub}'
            logger.info(message)
            msg.send(f'{msg.user} {message}')
        else:
            message = (
                f'Error posting {title} on {sub}.\n'
                f'{response.status_code} - {response.reason}\n'
                f'{response.json()["jquery"][10][3][0]}'
            )
            logger.error(message)
            msg.send(f'{msg.user} {message}')
            # TODO or could raise an exception here
            return

        data = {}
        with open(threads_json, 'r') as f:
            data = json.loads(f.read())
        if opta_id not in data.keys():
            data[opta_id] = {}
        else:
            # un-sticky pre-match thread
            try:
                reddit.sticky(data[opta_id]['pre'], False)
            except KeyError:
                pass
        data[opta_id]['match'] = thing_id
        with open(threads_json, 'w') as f:
            f.write(json.dumps(data))
    
    while not match_obj.is_final:
        time.sleep(60)
        match_obj = match.get_all_data(match_obj)
        title, markdown = md.match_thread(match_obj)
        # edit existing thread with thing_id
        try:
            response, _ = reddit.submit(sub, title, markdown, thing_id)
        except Exception as e:
            message = (
                f'Error while posting match thread.\n'
                f'{str(e)}\n'
                f'Continuing while loop.'
            )
            logger.error(message)
            msg.send(f'{msg.user} {message}')
            continue
        if not response.json()['success']:
            message = (
                f'Error posting {title} on {sub}.\n'
                f'{response.status_code} - {response.reason}\n'
                f'{response.json()["jquery"][10][3][0]}'
            )
            logger.error(message)
            msg.send(f'{msg.user} {message}')
            continue
        logger.debug(f'Successfully updated {match_obj.opta_id} at minute {match_obj.minute}')
        if match_obj.is_final:
            # post a post-match thread before exiting the loop
            post_match_thread(match_obj.opta_id, thing_id, sub)


def post_match_thread(opta_id, match_thing_id=None, sub=test_sub):
    """This function posts a post-match thread"""
    # initialize an empty Match object with the opta_id
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    title, markdown = md.post_match_thread(match_obj)
    response, thing_id = reddit.submit(sub, title, markdown)
    if match_thing_id is not None:
        # somehow gonna hve to get the full link text
        text = f'[Post-match thread has been posted.](https://www.reddit.com{sub}/comments/{thing_id})'
        reddit.comment(match_thing_id, text)
    if response.status_code == 200 and response.json()['success']:
        message = f'Posted {title} on {sub}'
        logger.info(message)
        msg.send(f'{msg.user} {message}')
    else:
        message = (
            f'Error posting {title} on {sub}.\n'
            f'{response.status_code} - {response.reason}\n'
            f'{response.json()["jquery"][10][3][0]}'
        )
        logger.error(message)
        msg.send(f'{msg.user} {message}')
        # TODO or could raise an exception here
        return
    data = {}
    with open(threads_json, 'r') as f:
        data = json.loads(f.read())
    if opta_id not in data.keys():
        data[opta_id] = {}
    else:
        # un-sticky match thread
        try:
            reddit.sticky(data[opta_id]['match'], False)
        except KeyError:
            pass
    data[opta_id]['post'] = thing_id
    with open(threads_json, 'w') as f:
        f.write(json.dumps(data))


@util.time_dec(False)
def main():
    args = parser.parse_args()
    id = args.id
    sub = args.sub
    if sub and '/r/' not in sub:
        sub = f'/r/{sub}'
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
                post_match_thread(id, sub=sub)
        else:
            # match thread
            if sub:
                match_thread(id, sub)
            else:
                match_thread(id)


if __name__ == '__main__':
    main()
