# Hostname for logging purposes
HOST = "host"
# Teams to follow, by Opta ID
TEAMS = [
    17012, # St. Louis City SC
    19202  # St. Louis City SC 2 (MLS Next Pro)
]
FEATURE_FLAGS = {
    # Enable playwright and widget updates
    'enable_widgets': True,
    # Enable player availability updates
    'enable_injuries': True,
    # Enable player disciplinary updates
    'enable_discipline': True,
    # Enable daily match checking tasks
    'enable_daily_setup':  True,
    # Enable inline club logos in match thread headers
    'enable_inline_logos': False,
    # Schedule times (24h format)
    'schedule_times': {
        'playwright': '00:45',
        'widgets': '01:00',
        'injuries': '01:15',
        'discipline': '01:15',
        'prune_threads': '01:25',
        'daily_setup': '01:30'
    }
}
# Reddit config
CLIENT_ID = ''
SECRET_TOKEN = ''
USERNAME = ''
PASSWORD = ''
SUB = '/r/stlouiscitysc'
TEST_SUB = '/r/u_citysc_bot'
USER_AGENT_STR = 'CitySCBot/0.0.1'
USER_AGENT = {'User-Agent': 'CitySCBot/0.0.1'}
# Discord config
DISCORD_BOTADMINID = '' # a group to tag for important log messages
DISCORD_APP_ID = ''
DISCORD_TOKEN = ''
MLS_BOT_WEBHOOK = 'https://discord.com/api/webhooks/'
THREADS_JSON = 'data/threads.json'
# Entries in THREADS_JSON older than this are removed daily
THREADS_MAX_AGE_DAYS = 30
# Seconds between match thread updates, and from the 80th minute on
MATCH_UPDATE_INTERVAL = 60
MATCH_UPDATE_INTERVAL_LATE = 30
# Stop updating a match thread this many hours after kickoff if the match never goes final
MATCH_THREAD_MAX_HOURS = 5

