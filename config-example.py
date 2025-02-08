# Hostname for logging purposes
HOST = "host"
# Teams to follow, by Opta ID
TEAMS = [
    17012, # St. Louis City SC
    19202  # St. Louis City SC 2 (MLS Next Pro)
]
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
THREADS_JSON = 'threads.json'

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
