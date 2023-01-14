BASE_URL = 'https://stats-api.mlssoccer.com/v1/'
GAME_ID = 'match_game_id'
"""For each api call, add the param 'match_game_id' with
an integer opta_id to get information about a specific match.
Multiple match_game_ids can be passed."""

# match_facts gives preview stuff
PREVIEW_URL = BASE_URL + 'matchfacts'
PREVIEW_PARAMS = {'matchfact_language': 'en'}

MATCH_DATA_URL = BASE_URL + 'matches'
MATCH_DATA_PARAMS = {
    'include': ['competition', 'venue', 'home_club', 'away_club',
                'home_club_match', 'away_club_match']
}

STATS_URL = BASE_URL + 'clubs/matches'
STATS_PARAMS = {'include': ['club', 'match', 'competition', 'statistics']}

# page limit defaults to 100 for summary, feed
FEED_URL = BASE_URL + 'commentaries'
SUMMARY_PARAMS = {
    'commentary_type': ['secondyellow card', 'penalty goal', 'own goal',
                        'yellow card', 'red card', 'substitution', 'goal',
                        'penalty miss', 'penalty saved'],
    'include': ['club', 'player'],
    # are these alllll necessary? 
    'order_by': ['commentary_period', 'commentary_minute', 'commentary_second',
                 'commentary_timestamp', 'commentary_opta_id']
}
FULL_FEED_PARAMS = {
    'commentary_type': ['secondyellow card', 'penalty goal', 'own goal',
                        'yellow card', 'red card', 'substitution', 'goal',
                        'penalty miss', 'penalty saved', 'lineup', 'start',
                        'end 1', 'end 2', 'end 3', 'end 4', 'end 5', 'end 14',
                        'start delay', 'end delay', 'postponed',
                        'free kick lost', 'free kick won', 'attempt blocked',
                        'attempt saved', 'miss', 'post', 'corner', 'offside',
                        'penalty won', 'penalty lost', 'penalty miss',
                        'penalty saved', 'player retired',
                        'contentious referee decision', 'VAR cancelled goal'],
    'include': ['club', 'player', 'player_match'],
    # are these alllll necessary? 
    'order_by': ['commentary_period', 'commentary_minute', 'commentary_second',
                 'commentary_timestamp', 'commentary_opta_id']
}
# TODO implications of ordering by X or -X

LINEUP_URL = BASE_URL + 'players/matches'
LINEUP_PARAMS = {
    # add match_game_id
    'include': ['player', 'club']
}
SUBS_URL = BASE_URL + 'substitutions'
SUBS_PARAMS = {
    # add match_game_id
    'include': ['player_match', 'club', 'player']
}
MANAGER_URL = BASE_URL + 'managers/matches'
MANAGER_PARAMS = {
    # add match_game_id
    'include': ['manager', 'club']
}