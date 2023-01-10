import requests
import json

import config as conf

# app ID and secret token
APP_AUTH = requests.auth.HTTPBasicAuth(conf.CLIENT_ID, conf.SECRET_TOKEN)

# user account login information
USER_DATA = {
    'grant_type': 'password',
    'username': conf.USERNAME,
    'password': conf.PASSWORD
}

# header info gives Reddit a description of our app
# example: {'User-Agent': 'MyBot/0.0.1'}
USER_AGENT = conf.USER_AGENT

# url definitions
REDDIT_OAUTH = 'https://oauth.reddit.com'
TEST_SUB = conf.TEST_SUB
PROD_SUB = conf.SUB
WIDGET_URL = '/api/widgets'

# widgets
WIDGETS = conf.WIDGETS

# this is the standard json structure for a textarea widget
WIDGET_TEMPLATE = {
    'kind': 'textarea',
    'shortName': 'Standings',
    'styles': {
        'headerColor': '',
        'backgroundColor': ''
    },
    'text': 'test from api call'
}

POST_TEMPLATE = {
    'kind': 'self',
    'sr': TEST_SUB,
    'title': 'Another Title Example',
    'text': 'asdf'
}

def get_oauth_token():
    """Request an OAuth token
    Returns headers needed to make Reddit API calls
    """
    headers = USER_AGENT
    res = requests.post('https://www.reddit.com/api/v1/access_token', auth=APP_AUTH, data=USER_DATA, headers=headers)
    token = res.json()['access_token']
    headers['Authorization'] = 'bearer {}'.format(token)
    return headers


def get_widgets(subreddit, headers):
    # get the widget IDs from a given subreddit
    r = requests.get(REDDIT_OAUTH + subreddit + WIDGET_URL, headers=headers)
    # this gets the IDs of user-added widgets from the sidebar, in order
    widget_ids = r.json()['layout']['sidebar']['order']
    return widget_ids


def craft_payload(name, text):
    retval = WIDGET_TEMPLATE
    retval['shortName'] = name
    retval['text'] = text
    return retval


def edit_widget(subreddit, widget_id, name, text, headers=None):
    """Edit a widget given its ID
    text should be a markdown string
    """
    # edit a widget given its id
    # payload should be a properly formatted python dict
    if headers is None:
        headers = get_oauth_token()
    payload = craft_payload(name, text)
    return requests.put(REDDIT_OAUTH + subreddit + '/api/widget/' + widget_id, headers=headers, data=json.dumps(payload))


def submit(subreddit, title, text, thing_id=None):
    headers = get_oauth_token()
    url = ''
    data = POST_TEMPLATE
    data['sr'] = subreddit
    data['title'] = title
    data['text'] = text
    if thing_id is not None:
        data['thing_id'] = f't3_{thing_id}'
        url = REDDIT_OAUTH + '/api/editusertext'
    else:
        url = REDDIT_OAUTH + '/api/submit'
    # don't json-ize the data!
    print(url)
    print(data)
    r = requests.post(url, data=data, headers=headers)
    print(json.dumps(r.json()))
    response = r.json()
    if thing_id is None:
        thing_id = (response['jquery'][10][3][0]).split('/')[-3]
    return response, thing_id


if __name__ == '__main__':
    #HEADERS = get_oauth_token()
    #ids = get_widgets(TEST_SUB, HEADERS)
    #print(ids)
    #r = edit_widget(TEST_SUB, WIDGETS['upcoming']['test widget'], 'TEST', 'testing testing')
    headers = get_oauth_token()
    r = requests.post(REDDIT_OAUTH + '/api/submit', data=POST_TEMPLATE, headers=headers).json()
    print(json.dumps(r))
    # this is how to get the post url
    print(r['jquery'][10][3][0])
    # t3 = link
    r = requests.post(REDDIT_OAUTH + '/api/editusertext', data={'text': 'testing my editing skillz', 'thing_id': 't3_102893o'}, headers=headers).json()