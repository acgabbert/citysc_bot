from time import time
import traceback
import logging
import sqlite3
import inspect
import json
import praw
import signal
import subprocess
from datetime import datetime
from collections import namedtuple

import config
import discord as msg
import functools

mls_db = 'mls.db'

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

loggers = {}

class GracefulExit:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, *args):
        self.kill_now = True

def setup_logger(name, log_file, level=logging.INFO):
    """To avoid duplicate logs/loggers, use a global dict to keep track
    of which loggers are already initialized."""
    global loggers
    
    if loggers.get(name):
        return loggers.get(name)
    else:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.addHandler(handler)
        loggers[name] = logger
        return logger


def time_dec(tag):
    def timed_func(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time()
            try:
                func(*args, **kwargs)
            except Exception as e:
                logging.error(f'Critical error: {str(e)}\n{traceback.format_exc()}')
            end = time()
            exe_time = f'%.2f' % (end-start)
            module_name = str(inspect.getmodule(func)).split('/')[-1].replace(".py'>",'')
            message = f'{module_name}.{func.__name__} finished. Execution time: {exe_time} seconds.'
            logging.info(message)
            if tag:
                message = f'{msg.user}\n{message}'
            msg.send(message)
            return func
        return wrapper
    return timed_func


def iso_to_epoch(t):
    """Convert an ISO time (from get_schedule) to epoch time."""
    retval = datetime.fromisoformat(t)
    retval = retval.astimezone(tz=None)
    retval = int(retval.strftime('%s'))
    return retval


def db_query(query: str, data: tuple=None):
    retval = None
    try:
        con = sqlite3.connect(mls_db)
        cur = con.cursor()
        if data is not None:
            retval = cur.execute(query, data)
        else:
            retval = cur.execute(query)
        logging.debug(query)
        if cur.rowcount > -1:
            logging.debug(f'{cur.rowcount} rows affected.')
        retval = retval.fetchall()
        con.commit()
        logging.debug(query)
    except Exception as e:
        logging.error(f'Database error: {str(e)}\n{traceback.format_exc()}\nQuery: {query}')
        raise
    finally:
        con.close()
    return retval


def write_json(data, filename):
    """Write json data to filename."""
    with open(filename, 'w') as f:
        f.write(json.dumps(data, indent=4))
    return


def read_json(filename):
    """Read json data from a file to a dict."""
    with open(filename, 'r') as f:
        data = json.loads(f.read())
        return data


def file_changed(filename):
    changes = subprocess.run(f'git status {filename}', capture_output=True, shell=True, text=True).stdout
    logging.debug(changes)
    if 'Changes not staged' in changes:
        message = f'{filename} changed.'
        logging.info(message)
        msg.send(f'{msg.user}\n{message}')
        return True
    else:
        message = f'No changes to {filename}.'
        logging.info(message)
        msg.send(message)
        return False


Names = namedtuple('Names', 'full_name short_name abbrev')

# a dict of namedtuples with each club's full/short/abbrev names
names = {
    15296: Names('Austin FC', 'Austin', 'ATX'),
    11901: Names('Atlanta United', 'Atlanta', 'ATL'),
    1616: Names('CF Montréal', 'Montréal', 'MTL'),
    436: Names('Colorado Rapids', 'Colorado', 'COL'),
    16629: Names('Charlotte FC', 'Charlotte', 'CLT'),
    1903: Names('FC Dallas', 'Dallas', 'DAL'),
    1207: Names('Chicago Fire FC', 'Chicago', 'CHI'),
    1897: Names('Houston Dynamo FC', 'Houston', 'HOU'),
    1230: Names('LA Galaxy', 'LA', 'LA'),
    454: Names('Columbus Crew', 'Columbus', 'CLB'),
    11690: Names('Los Angeles Football Club', 'LAFC', 'LAFC'),
    1326: Names('D.C. United', 'D.C.', 'DC'),
    6977: Names('Minnesota United', 'Minnesota', 'MIN'),
    11504: Names('FC Cincinnati', 'Cincinnati', 'CIN'),
    14880: Names('Inter Miami CF', 'Miami', 'MIA'),
    1581: Names('Portland Timbers', 'Portland', 'POR'),
    1899: Names('Real Salt Lake', 'Salt Lake', 'RSL'),
    15154: Names('Nashville SC', 'Nashville', 'NSH'),
    1131: Names('San Jose Earthquakes', 'San Jose', 'SJ'),
    928: Names('New England Revolution', 'New England', 'NE'),
    9668: Names('New York City FC', 'New York City', 'NYC'),
    3500: Names('Seattle Sounders FC', 'Seattle', 'SEA'),
    399: Names('New York Red Bulls', 'New York', 'RBNY'),
    421: Names('Sporting Kansas City', 'Kansas City', 'KC'),
    6900: Names('Orlando City', 'Orlando', 'ORL'),
    17012: Names('St. Louis City SC', 'St. Louis', 'STL'),
    1708: Names('Vancouver Whitecaps FC', 'Vancouver', 'VAN'),
    5513: Names('Philadelphia Union', 'Philadelphia', 'PHI'),
    2077: Names('Toronto FC', 'Toronto', 'TOR'),
    14156: Names('Atlanta United 2', 'Atlanta 2', 'ATL2'),
    20220: Names('Austin FC II', 'Austin II', 'ATX2'),
    19193: Names('Chicago Fire FC II', 'Chicago II', 'CHI2'),
    19194: Names('Colorado Rapids 2', 'Colorado 2', 'COL2'),
    19195: Names('Columbus Crew 2', 'Columbus 2', 'CLB2'),
    20222: Names('Crown Legacy FC', 'Crown Legacy FC', 'CLT2'),
    19196: Names('FC Cincinnati 2', 'Cincinnati 2', 'CIN2'),
    19197: Names('Houston Dynamo 2', 'Houston 2', 'HOU2'),
    20223: Names('Huntsville City FC', 'Huntsville', 'HNT'),
    19198: Names('Inter Miami II', 'Inter Miami II', 'MIA2'),
    12135: Names('LA Galaxy II', 'Galaxy II', 'LA2'),
    20221: Names('Los Angeles Football Club 2', 'LAFC2', 'LAFC2'),
    19199: Names('Minnesota United 2', 'MNUFC2', 'MIN2'),
    16496: Names('New England Revolution II', 'New England II', 'NE2'),
    12125: Names('New York Red Bulls II' 'New York II', 'RBNY2'),
    15140: Names('North Texas SC', 'North Texas', 'NTX'),
    19200: Names('NYCFC II', 'NYCFC II', 'NYC2'),
    12133: Names('Orlando City B', 'Orlando City B', 'ORL2'),
    12131: Names('Philadelphia Union II', 'Philadelphia II', 'PHI2'),
    12137: Names('Real Monarchs', 'Monarchs', 'SLC'),
    19201: Names('San Jose Earthquakes II', 'Earthquakes II', 'SJ2'),
    11521: Names('Sporting KC II', 'Sporting KC II', 'SKC2'),
    19202: Names('St. Louis CITY 2', 'CITY 2', 'STL2'),
    10970: Names('Tacoma Defiance', 'Tacoma', 'TAC'),
    12134: Names('TFC II', 'TFC II', 'TOR2'),
    12136: Names('Timbers2', 'Timbers2', 'POR2'),
    12142: Names('Whitecaps FC 2', 'Vancouver 2', 'VAN2')
}


def get_reddit() -> praw.Reddit:
    reddit = praw.Reddit(
        client_id=config.CLIENT_ID,
        client_secret=config.SECRET_TOKEN,
        password=config.PASSWORD,
        user_agent=config.USER_AGENT_STR,
        username=config.USERNAME
    )
    reddit.validate_on_submit = True
    return reddit
