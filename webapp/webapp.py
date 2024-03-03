from datetime import datetime
from datetime import timedelta
from flask import Flask, render_template
import json

import citysc_bot.mls_schedule as mls_schedule

app = Flask(__name__)

@app.route('/')
@app.route('/index')
def hello_world():
    date_format = '%Y-%m-%d'
    date_from = datetime.now()
    date_to = date_from + timedelta(days=14)
    date_from = date_from.strftime(date_format)
    date_to = date_to.strftime(date_format)
    schedule = mls_schedule.get_schedule(team=17012, date_from=date_from, date_to=date_to)
    return render_template('index.html', schedule=schedule)