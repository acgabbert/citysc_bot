import mls_api as mls
import util
from typing import TypedDict
from collections import namedtuple
from dataclasses import dataclass
from dataclasses import field
from typing import Optional

BASE_URL = 'https://stats-api.mlssoccer.com/v1/'
# match_facts gives preview stuff
PREVIEW = 'matchfacts?&matchfact_language=en'
GAME_ID = '&match_game_id='
MATCH_DATA = 'matches?&include=away_club_match&include=home_club_match&include=venue&include=home_club&include=away_club&include=competition'
STATS = 'clubs/matches?&include=club&include=match&include=competition&include=statistics'
# no page limit for summary, could pose issues
SUMMARY = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&include=club&include=player&order_by=commentary_period&order_by=commentary_minute&order_by=commentary_second&order_by=commentary_timestamp&order_by=commentary_opta_id'
# no page limit for feed, could pose issues
FEED = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&commentary_type=lineup&commentary_type=start&commentary_type=end 1&commentary_type=end 2&commentary_type=end 3&commentary_type=end 4&commentary_type=end 5&commentary_type=end 14&commentary_type=start delay&commentary_type=end delay&commentary_type=postponed&commentary_type=free kick lost&commentary_type=free kick won&commentary_type=attempt blocked&commentary_type=attempt saved&commentary_type=miss&commentary_type=post&commentary_type=corner&commentary_type=offside&commentary_type=penalty won&commentary_type=penalty lost&commentary_type=penalty miss&commentary_type=penalty saved&commentary_type=player retired&commentary_type=contentious referee decisions&commentary_type=VAR cancelled goal&include=club&include=player&include=player_match&order_by=-commentary_period&order_by=-commentary_minute&order_by=-commentary_second&order_by=-commentary_timestamp&order_by=-commentary_opta_id'
LINEUPS = 'players/matches?&include=player&include=club'
MANAGERS = 'managers/matches?&include=manager&include=club'


class Team(mls.MlsObject):
    def __init__(self, opta_id):
        super().__init__(opta_id)
        self.name = ''
        self.starters = []
        self.subs = []
        self.formation_matrix = []
    
    def __str__(self):
        if self.name:
            return self.name
        else:
            return super().__str__()


class Match(mls.MlsObject):
    def __init__(self, opta_id):
        super().__init__(opta_id)
        self.venue = ''
        self.comp = ''
        self.home = Team(-1)
        self.away = Team(-1)
        self.is_final = False
        self.preview = []
        self.feed = []
        self.summary = []
    
    def __str__(self):
        retval = ''
        if self.home.opta_id != -1:
            retval += f'{self.home.name} vs. {self.away.name}'
        else:
            return super().__str__()
        return retval


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


def process_feed(data) -> list[str]:
    """Process a feed (summary or full feed)."""
    comments = []
    for comment in data:
        # in order from earliest to latest
        adder = f'{comment["minute_display"]} {comment["comment"]}'
        comments.append(adder)
    return comments


def process_club(data, away=False) -> Team:
    team = 'home_club'
    if away:
        team = 'away_club'
    team_match = team + '_match'
    opta_id = data[team]['opta_id']
    retval = Team(opta_id=opta_id)
    retval.name = data[team]['name']
    if data[team_match]['formation_matrix'] is not None:
        retval.form
    print(retval)
    return retval


def get_match_data(match_obj: Match) -> Match:
    """Get the match data for a match.
    Specfically, this is one place to get the formation matrix.
    """
    retval = match_obj
    url = BASE_URL + MATCH_DATA + GAME_ID + str(match_obj.opta_id)
    data = call_match_api(url, 'match-data')[0]
    retval.venue = data['venue']['name']
    retval.comp = data['competition']['name']
    retval.home = process_club(data)
    retval.away = process_club(data, True)
    return retval


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
    Returns a list of comments.
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


def get_stats(opta_id):
    url = BASE_URL + STATS + GAME_ID + opta_id
    data = call_match_api(url, 'stats')
    home_score = 0
    away_score = 0
    try:
        home_score = data[0]['statistics']['goals']
    except KeyError:
        pass
    try:
        away_score = data[1]['statistics']['goals']
    except KeyError:
        pass
    print(f'{home_score}:{away_score}')
    return data


@util.time_dec(False)
def main():
    opta_id = 2341646
    match_obj = Match(opta_id)
    print(match_obj)
    match_obj = get_match_data(match_obj)
    print(match_obj)
    #match_obj = get_preview(match_obj)
    #get_stats(match_obj)


if __name__ == '__main__':
    main()
