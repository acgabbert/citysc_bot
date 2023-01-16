import mls_schedule
from match import Match, get_match_data
import widget_markdown as md

STL_CITY = 17012

def get_upcoming(opta_id):
    """Returns a list of the next 5 upcoming matches
    Sorted in date order"""
    data = mls_schedule.get_schedule(team=opta_id)
    ids = mls_schedule.get_upcoming_matches(data)
    matches = []
    for id in ids:
        m = Match(id)
        get_match_data(m)
        matches.append(m)
    matches.sort()
    return matches


if __name__ == '__main__':
    matches = get_upcoming(STL_CITY)
    print(md.schedule(matches))
