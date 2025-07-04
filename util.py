from time import time
import traceback
import logging
import sqlite3
import inspect
import json
import asyncpraw
import asyncio
import signal
import subprocess
from datetime import datetime, timezone
from collections import namedtuple
from typing import Any

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
        async def async_wrapper(*args, **kwargs):
            start = time()
            result = None
            try:
                if asyncio.iscoroutinefunction(func):
                    result =  await func(*args, **kwargs)
                else: 
                    result = func(*args, **kwargs)
            except Exception as e:
                logging.error(f'Critical error: {str(e)}\n{traceback.format_exc()}')
            finally:
                end = time()
                exe_time = f'%.2f' % (end-start)
                module_name = str(inspect.getmodule(func)).split('/')[-1].replace(".py'>",'')
                message = f'{module_name}.{func.__name__} finished. Execution time: {exe_time} seconds.'
                logging.info(message)
                msg.send(message, tag)
            return result 
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time()
            result = None
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                logging.error(f'Critical error: {str(e)}\n{traceback.format_exc()}')
            finally:
                end = time()
                exe_time = f'%.2f' % (end-start)
                module_name = str(inspect.getmodule(func)).split('/')[-1].replace(".py'>",'')
                message = f'{module_name}.{func.__name__} finished. Execution time: {exe_time} seconds.'
                logging.info(message)
                msg.send(message, tag)
            return result 
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
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
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        logging.error(f"Error writing file {filename}\n{str(e)}")
    return


def read_json(filename):
    """Read json data from a file to a dict."""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.loads(f.read())
        return data


def file_changed(filename):
    changes = subprocess.run(f'git status {filename}', capture_output=True, shell=True, text=True).stdout
    logging.debug(changes)
    if 'Changes not staged' in changes:
        message = f'{filename} changed.'
        logging.info(message)
        msg.send(message, tag=True)
        return True
    else:
        message = f'No changes to {filename}.'
        logging.info(message)
        msg.send(message)
        return False


Names = namedtuple('Names', 'full_name short_name abbrev sportec_id')

