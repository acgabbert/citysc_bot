import time

import match
import util

"""
# select STL City matches coming up
# just edit the time
SELECT * FROM match WHERE time > 1677304800 and time < 1677391200 and (home = 17012 or away = 17012)
"""

def match_footer(match_obj: match.Match):
    retval = '\n\n---\n'
    retval += '^^Last ^^updated: '
    update = time.strftime('^^%b ^^%d, ^^%I:%M%p', time.localtime())
    retval += update + '.' + f' ^^Opta ^^ID: ^^{str(match_obj.opta_id)}'
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


def recent_form(match_obj: match.Match):
    home = match_obj.home
    away = match_obj.away
    retval = '### Recent Form\n'
    retval += f'{home.full_name}: {home.recent_form}\n\n'
    retval += f'{away.full_name}: {away.recent_form}\n\n---\n'
    return retval


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
    markdown += recent_form(match_obj)
    if len(match_obj.preview) > 0:
        markdown += '### Match Facts\n'
        for comment in match_obj.preview:
            markdown += comment + '\n\n'
    markdown += match_footer(match_obj)
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
    if match_obj.started:
        # TODO only add stats table after match has started
        markdown += stats_table(match_obj)
    markdown += '### Match Events\n'
    for comment in match_obj.summary:
        markdown += comment + '\n\n'
    markdown += match_footer(match_obj)
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

    markdown += match_footer(match_obj)
    return title, markdown


def stats_table(match_obj: match.Match):
    """Format stats table based on /u/matchcaster
    https://www.reddit.com/r/MLS/comments/z2x0xs/match_thread_belgium_vs_canada/
    """
    home = match_obj.home
    away = match_obj.away
    markdown = '### Match Stats:\n'
    table_header = f'{home.short_name}|{home.goals}-{away.goals}|{away.short_name}'
    table_header += '\n:-:|:-:|:-:'
    markdown += table_header
    markdown += f'\n{home.possession_percentage}|Ball Possession|{away.possession_percentage}'
    markdown += f'\n{home.total_scoring_att}|Total Shots|{away.total_scoring_att}'
    markdown += f'\n{home.ontarget_scoring_att}|Shots on Target|{away.ontarget_scoring_att}'
    markdown += f'\n{home.corner_taken}|Corner Kicks|{away.corner_taken}'
    markdown += f'\n{home.total_offside}|Offside|{away.total_offside}'
    markdown += f'\n{home.fk_foul_lost}|Fouls|{away.fk_foul_lost}'
    markdown += f'\n{home.yellow_card}|Yellow Cards|{away.yellow_card}'
    markdown += f'\n{home.red_card}|Red Cards|{away.red_card}'
    markdown += f'\n{home.saves}|Goalkeeper Saves|{away.saves}'
    markdown += f'\n{home.expected_goals}|Expected Goals (xG)|{away.expected_goals}'
    markdown += f'\n{home.total_pass}|Total Passes|{away.total_pass}'
    markdown += f'\n{home.pass_accuracy}%|Pass Accuracy|{away.pass_accuracy}%'
    markdown += '\n---\n'
    return markdown


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
