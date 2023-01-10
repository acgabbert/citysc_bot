from time import time
import traceback
import logging
import sqlite3
import inspect
import json

import discord as msg
import functools

mls_db = 'mls.db'

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

loggers = {}

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
            logger = setup_logger('MLS API Logger', 'log/mls_api.log')
            start = time()
            try:
                func()
            except Exception as e:
                logger.error(f'Critical error: {str(e)}\n{traceback.format_exc()}')
            end = time()
            exe_time = f'%.2f' % (end-start)
            module_name = str(inspect.getmodule(func)).split('/')[-1].replace(".py'>",'')
            message = f'{module_name}.{func.__name__} finished. Execution time: {exe_time} seconds.'
            logger.info(message)
            if tag:
                message = f'{msg.user}\n{message}'
            msg.send(message)
            return func
        return wrapper
    return timed_func


def db_query(query: str, data: tuple=None):
    logger = setup_logger('MLS Database Logger', 'log/db.log', level=logging.DEBUG)
    retval = None
    try:
        con = sqlite3.connect(mls_db)
        cur = con.cursor()
        if data is not None:
            retval = cur.execute(query, data)
        else:
            retval = cur.execute(query)
        logger.debug(query)
        if cur.rowcount > -1:
            logger.debug(f'{cur.rowcount} rows affected.')
        retval = retval.fetchall()
        con.commit()
        logger.debug(query)
    except Exception as e:
        logger.error(f'Database error: {str(e)}\n{traceback.format_exc()}\nQuery: {query}')
        raise
    finally:
        con.close()
    return retval


def write_json(data, filename):
    """Write json data to filename."""
    with open(filename, 'w') as f:
        f.write(json.dumps(data, indent=4))