# a dict of namedtuples with each club's full/short/abbrev names
names = {
    15296: Names('Austin FC', 'Austin', 'ATX', 'MLS-CLU-000003'),
    11091: Names('Atlanta United', 'Atlanta', 'ATL', ''),
    1616: Names('CF Montréal', 'Montréal', 'MTL', ''),
    436: Names('Colorado Rapids', 'Colorado', 'COL', ''),
    16629: Names('Charlotte FC', 'Charlotte', 'CLT', ''),
    1903: Names('FC Dallas', 'Dallas', 'DAL', ''),
    1207: Names('Chicago Fire FC', 'Chicago', 'CHI', ''),
    1897: Names('Houston Dynamo FC', 'Houston', 'HOU', 'MLS-CLU-00000H'),
    1230: Names('LA Galaxy', 'LA Galaxy', 'LA', 'MLS-CLU-00000G'),
    454: Names('Columbus Crew', 'Columbus', 'CLB', 'MLS-CLU-00000E'),
    11690: Names('Los Angeles Football Club', 'LAFC', 'LAFC', 'MLS-CLU-000001'),
    1326: Names('D.C. United', 'D.C.', 'DC', ''),
    6977: Names('Minnesota United', 'Minnesota', 'MIN', ''),
    11504: Names('FC Cincinnati', 'Cincinnati', 'CIN', ''),
    14880: Names('Inter Miami CF', 'Miami', 'MIA', 'MLS-CLU-000008'),
    1581: Names('Portland Timbers', 'Portland', 'POR', 'MLS-CLU-00000P'),
    1899: Names('Real Salt Lake', 'Salt Lake', 'RSL', ''),
    15154: Names('Nashville SC', 'Nashville', 'NSH', ''),
    1131: Names('San Jose Earthquakes', 'San Jose', 'SJ', 'MLS-CLU-00000Q'),
    928: Names('New England Revolution', 'New England', 'NE', ''),
    9668: Names('New York City FC', 'New York City', 'NYC', ''),
    3500: Names('Seattle Sounders FC', 'Seattle', 'SEA', ''),
    399: Names('New York Red Bulls', 'New York', 'RBNY', ''),
    421: Names('Sporting Kansas City', 'Kansas City', 'KC', 'MLS-CLU-00000K'),
    6900: Names('Orlando City', 'Orlando', 'ORL', ''),
    21280: Names('San Diego FC', 'San Diego', 'SD', ''),
    17012: Names('St. Louis City SC', 'St. Louis', 'STL', 'MLS-CLU-00001L'),
    1708: Names('Vancouver Whitecaps FC', 'Vancouver', 'VAN', 'MLS-CLU-00000C'),
    5513: Names('Philadelphia Union', 'Philadelphia', 'PHI', ''),
    2077: Names('Toronto FC', 'Toronto', 'TOR', ''),
    14156: Names('Atlanta United 2', 'Atlanta 2', 'ATL2', ''),
    20220: Names('Austin FC II', 'Austin II', 'ATX2', ''),
    21148: Names('Carolina Core FC', 'Carolina', 'CCFC', ''),
    11662: Names('Chattanooga FC', 'Chattanooga', 'CFC', ''),
    19193: Names('Chicago Fire FC II', 'Chicago II', 'CHI2', ''),
    19194: Names('Colorado Rapids 2', 'Colorado 2', 'COL2', ''),
    19195: Names('Columbus Crew 2', 'Columbus 2', 'CLB2', 'MLS-CLU-000019'),
    20222: Names('Crown Legacy FC', 'Crown Legacy FC', 'CLT2', ''),
    19196: Names('FC Cincinnati 2', 'Cincinnati 2', 'CIN2', ''),
    19197: Names('Houston Dynamo 2', 'Houston 2', 'HOU2', ''),
    20223: Names('Huntsville City FC', 'Huntsville', 'HNT', ''),
    19198: Names('Inter Miami CF II', 'Inter Miami II', 'MIA2', ''),
    12135: Names('Ventura County FC', 'Ventura', 'VCFC', ''),
    20221: Names('Los Angeles Football Club 2', 'LAFC2', 'LAFC2', ''),
    19199: Names('Minnesota United 2', 'MNUFC2', 'MIN2', ''),
    16496: Names('New England Revolution II', 'New England II', 'NE2', ''),
    12125: Names('New York Red Bulls II', 'New York II', 'RBNY2', ''),
    15140: Names('North Texas SC', 'North Texas', 'NTX', ''),
    19200: Names('NYCFC II', 'NYCFC II', 'NYC2', ''),
    12133: Names('Orlando City B', 'Orlando City B', 'ORL2', ''),
    12131: Names('Philadelphia Union II', 'Philadelphia II', 'PHI2', ''),
    12137: Names('Real Monarchs', 'Monarchs', 'SLC', ''),
    19201: Names('The Town FC', 'The Town', 'TTFC', ''),
    11521: Names('Sporting KC II', 'Sporting KC II', 'SKC2', ''),
    19202: Names('St. Louis CITY 2', 'CITY 2', 'STL2', 'MLS-CLU-00001G'),
    10970: Names('Tacoma Defiance', 'Tacoma', 'TAC', ''),
    12134: Names('TFC II', 'TFC II', 'TOR2', ''),
    12136: Names('Timbers2', 'Timbers2', 'POR2', ''),
    12142: Names('Whitecaps FC 2', 'Vancouver 2', 'VAN2', ''),
    16497: Names('Union Omaha', 'Omaha', 'OMA', ''),
    1292: Names('Club América', 'América', 'CA', '')
}


def get_reddit() -> asyncpraw.Reddit:
    reddit = asyncpraw.Reddit(
        client_id=config.CLIENT_ID,
        client_secret=config.SECRET_TOKEN,
        password=config.PASSWORD,
        user_agent=config.USER_AGENT_STR,
        username=config.USERNAME
    )
    reddit.validate_on_submit = True
    return reddit

def normalize_datetime(v: Any) -> datetime:
    """
    Take a datetime string or object and return a UTC datetime.
    Raises ValueError for invalid formats or types.
    """
    if isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc)
            else:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception as e:
            raise ValueError(f"Invalid date format: {v}") from e
    elif isinstance(v, datetime):
        if v.tzinfo is not None:
            return v.astimezone(timezone.utc)
        return v.replace(tzinfo=timezone.utc)
    raise ValueError(f"Expected string or datetime, got {type(v)}")

def normalize_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        v_lower = v.strip().lower()
        if v_lower in ('true', '1', 'yes', 'on'):
            return True
        if v_lower in ('false', '0', 'no', 'off'):
            return False
    if isinstance(v, int):
        if v == 1:
            return True
        if v == 0:
            return False
    
    raise ValueError(f"Invalid boolean value: {v!r}")