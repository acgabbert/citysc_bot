import time
import logging
from datetime import datetime

import mls_api as mls
import mls_schedule
import util
import match_constants as const
import player
import club
import injuries

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
        self.started = False
        self.is_final = False
        self.preview = []
        self.feed = []
        self.videos = []
        self.summary = []
        self.broadcasters = []
        self.apple_tier = ''
        self.apple_url = ''
    
    def get_date_time(self):
        """Return date, time in match thread format."""
        secs = int(self.date)
        date = time.strptime(time.ctime(secs))
        date_val = time.strftime('%B %d, %Y', date)
        time_val = time.strftime('%I:%M %p ', date)
        time_val += datetime.now().astimezone().tzname()
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
    try:
        opta_id = params[const.GAME_ID]
        filename = f'{filename}-{opta_id}'
    except KeyError:
        pass
    data, _ = mls.call_api(url, params)
    util.write_json(data, f'assets/{filename}.json')
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
    scorers = {}
    for comment in data:
        # in order from earliest to latest
        adder = ''
        if comment['minute_display'] is None or comment['period'] == 'FullTime':
            adder = f'⏱️ {comment["comment"]}'
        else:
            adder = f'{comment["minute_display"]} '
            if comment['type'] in const.FEED_EMOJI:
                adder += const.FEED_EMOJI[comment['type']]
            adder += f' {comment["comment"]}'
        if comment['type'] in ['goal', 'own goal']:
            p = comment['first_player'] # goalscorer
            name = get_player_name(p)
            minute = comment['minute_display']
            scorer = f'{name} {minute}'
            if comment['type'] == 'own goal':
                scorer += ' (OG)'
            tm = comment['first_club']['opta_id']
            if tm in scorers.keys():
                scorers[tm].append(scorer)
            else:
                scorers[tm] = [scorer]
        comments.append(adder)
    return comments, scorers


def process_scorers(match_obj: Match, scorers: dict) -> Match:
    retval = match_obj
    tms = scorers.keys()
    for id in tms:
        # TODO do this more gracefully
        if id == match_obj.home.opta_id:
            for p in scorers[id]:
                if '(OG)' in p:
                    retval.away.goalscorers.append(p)
                else:
                    retval.home.goalscorers.append(p)
        elif id == match_obj.away.opta_id:
            for p in scorers[id]:
                if '(OG)' in p:
                    retval.home.goalscorers.append(p)
                else:
                    retval.away.goalscorers.append(p)
        else:
            logger.error('Scorers ID does not match either team.')
    return retval


def process_club(data, away=False) -> club.ClubMatch:
    """Process club data. Should be called from get_match_data."""
    t = 'home_club'
    if away:
        t = 'away_club'
    team_match = t + '_match'
    opta_id = data[t]['opta_id']
    retval = club.ClubMatch(opta_id=opta_id)
    retval.match_id = data[team_match]['match_id']
    if retval.full_name == '':
        retval.full_name = data[t]['name']
        retval.abbrev = data[t]['abbreviation']
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
    - started
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
        logger.error(message)
        return retval
    retval.venue = data['venue']['name']
    retval.comp = data['competition']['name']
    if retval.comp == 'US Major League Soccer':
        retval.comp = 'MLS'
        if data['type'] == 'Cup':
            retval.comp = 'MLS Cup Playoffs'
    if data['type'] == 'Cup':
        retval.comp += f', {data["round_name"]}'
        if data['round_number'] is not None:
            retval.comp += f' {data["round_number"]}'
    retval.home = process_club(data)
    retval.away = process_club(data, True)
    retval.date = data['date']
    if retval.date > 999999999999:
        retval.date /= 1000
    retval.minute = data['minute_display']
    if data['period'] == 'HalfTime':
        retval.minute = 'HT'
    result = data['result_type']
    if result == 'FullTime' or result == 'Aggregate' or result == 'NormalResult':
        retval.result_type = 'FT'
    elif result == 'PenaltyShootout':
        retval.result_type = 'FT-Pens'
    elif result == 'AfterExtraTime':
        retval.result_type = 'AET'
    if result is None and data['period'] == 'FullTime':
        retval.result_type = 'FT'
    if data['first_half_start'] is not None:
        retval.started = True
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
    comments, scorers = process_feed(data)
    retval = process_scorers(retval, scorers)
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
    comments, scorers = process_feed(data)
    retval = process_scorers(retval, scorers)
    retval.summary = comments
    return retval


