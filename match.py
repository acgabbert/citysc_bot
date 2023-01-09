import time

import mls_api as mls
import util

BASE_URL = 'https://stats-api.mlssoccer.com/v1/'
# match_facts gives preview stuff
PREVIEW = 'matchfacts?&matchfact_language=en'
GAME_ID = '&match_game_id='
MATCH_DATA = 'matches?&include=away_club_match&include=home_club_match&include=venue&include=home_club&include=away_club&include=competition'
STATS = 'clubs/matches?&include=club&include=match&include=competition&include=statistics'
# page limit defaults to 100 for summary, feed
SUMMARY = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&include=club&include=player&order_by=commentary_period&order_by=commentary_minute&order_by=commentary_second&order_by=commentary_timestamp&order_by=commentary_opta_id'
FULL_FEED = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&commentary_type=lineup&commentary_type=start&commentary_type=end 1&commentary_type=end 2&commentary_type=end 3&commentary_type=end 4&commentary_type=end 5&commentary_type=end 14&commentary_type=start delay&commentary_type=end delay&commentary_type=postponed&commentary_type=free kick lost&commentary_type=free kick won&commentary_type=attempt blocked&commentary_type=attempt saved&commentary_type=miss&commentary_type=post&commentary_type=corner&commentary_type=offside&commentary_type=penalty won&commentary_type=penalty lost&commentary_type=penalty miss&commentary_type=penalty saved&commentary_type=player retired&commentary_type=contentious referee decisions&commentary_type=VAR cancelled goal&include=club&include=player&include=player_match&order_by=-commentary_period&order_by=-commentary_minute&order_by=-commentary_second&order_by=-commentary_timestamp&order_by=-commentary_opta_id'
FEED = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&commentary_type=lineup&commentary_type=start&commentary_type=end 1&commentary_type=end 2&commentary_type=end 3&commentary_type=end 4&commentary_type=end 5&commentary_type=end 14&commentary_type=start delay&commentary_type=end delay&commentary_type=postponed&commentary_type=penalty won&commentary_type=penalty lost&commentary_type=penalty miss&commentary_type=penalty saved&commentary_type=player retired&commentary_type=contentious referee decisions&commentary_type=VAR cancelled goal&order_by=-commentary_period&order_by=-commentary_minute&order_by=-commentary_second&order_by=-commentary_timestamp&order_by=-commentary_opta_id'
LINEUPS = 'players/matches?&include=player&include=club'
MANAGERS = 'managers/matches?&include=manager&include=club'


class Team(mls.MlsObject):
    def __init__(self, opta_id):
        super().__init__(opta_id)
        self.name = ''
        self.manager = ''
        self.lineup = []
        self.formation_matrix = []
        self.goals = 0
    
    def lineup_str(self):
        starters = []
        subs = []
        for player in self.lineup:
            if player.status == 'Start':
                index = self.formation_matrix.index(player.formation_place)
                starters.insert(index, player)
            else:
                subs.append(player)
        retval = f'**{self.name}**\n\n'
        for player in starters:
            retval += player.name + ', '
        retval = retval[:-2] + '\n\n**Subs:** '
        for player in subs:
            retval += player.name + ', '
        retval = retval[:-2]
        retval += '\n\n'
        return retval
    
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
        self.date = -1
        self.home = Team(-1)
        self.away = Team(-1)
        self.is_final = False
        self.preview = []
        self.feed = []
        self.summary = []
    
    def get_date_time(self):
        """Return date, time in match thread format."""
        secs = int(self.date)
        date = time.strptime(time.ctime(secs))
        date_val = time.strftime('%B %d, %Y', date)
        time_val = time.strftime('%I:%M%p', date)
        # remove leading zero from time
        if time_val[0] == '0':
            time_val = time_val[1:]
        return date_val, time_val
    
    def __str__(self):
        retval = ''
        if self.home.opta_id != -1:
            retval += f'{self.home.name} vs. {self.away.name}'
        else:
            return super().__str__()
        return retval


