#!/bin/bash
cd /home/aaron/mls_api
source /home/aaron/mls_api/env/bin/activate
/home/aaron/mls_api/env/bin/python /home/aaron/mls_api/sched_controller.py --sub /r/stlouiscitysc &
deactivate
