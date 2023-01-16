import time
import logging

import mls_api as mls
import util
import match_constants as const
import player
import club

logger = logging.getLogger(__name__)


class Match(mls.MlsObject):
    def __init__(self, opta_id):
        super().__init__(opta_id)
        self.venue = ''
        self.comp = ''
        self.date = -1
        self.home = club.ClubMatch(-1)
        self.away = club.ClubMatch(-1)
        self.minute = ''
        self.result_type = ''
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
            retval += f'{self.home.full_name} vs. {self.away.full_name}'
        else:
            return super().__str__()
        return retval
    
    def __lt__(self, other):
        """Required in order to properly sort matches by date."""
        if self.date < other.date:
            return True
        else:
            return False


def call_match_api(url, params, filename):
    opta_id = params[const.GAME_ID]
    data, _ = mls.call_api(url, params)
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


def process_club(data, away=False) -> club.ClubMatch:
    """Process club data. Should be called from get_match_data."""
    t = 'home_club'
    if away:
        t = 'away_club'
    team_match = t + '_match'
    opta_id = data[t]['opta_id']
    retval = club.ClubMatch(opta_id=opta_id)
    retval.full_name = data[t]['name']
    formation = data[team_match]['formation_matrix']
    if formation is not None:
        retval.formation_matrix = process_formation(formation)
    return retval


def get_match_data(match_obj: Match) -> Match:
    """Get the match data for a match.
    Specfically, this is one place to get the formation matrix.
    Populates the following data in the Match object:
    - venue
    - comp
    - home
    - away
    - date
    - minute
    - result_type
    - is_final
    """
    retval = match_obj
    url = const.MATCH_DATA_URL
    params = const.MATCH_DATA_PARAMS
    params[const.GAME_ID] = match_obj.opta_id
    try:
        # should only get one dict for match data
        data = call_match_api(url, params, 'match-data')[0]
    except IndexError:
        message = f'{url} returned no data.'
        logging.error(message)
        return retval
    retval.venue = data['venue']['name']
    retval.comp = data['competition']['name']
    if retval.comp == 'US Major League Soccer':
        retval.comp = 'MLS'
        if data['type'] == 'Cup':
            retval.comp = 'MLS Cup Playoffs'
    if data['type'] == 'Cup':
        retval.comp += f', {data["round_name"]}'
    retval.home = process_club(data)
    retval.away = process_club(data, True)
    retval.date = data['date']
    if retval.date > 999999999999:
        retval.date /= 1000
    retval.minute = data['minute_display']
    result = data['result_type']
    if result == 'FullTime' or result == 'Aggregate' or result == 'NormalResult':
        retval.result_type = 'FT'
    elif result == 'PenaltyShootout':
        retval.result_type = 'FT-Pens'
    elif result == 'AfterExtraTime':
        retval.result_type = 'AET'
    retval.is_final = data['is_final']
    return retval


def get_preview(match_obj: Match) -> Match:
    """Get the preview (match facts) for a match.
    Returns a list of comments.
    """
    retval = match_obj
    url = const.PREVIEW_URL
    params = const.PREVIEW_PARAMS
    params[const.GAME_ID] = match_obj.opta_id
    data = call_match_api(url, params, 'preview')
    comments = []
    for row in data:
        comments.append(row['fact'])
    retval.preview = comments
    return retval


def get_feed(match_obj: Match) -> Match:
    """Get the full feed from a match."""
    retval = match_obj
    url = const.FEED_URL
    params = const.FULL_FEED_PARAMS
    params[const.GAME_ID] = match_obj.opta_id
    data = call_match_api(url, params, 'feed')
    comments = process_feed(data)
    retval.feed = comments
    return retval


def get_summary(match_obj: Match) -> Match:
    """Get the summary feed from a match.
    Includes goals, red cards, substitutions (?)
    Returns a list of comments.
    """
    retval = match_obj
    url = const.FEED_URL
    params = const.SUMMARY_PARAMS
    params[const.GAME_ID] = match_obj.opta_id
    # TODO refactor all of these try/except blocks, because not all of them take data[0]
    data = call_match_api(url, params, 'summary')
    comments = process_feed(data)
    retval.summary = comments
    return retval


def get_lineups(match_obj: Match) -> Match:
    """Get the lineups from a match."""
    retval = match_obj
    url = const.LINEUP_URL
    params = const.LINEUP_PARAMS
    params[const.GAME_ID] = match_obj.opta_id
    data = call_match_api(url, params, 'lineups')
    subs_url = const.SUBS_URL
    subs_params = const.SUBS_PARAMS
    subs_params[const.GAME_ID] = match_obj.opta_id
    subs = call_match_api(subs_url, subs_params, 'subs')
    for p in data:
        team_id = p['club']['opta_id']
        status = p['status']
        name = p['player']['full_name']
        formation_place  = p['formation_place']
        player_id = p['player']['opta_id']
        adder = player.Player(player_id, name, status, formation_place, team_id)
        # TODO figure out a place to get subs
        if team_id == retval.home.opta_id:
            retval.home.lineup.append(adder)
        elif team_id == retval.away.opta_id:
            retval.away.lineup.append(adder)
        else:
            logger.error(f'Error: player {name}, game {retval.opta_id} does not match either team.')
    for p in subs:
        off_name = p['off_player']['full_name']
        on_name = p['on_player']['full_name']
        if p['club']['opta_id'] == retval.home.opta_id:
            retval.home.subs[off_name] = on_name
        elif p['club']['opta_id'] == retval.away.opta_id:
            retval.away.subs[off_name] = on_name
    return retval


def get_managers(match_obj: Match) -> Match:
    """Get managers from a match."""
    retval = match_obj
    url = const.MANAGER_URL
    params = const.MANAGER_PARAMS
    params[const.GAME_ID] = match_obj.opta_id
    data = call_match_api(url, params, 'managers')
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
    url = const.STATS_URL
    params = const.STATS_PARAMS
    params[const.GAME_ID] = match_obj.opta_id
    data = call_match_api(url, params, 'stats')
    home_score = 0
    away_score = 0
    try:
        home_score = data[0]['score']
        match_obj.home.goals = home_score
        if data[0]['first_penalty_kick'] is not None:
            home_pens = data[0]['shootout_score']
            match_obj.home.shootout_score = home_pens
    except KeyError:
        pass
    try:
        away_score = data[1]['score']
        match_obj.away.goals = away_score
        if data[1]['first_penalty_kick'] is not None:
            away_pens = data[1]['shootout_score']
            match_obj.away.shootout_score = away_pens
    except KeyError:
        pass
    return retval


def get_all_data(match_obj: Match) -> Match:
    """Get all data for a match thread (only a summary feed)."""
    logger.info(f'Getting all data for {match_obj.opta_id}')
    match_obj = get_match_data(match_obj)
    match_obj = get_preview(match_obj)
    match_obj = get_lineups(match_obj)
    match_obj = get_managers(match_obj)
    match_obj = get_stats(match_obj)
    match_obj = get_summary(match_obj)
    return match_obj


@util.time_dec(False)
def main():
    opta_id = 2277793
    match_obj = Match(opta_id)
    match_obj = get_preview(match_obj)
    print(match_obj.preview)


if __name__ == '__main__':
    main()