class Player(mls.MlsObject):
    def __init__(self, opta_id, name, status, formation_place, team):
        super().__init__(opta_id)
        self.name = name
        self.status = status
        self.formation_place = formation_place
        self.team = team
    
    def __str__(self):
        return self.name


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
        adder = ''
        if comment['minute_display'] is None or comment['period'] == 'FullTime':
            adder = f'{comment["comment"]}'
        else:
            adder = f'{comment["minute_display"]} {comment["comment"]}'
        comments.append(adder)
    return comments


def process_club(data, away=False) -> Team:
    """Process club data. Should be called from get_match_data."""
    team = 'home_club'
    if away:
        team = 'away_club'
    team_match = team + '_match'
    opta_id = data[team]['opta_id']
    retval = Team(opta_id=opta_id)
    retval.name = data[team]['name']
    formation = data[team_match]['formation_matrix']
    if formation is not None:
        retval.formation_matrix = process_formation(formation)
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
    retval.date = data['date']
    if retval.date > 999999999999:
        retval.date /= 1000
    retval.is_final = data['is_final']
    return retval


def get_preview(match_obj: Match) -> Match:
    """Get the preview (match facts) for a match.
    Returns a list of comments.
    """
    retval = match_obj
    url = BASE_URL + PREVIEW + GAME_ID + str(match_obj.opta_id)
    data = call_match_api(url, 'preview')
    comments = []
    for row in data:
        comments.append(row['fact'])
    retval.preview = comments
    return retval


def get_feed(match_obj: Match) -> Match:
    """Get the full feed from a match."""
    retval = match_obj
    url = BASE_URL + FEED + GAME_ID + str(match_obj.opta_id)
    data = call_match_api(url, 'feed')
    comments = process_feed(data)
    retval.feed = comments
    return retval


def get_summary(match_obj: Match) -> Match:
    """Get the summary feed from a match.
    Includes goals, red cards, substitutions (?)
    Returns a list of comments.
    """
    retval = match_obj
    url = BASE_URL + SUMMARY + GAME_ID + str(match_obj.opta_id)
    data = call_match_api(url, 'summary')
    comments = process_feed(data)
    retval.summary = comments
    return retval


def get_lineups(match_obj: Match) -> Match:
    """Get the lineups from a match."""
    retval = match_obj
    url = BASE_URL + LINEUPS + GAME_ID + str(match_obj.opta_id)
    data = call_match_api(url, 'lineups')
    for player in data:
        team_id = player['club']['opta_id']
        status = player['status']
        name = player['player']['full_name']
        formation_place  = player['formation_place']
        player_id = player['player']['opta_id']
        adder = Player(player_id, name, status, formation_place, team_id)
        if team_id == retval.home.opta_id:
            retval.home.lineup.append(adder)
        elif team_id == retval.away.opta_id:
            retval.away.lineup.append(adder)
        else:
            print('problem, player does not match either team')
    return retval


def get_managers(match_obj: Match) -> Match:
    """Get managers from a match."""
    retval = match_obj
    url = BASE_URL + MANAGERS + GAME_ID + str(match_obj.opta_id)
    data = call_match_api(url, 'managers')
    for manager in data:
        team_id = manager['club']['opta_id']
        first = manager['manager']['first_name']
        last = manager['manager']['last_name']
        name = f'{first} {last}'
        if team_id == retval.home.opta_id:
            retval.home.manager = name
        elif team_id == retval.away.opta_id:
            retval.away.manager = name
    return retval


def get_stats(match_obj: Match) -> Match:
    """Get stats from a match."""
    retval = match_obj
    url = BASE_URL + STATS + GAME_ID + str(match_obj.opta_id)
    data = call_match_api(url, 'stats')
    home_score = 0
    away_score = 0
    try:
        home_score = data[0]['score']
        match_obj.home.goals = home_score
    except KeyError:
        pass
    try:
        away_score = data[1]['score']
        match_obj.away.goals = away_score
    except KeyError:
        pass
    return data


@util.time_dec(False)
def main():
    opta_id = 2335158
    match_obj = Match(opta_id)
    match_obj = get_match_data(match_obj)
    print(match_obj.get_date_time())


if __name__ == '__main__':
    main()
