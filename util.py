from time import time
import traceback
import logging
import sqlite3
import inspect
import json
import signal
from datetime import datetime

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
                func()
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
