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

SORT_TEMPLATE = {
    'id': '',
    'sort': 'new'
}

COMMENT_TEMPLATE = {
    'text': '',
    'thing_id': ''
}

def get_oauth_token():
    """Request an OAuth token
    Returns headers needed to make Reddit API calls
    """
    headers = USER_AGENT
    res = requests.post('https://www.reddit.com/api/v1/access_token', auth=APP_AUTH, data=USER_DATA, headers=headers)
    if res.status_code != 200:
        raise Exception(f'Status code {res.status_code} when getting Reddit OAuth token.')
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


def submit(subreddit, title, text, thing_id=None, no_replies=True, pin=True):
    """Submit a post to the given subreddit.
    If thing_id is not None, edit the existing post."""
    try:
        headers = get_oauth_token()
    except:
        raise
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
    r = requests.post(url, data=data, headers=headers)
    if thing_id is None:
        thing_id = (r.json()['jquery'][10][3][0]).split('/')[-3]
        if no_replies:
            disable_replies(thing_id, headers)
        if pin:
            sticky(thing_id, True, headers)
    #approve_post(thing_id, headers)
    return r, thing_id


def set_sort_order(thing_id, order='new'):
    """Set a post's default sort order.
    This can only be done as a moderator."""
    headers = get_oauth_token()
    url = REDDIT_OAUTH + '/api/set_suggested_sort'
    data = SORT_TEMPLATE
    data['id'] = f't3_{thing_id}'
    data['sort'] = order
    r = requests.post(url, data=data, headers=headers)
    return r


def get_sidebar_content(subreddit):
    headers = get_oauth_token()
    url = REDDIT_OAUTH + subreddit + '/wiki/config/sidebar'
    print(url)
    content = requests.get(url, headers=headers)
    return content.json()['data']['content_md']


def craft_sidebar(subreddit, new_content):
    """Craft sidebar content using bot content separators"""
    start_sep = '\r\n[comment]: # (start of bot content)\r\n'
    end_sep = '\r\n[comment]: # (end of bot content)\r\n'
    prev_sidebar = get_sidebar_content(subreddit)
    before = prev_sidebar.split(start_sep)
    after = before[1].split(end_sep)[1]
    before = before[0]
    retval = before + start_sep + new_content + end_sep + after
    return retval


def edit_sidebar(subreddit, new_content):
    """Push new content to the sidebar using bot content separators"""
    new_sidebar = craft_sidebar(subreddit, new_content)
    headers = get_oauth_token()
    url = REDDIT_OAUTH + subreddit + '/api/wiki/edit'
    data = {'content': new_sidebar, 'page': 'config/sidebar', 'reason': ''}
    return requests.post(url, data=data, headers=headers)


def comment(thing_id, text):
    headers = get_oauth_token()
    url = REDDIT_OAUTH + '/api/comment'
    data = COMMENT_TEMPLATE
    data['thing_id'] = f't3_{thing_id}'
    data['text'] = text
    r = requests.post(url, data=data, headers=headers)
    thing_id = (r.json()['jquery'][10][3][0]).split('/')[-3]
    #approve_post(thing_id, headers, True)
    return r


def disable_replies(thing_id, headers=None):
    if not headers:
        headers = get_oauth_token()
    url = REDDIT_OAUTH + '/api/sendreplies'
    data = {'id': f't3_{thing_id}', 'state': False}
    return requests.post(url, data=data, headers=headers)


def sticky(thing_id, state=True, headers=None):
    if not headers:
        headers = get_oauth_token()
    url = REDDIT_OAUTH + '/api/set_subreddit_sticky'
    data = {'id': f't3_{thing_id}', 'state': state}
    return requests.post(url, data=data, headers=headers)


def approve_post(thing_id, headers=None, comment=False):
    if not headers:
        headers = get_oauth_token()
    url = REDDIT_OAUTH + '/api/approve'
    if not comment:
        data = {'id': f't3_{thing_id}'}
    else:
        data = {'id': f't1_{thing_id}'}
    return requests.post(url, data=data, headers=headers)


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
