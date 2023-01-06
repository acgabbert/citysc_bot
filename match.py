import mls_api as mls
import util

MATCH_BASE = 'https://stats-api.mlssoccer.com/v1/'
# match_facts gives preview stuff
PREVIEW = 'matchfacts?&matchfact_language=en'
GAME_ID = '&match_game_id='
STATS = '&include=club&include=match&include=competition&include=statistics'
# no page limit for summary, may pose issues
SUMMARY = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&include=club&include=player&order_by=commentary_period&order_by=commentary_minute&order_by=commentary_second&order_by=commentary_timestamp&order_by=commentary_opta_id'
# no page limit for feed, may pose issues
FEED = 'commentaries?&commentary_type=secondyellow card&commentary_type=penalty goal&commentary_type=own goal&commentary_type=yellow card&commentary_type=red card&commentary_type=substitution&commentary_type=goal&commentary_type=lineup&commentary_type=start&commentary_type=end 1&commentary_type=end 2&commentary_type=end 3&commentary_type=end 4&commentary_type=end 5&commentary_type=end 14&commentary_type=start delay&commentary_type=end delay&commentary_type=postponed&commentary_type=free kick lost&commentary_type=free kick won&commentary_type=attempt blocked&commentary_type=attempt saved&commentary_type=miss&commentary_type=post&commentary_type=corner&commentary_type=offside&commentary_type=penalty won&commentary_type=penalty lost&commentary_type=penalty miss&commentary_type=penalty saved&commentary_type=player retired&commentary_type=contentious referee decisions&commentary_type=VAR cancelled goal&include=club&include=player&include=player_match&order_by=-commentary_period&order_by=-commentary_minute&order_by=-commentary_second&order_by=-commentary_timestamp&order_by=-commentary_opta_id'

def get_preview(opta_id):
    url = MATCH_BASE + PREVIEW + GAME_ID + opta_id
    data, status = mls.call_api(url)
    util.write_json(data, f'assets/preview-{opta_id}.json')

if __name__ == '__main__':
    get_preview('2261390')