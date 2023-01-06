import mls_api as mls
import util

BASE_URL = 'https://stats-api.mlssoccer.com/v1/'
# match_facts gives preview stuff
PREVIEW = 'matchfacts?&matchfact_language=en'
GAME_ID = '&match_game_id='
MATCH_DATA = 'matches?&include=away_club_match&include=home_club_match&include=venue&include=home_club&include=away_club'
STATS = '&include=club&include=match&include=competition&include=statistics'
# no page limit for summary, could pose issues
SUMMARY = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&include=club&include=player&order_by=commentary_period&order_by=commentary_minute&order_by=commentary_second&order_by=commentary_timestamp&order_by=commentary_opta_id'
# no page limit for feed, could pose issues
FEED = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&commentary_type=lineup&commentary_type=start&commentary_type=end 1&commentary_type=end 2&commentary_type=end 3&commentary_type=end 4&commentary_type=end 5&commentary_type=end 14&commentary_type=start delay&commentary_type=end delay&commentary_type=postponed&commentary_type=free kick lost&commentary_type=free kick won&commentary_type=attempt blocked&commentary_type=attempt saved&commentary_type=miss&commentary_type=post&commentary_type=corner&commentary_type=offside&commentary_type=penalty won&commentary_type=penalty lost&commentary_type=penalty miss&commentary_type=penalty saved&commentary_type=player retired&commentary_type=contentious referee decisions&commentary_type=VAR cancelled goal&include=club&include=player&include=player_match&order_by=-commentary_period&order_by=-commentary_minute&order_by=-commentary_second&order_by=-commentary_timestamp&order_by=-commentary_opta_id'
LINEUPS = 'players/matches?&include=player&include=club'
MANAGERS = 'managers/matches?&include=manager&include=club'


def call_match_api(url, filename):
    opta_id = url.split('=')[-1]
    data, status = mls.call_api(url)
    util.write_json(data, f'assets/{filename}-{opta_id}.json')
    return data


def process_formation(data):
    """Process the formation matrix"""
    formation = []
    for row in data:
        for i in row:
            formation.append(i)
    return formation


def process_feed(data):
    """Process a feed (summary or full feed)."""
    comments = []
    for comment in data:
        # in order from earliest to latest
        adder = f'{comment["minute_display"]} {comment["comment"]}'
        comments.append(adder)
    return comments


def get_match_data(opta_id):
    """Get the match data for a match.
    Specfically, this is one place to get the formation matrix.
    """
    url = BASE_URL + MATCH_DATA + GAME_ID + opta_id
    data = call_match_api(url, 'match-data')
    home = data[0]['home_club_match']
    home_formation = process_formation(home['formation_matrix'])
    print(home_formation)
    away = data[0]['away_club_match']
    away_formation = process_formation(away['formation_matrix'])
    print(away_formation)
    return data


def get_preview(opta_id):
    """Get the preview (match facts) for a match.
    Returns a list of comments.
    """
    url = BASE_URL + PREVIEW + GAME_ID + opta_id
    data = call_match_api(url, 'preview')
    comments = []
    for row in data:
        comments.append(row['fact'])
    return comments


def get_feed(opta_id):
    """Get the full feed from a match."""
    url = BASE_URL + FEED + GAME_ID + opta_id
    data = call_match_api(url, 'feed')
    comments = process_feed(data)
    return comments


def get_summary(opta_id):
    """Get the summary feed from a match.
    Includes goals, red cards, substitutions (?)
    """
    url = BASE_URL + SUMMARY + GAME_ID + opta_id
    data = call_match_api(url, 'summary')
    comments = process_feed(data)
    return comments


def get_lineups(opta_id):
    """Get the lineups from a match."""
    # TODO to get the lineups in the correct order, we need formation matrix
    # this can come from stats
    url = BASE_URL + LINEUPS + GAME_ID + opta_id
    data = call_match_api(url, 'lineups')
    lineups = {}
    for player in data:
        team_id = player['club']['opta_id']
        if team_id not in lineups.keys():
            lineups[team_id] = {'Start': [], 'Sub': []}
        status = player['status']
        name = player['player']['full_name']
        formation_place  = player['formation_place']
        lineups[team_id][status].append((name, formation_place))
    return lineups


def get_managers(opta_id):
    url = BASE_URL + MANAGERS + GAME_ID + opta_id
    data = call_match_api(url, 'managers')
    managers = []
    for manager in data:
        name = f'{manager["manager"]["first_name"]} {manager["manager"]["last_name"]}'
        club_id = manager['club']['opta_id']
        managers.append((club_id, name))
    return managers


@util.time_dec
def main():
    print(get_managers('2261389'))


if __name__ == '__main__':
    main()
