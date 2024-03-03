from datetime import datetime
from datetime import timedelta
from flask import Flask
import json

import citysc_bot.mls_schedule as mls_schedule

app = Flask(__name__)

@app.route('/')
def hello_world():
    date_format = '%Y-%m-%d'
    date_from = datetime.now()
    date_to = date_from + timedelta(days=14)
    date_from = date_from.strftime(date_format)
    date_to = date_to.strftime(date_format)
    retval = mls_schedule.get_schedule(team=17012, date_from=date_from, date_to=date_to)
    return json.dumps(retval, indent=2)