import time

import match
import util

"""
# select STL City matches coming up
# just edit the time
SELECT * FROM match WHERE time > 1677304800 and time < 1677391200 and (home = 17012 or away = 17012)
"""

def match_footer():
    retval = '\n\n---\n'
    retval += '^^Last ^^updated: '
    update = time.strftime('^^%b ^^%d, ^^%I:%M%p', time.localtime())
    retval += update
    return retval


def match_header(match_obj: match.Match):
    """Create a match thread header (used by all types of thread)"""
    home = match_obj.home
    away = match_obj.away
    comp = match_obj.comp
    date, time = match_obj.get_date_time()
    venue = match_obj.venue
    header = ''
    if len(match_obj.summary) > 1:
        # match has started
        header = '# '
        if match_obj.is_final:
            header += f'{match_obj.result_type}: '
        header += f'{home.full_name} {home.goals}-{away.goals} '
        if home.shootout_score or away.shootout_score:
            header += f'({home.shootout_score}-{away.shootout_score} pens) '
        header += f'{away.full_name}\n'
    else:
        header = f'# {home.full_name} vs. {away.full_name}\n'
    header += f'### Match Info\n'
    header += f'**Competition:** {comp}\n\n'
    header += f'**Date:** {date}\n\n'
    header += f'**Time:** {time}\n\n'
    header += f'**Venue:** {venue}\n\n---\n'
    return header


def pre_match_thread(match_obj: match.Match):
    """Generate markdown for a pre-match thread."""
    home = match_obj.home.full_name
    away = match_obj.away.full_name
    comp = match_obj.comp
    # TODO this will eventually need to handle different values
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    title = f'Pre-Match Thread: {home} vs. {away} ({comp})'
    markdown = match_header(match_obj)
    markdown += '### Match Facts\n'
    for comment in match_obj.preview:
        markdown += comment + '\n\n'
    markdown += match_footer()
    return title, markdown


def match_thread(match_obj: match.Match):
    home = match_obj.home.full_name
    away = match_obj.away.full_name
    comp = match_obj.comp
    # TODO this will eventually need to handle different values
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    # TODO add date to title?
    title = f'Match Thread: {home} vs. {away} ({comp})'
    # TODO: if pens, add to title
    markdown = match_header(match_obj)
    markdown += '### Lineups\n'
    markdown += match_obj.home.lineup_str()
    markdown += match_obj.away.lineup_str()
    markdown += '---\n'
    markdown += '### Match Events\n'
    for comment in match_obj.summary:
        markdown += comment + '\n\n'
    markdown += match_footer()
    return title, markdown


def post_match_thread(match_obj: match.Match):
    home = match_obj.home
    away = match_obj.away
    comp = match_obj.comp
    # TODO this will eventually need to handle different values
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    # TODO add period/result type
    title = f'Post-Match Thread: {home.full_name} {home.goals}-{away.goals} '
    # TODO if pens, add to title here
    title += f'{away.full_name} ({comp})'
    markdown = match_header(match_obj)

    markdown += match_footer()
    return title, markdown


@util.time_dec(False)
def main():
    """
    matches = get_upcoming_matches(date_from=1674627098)
    print(matches)
    opta_id = 2261385
    match_obj = match.Match(opta_id)
    title, markdown = match_thread(match_obj)
    print(markdown)
    """
    pass


if __name__ == '__main__':
    main()
