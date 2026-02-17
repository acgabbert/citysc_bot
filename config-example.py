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
        'selenium': '00:45',
        'widgets': '01:00',
        'injuries': '01:15',
        'discipline': '01:15',
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
CSS_PATH = 'markdown/markdown.css'
THREADS_JSON = 'data/threads.json'

# More reddit config - widgets
WIDGETS = {
    'upcoming': {
        'name': 'Upcoming Matches',
        'file': 'markdown/Upcoming_alt.md',
        'widget': '',
        'test widget': '',
        'css': CSS_PATH
    },
    'standings': {
        'name': 'Western Conference Standings',
        'file': 'markdown/WesternConference.md',
        'widget': '',
        'test widget': '',
        'css': CSS_PATH
    },
    'schedule': {
        'name': 'Full Schedule',
        'file': 'markdown/Schedule_alt.md',
        'widget': '',
        'test widget': '',
        'css': CSS_PATH
    },
    'preseason': {
        'name': 'Preseason Schedule',
        'file': 'markdown/Preseason.md',
        'widget': '',
        'test widget': '',
        'css': CSS_PATH
    }
}