def get_player_name(player):
    name = player['full_name']
    if name is None:
        name = player['first_name'] + ' ' + player['last_name']
    return name


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
        name = get_player_name(p['player'])
        formation_place  = p['formation_place']
        player_id = p['player']['opta_id']
        adder = player.Player(player_id, name, status, formation_place, team_id)
        if team_id == retval.home.opta_id:
            retval.home.lineup.append(adder)
        elif team_id == retval.away.opta_id:
            retval.away.lineup.append(adder)
        else:
            logger.error(f'Error: player {name}, game {retval.opta_id} does not match either team. {team_id}')
    for p in subs:
        off_name = get_player_name(p['off_player'])
        on_name = get_player_name(p['on_player'])
        minute = p['minute_display']
        if p['club']['opta_id'] == retval.home.opta_id:
            retval.home.subs[off_name] = (on_name, minute)
        elif p['club']['opta_id'] == retval.away.opta_id:
            retval.away.subs[off_name] = (on_name, minute)
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


def process_stats(data, team: club.ClubMatch) -> club.ClubMatch:
    """Process stats fields from const.STATS_FIELDS"""
    team.goals = data['score']
    if data['first_penalty_kick'] is not None:
        team.shootout_score = data['shootout_score']
    stats = data['statistics']
    for stat in const.STATS_FIELDS:
        try:
            setattr(team, stat, stats[stat])
        except KeyError:
            # field does not exist from api
            # set to 0 so we know it was attempted
            setattr(team, stat, 0)
    # calculate pass accuracy and save it as a string
    if team.total_pass > 0:
        pass_accuracy = (team.accurate_pass / team.total_pass) * 100
        team.pass_accuracy = '%.1f' % pass_accuracy
    return team


def get_stats(match_obj: Match) -> Match:
    """Get stats from a match."""
    retval = match_obj
    url = const.STATS_URL
    params = const.STATS_PARAMS
    params[const.GAME_ID] = match_obj.opta_id
    data = call_match_api(url, params, 'stats')
    for team in data:
        try:
            if team['side'] == 'home':
                retval.home = process_stats(team, match_obj.home)
            elif team['side'] == 'away':
                retval.away = process_stats(team, match_obj.away)
            else:
                # team is neither home nor away...this shouldn't happen
                pass
        except KeyError:
            # data most likely hasn't been populated yet
            pass
    return retval


def get_recent_form(match_obj: Match) -> Match:
    """Get recent form for the teams participating in a match"""
    retval = match_obj
    url = const.RECENT_FORM_URL + str(match_obj.home.opta_id) + '?'
    params = const.RECENT_FORM_PARAMS
    params['secondClub'] = match_obj.away.opta_id
    params['matchDate'] = datetime.fromtimestamp(match_obj.date).isoformat()
    data = call_match_api(url, params, 'recent-form')
    retval.home.recent_form = data['firstClubFormGuide']
    retval.away.recent_form = data['secondClubFormGuide']
    return retval


