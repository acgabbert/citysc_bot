import time
import argparse
import logging

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

subreddit = config.TEST_SUB


def pre_match_thread(opta_id):
    global subreddit
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    title, markdown = md.pre_match_thread(match_obj)
    response, thing_id = reddit.submit(subreddit, title, markdown)
    if response.status_code == 200:
        logger.info(f'Posted {title} on {subreddit} with thing_id {thing_id}')
    else:
        logger.error(f'Error posting {title} on {subreddit}.\n{response.status_code}')
    return thing_id


def match_thread(opta_id):
    global subreddit
    # initialize an empty Match object with the opta_id
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    
    # TODO use something other than a database to track current threads
    try:
        # need to check for a thing_id here, in wherever we decide to keep track of them
        thing_id = None
        #thing_id = util.db_query(sql)[0][0]
    except IndexError:
        thing_id = None
    if thing_id is None:
        # no thread exists, post a new one
        title, markdown = md.match_thread(match_obj)
        response, thing_id = reddit.submit(config.TEST_SUB, title, markdown, thing_id)
        reddit.set_sort_order(thing_id)
        if response.status_code == 200 and response.json()['success']:
            # TODO use something other than a database to track current threads
            logger.info(f'Posted {title} on {subreddit}')
        else:
            message = (
                f'Error posting {title} on {subreddit}.\n'
                f'{response.status_code} - {response.reason}\n'
                f'{response.json()["jquery"][10][3][0]}'
            )
            logger.error(message)
            msg.send(message)
            # TODO or could raise an exception here
            return
    
    while not match_obj.is_final:
        time.sleep(60)
        match_obj = match.get_stats(match_obj)
        match_obj = match.get_feed(match_obj)
        title, markdown = md.match_thread(match_obj)
        # edit existing thread with thing_id
        response, _ = reddit.submit(subreddit, title, markdown, thing_id)
        logger.debug(f'Updated {match_obj.opta_id} at minute {match_obj.minute}')
        if not response.json()['success']:
            message = (
                f'Error posting {title} on {subreddit}.\n'
                f'{response.status_code} - {response.reason}\n'
                f'{response.json()["jquery"][10][3][0]}'
            )
            logger.error(message)
            msg.send(message)
        if match_obj.is_final:
            # post a post-match thread before exiting the loop
            post_match_thread(match_obj.opta_id)


def post_match_thread(opta_id):
    global subreddit
    # initialize an empty Match object with the opta_id
    match_obj = match.Match(opta_id)
    match_obj = match.get_all_data(match_obj)
    title, markdown = md.post_match_thread(match_obj)
    response, _ = reddit.submit(subreddit, title, markdown)
    if response.status_code == 200 and response.json()['success']:
        # TODO use something other than a database to track current threads
        logger.info(f'Posted {title} on {subreddit}')
    else:
        message = (
            f'Error posting {title} on {subreddit}.\n'
            f'{response.status_code} - {response.reason}\n'
            f'{response.json()["jquery"][10][3][0]}'
        )
        logger.error(message)
        msg.send(message)
        # TODO or could raise an exception here
        return


@util.time_dec(False)
def main():
    args = parser.parse_args()
    id = args.id
    if args.id:
        if args.pre:
            # pre-match thread
            pre_match_thread(id)
        elif args.post:
            post_match_thread(id)
        else:
            # match thread
            match_thread(id)
    #matches = get_upcoming_matches(date_from=1674627098)
    #print(matches)


if __name__ == '__main__':
    main()
