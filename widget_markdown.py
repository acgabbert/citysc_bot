from datetime import datetime
from match import Match
from util import names
from club import Club

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

def western_conference(teams: list[Club]):
    retval = '## Western Conference Standings\n'
    retval += 'Pos|Team|Pts|GP|GD\n'
    retval += ':-:|:-:|:-:|:-:|:-:\n'
    for team in teams:
        if team.conference != 'West':
            continue
        retval += f'{team.position}|'
        retval += f'{team.short_name}|'
        retval += f'{team.points}|'
        retval += f'{team.gp}|'
        retval += f'{team.gd}|\n'
    return retval
