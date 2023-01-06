from time import time
import traceback
import logging
import sqlite3

import discord as msg

mls_db = 'mls_test.db'

def time_dec(func):
    logging.basicConfig(filename='log/mls_scraper.log', format='%(asctime)s | %(levelname)s | %(message)s', level=logging.INFO)
    start = time()
    try:
        func()
    except Exception as e:
        logging.error(f'Critical error: {str(e)}\n{traceback.format_exc()}')
    end = time()
    exe_time = f'%.2f' % (end-start)
    message = f'MLS Scraper finished. Execution time: {exe_time} seconds.'
    logging.info(message)
    msg.send(f'{msg.user}\n{message}')


def db_query(query: str, data: tuple=None):
    retval = None
    try:
        con = sqlite3.connect(mls_db)
        cur = con.cursor()
        if data is not None:
            retval = cur.execute(query, data)
        else:
            retval = cur.execute(query)
        retval = retval.fetchall()
        con.commit()
    except Exception as e:
        logging.error(f'Database error: {str(e)}\n{traceback.format_exc()}')
    finally:
        con.close()
    return retval