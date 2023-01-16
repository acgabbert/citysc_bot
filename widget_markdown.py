from datetime import datetime
from match import Match
from util import names

STL_CITY = 17012

def schedule(matches: list[Match]):
    retval = '## Upcoming Matches\n'
    retval += 'Date|Opponent|Comp|Time (CT)\n'
    retval += ':-:|:-:|:-:|:-:\n'
    for match in matches:
        date, time = match.get_date_time()
        date = datetime.strptime(date, '%B %d, %Y').strftime('%m/%d')
        adder = f'{date}|'
        if match.home.opta_id == STL_CITY:
            team = names[match.away.opta_id]
            adder += f'{team.short_name}|'
        else:
            team = names[match.home.opta_id]
            adder += f'{team.short_name}|'
        if match.comp == 'US Major League Soccer':
            adder += 'MLS|'
        else:
            adder += f'{match.comp}|'
        adder += f'{time}\n'
        retval += adder
    return retval