def get_broadcasters(match_obj: Match) -> Match:
    retval = match_obj
    url = mls_schedule.BASE_URL + f'/{match_obj.opta_id}'
    data, status_code = mls.call_api(url)
    if status_code == 204:
        url = mls_schedule.NEXTPRO_URL + f'/{match_obj.opta_id}'
        data = mls.call_api(url)[0]
    if data is None:
        # no broadcast info...
        return retval
    util.write_json(data, f'assets/match-{match_obj.opta_id}.json')
    match_obj.apple_tier = data['appleSubscriptionTier']
    match_obj.apple_url = data['appleStreamURL'].split('?')[0]
    broadcasters = data['broadcasters']
    adder = []
    for b in broadcasters:
        if b['broadcasterType'] not in ['US TV', 'International Streaming', 'US Streaming']:
            continue
        if 'Apple' in b['broadcasterName']:
            adder.append(f'[{b["broadcasterName"]}]({data["appleStreamURL"]})')
        elif len(b['broadcasterStreamingURL']) > 1:
            adder.append(f'[{b["broadcasterName"]}]({b["broadcasterStreamingURL"]}) (US)')
        else:
            adder.append(f'{b["broadcasterName"]} (US)')
    match_obj.broadcasters = adder
    return retval


def get_videos(match_obj: Match) -> Match:
    retval = match_obj
    vid_url = 'https://mlssoccer.com/video/'
    url = 'https://dapi.mlssoccer.com/v2/content/en-us/brightcovevideos'
    params = {'fields.optaMatchId': match_obj.opta_id}
    data = mls.call_api(url, params)[0]['items']
    vids = []
    for vid in data:
        vids.append((vid['title'],f'{vid_url}{vid["slug"]}'))
    retval.videos = vids
    return retval


def get_injuries(match_obj: Match) -> Match:
    retval = match_obj
    inj = util.read_json(injuries.INJ_FILE)
    date_format = '%m/%d/%Y, %H:%M'
    last_updated = datetime.strptime(inj['updated'], date_format)
    delta = datetime.now() - last_updated
    if delta.days > 2:
        return retval
    inj = inj['injuries']
    home_inj = []
    away_inj = []
    try:
        home_inj = inj[str(retval.home.opta_id)]
        away_inj = inj[str(retval.away.opta_id)]
    except Exception as e:
        # did not match
        logger.error(f'Failed to match injury opta IDs for {retval.home.opta_id}, {retval.away.opta_id}')
        logger.error(e)
    retval.home.injuries = home_inj
    retval.away.injuries = away_inj
    return retval


def get_prematch_data(match_obj: Match) -> Match:
    """Get data for a pre-match thread (no stats, lineups, etc)"""
    logger.info(f'Getting pre-match data for {match_obj.opta_id}')
    match_obj = get_match_data(match_obj)
    match_obj = get_recent_form(match_obj)
    match_obj = get_preview(match_obj)
    match_obj = get_broadcasters(match_obj)
    match_obj = get_injuries(match_obj)
    return match_obj


def get_all_data(match_obj: Match) -> Match:
    """Get all data for a match thread (only a summary feed)."""
    logger.info(f'Getting all data for {match_obj.opta_id}')
    match_obj = get_match_data(match_obj)
    match_obj = get_recent_form(match_obj)
    match_obj = get_preview(match_obj)
    match_obj = get_lineups(match_obj)
    match_obj = get_managers(match_obj)
    match_obj = get_stats(match_obj)
    match_obj = get_summary(match_obj)
    match_obj = get_broadcasters(match_obj)
    match_obj = get_videos(match_obj)
    return match_obj


def get_match_update(match_obj: Match) -> Match:
    """Get data for updating a match thread."""
    logger.info(f'Getting updated data for {match_obj.opta_id}')
    match_obj = get_match_data(match_obj)
    match_obj = get_lineups(match_obj)
    match_obj = get_stats(match_obj)
    match_obj = get_summary(match_obj)
    match_obj = get_videos(match_obj)
    return match_obj


@util.time_dec(False)
def main():
    opta_id = 2335158
    match_obj = Match(opta_id)
    match_obj = get_match_data(match_obj)
    match_obj = get_lineups(match_obj)
    print(match_obj.away.lineup_str())


if __name__ == '__main__':
    main()
