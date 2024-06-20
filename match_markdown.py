import logging
import time

from discipline import DISC_URL
from injuries import INJ_URL
import match
import util

logger = logging.getLogger(__name__)


def match_footer(match_obj: match.Match):
    retval = '\n\n---\n\n'
    retval += '^^Last ^^updated: '
    update = time.strftime('^^%b ^^%d, ^^%I:%M%p', time.localtime())
    retval += update + '.' + f' ^^All ^^data ^^via ^^mlssoccer.com. ^^Opta ^^ID: ^^{str(match_obj.opta_id)}'
    return retval


def match_header(match_obj: match.Match, pre=False):
    """Create a match thread header (used by all types of thread)"""
    home = match_obj.home
    away = match_obj.away
    header = ''
    # TODO this is a problem - sometimes a match has no summary
    if match_obj.started or match_obj.is_final:
        # match has started
        header = '## '
        if match_obj.is_final:
            header += f'{match_obj.result_type}: '
        else:
            header += f'{match_obj.minute}: '
        header += f'{home.full_name} {home.goals}-{away.goals} '
        if home.shootout_score or away.shootout_score:
            header += f'({home.shootout_score}-{away.shootout_score} pens) '
        header += f'{away.full_name} '
        if match_obj.is_aggregate:
            header += f'({home.goals+home.previous_goals}-{away.goals+away.previous_goals} aggregate) '
        header += '\n'
    else:
        header = f'# {home.full_name} vs. {away.full_name}\n'
    if home.goalscorers:
        header += f'\n*{home.full_name} scorers: '
        for p in home.goalscorers:
            header += p + ', '
        header = header[:-2] + '*\n\n'
    if away.goalscorers:
        header += f'\n*{away.full_name} scorers: '
        for p in away.goalscorers:
            header += p + ', '
        header = header[:-2] + '*\n\n'
    if pre:
        header += match_info(match_obj)
    else:
        # add tv/streaming options here
        header += f'**TV/Streaming:** '
        for b in match_obj.broadcasters:
            header += f'{b}, '
        if len(match_obj.broadcasters) == 0:
            header += 'No data via mlssoccer.com.'
        else:
            header = header[:-2]
    header += '\n\n---\n\n'
    return header


def match_info(match_obj: match.Match):
    """Add match info to a header (pre-match threads only)"""
    comp = match_obj.comp
    date, time = match_obj.get_date_time()
    venue = match_obj.venue
    info = f'### Match Info\n'
    info += f'- **Competition:** {comp}\n'
    info += f'- **Date:** {date}\n'
    info += f'- **Time:** {time}\n'
    info += f'- **Venue:** {venue}\n'
    info += f'- **TV/Streaming:** '
    for b in match_obj.broadcasters:
        info += f'{b}, '
    if len(match_obj.broadcasters) == 0:
        info += 'No data via mlssoccer.com.'
    else:
        info = info[:-2]
    if match_obj.previous_match_opta_id not in [-1, 0]:
        info += '\n### Previous Result\n'
        info += f'{match_obj.away.full_name} {match_obj.away.previous_goals}-{match_obj.home.previous_goals} {match_obj.home.full_name}'
    return info


def video_highlights(match_obj: match.Match):
    """Add video highlights to a footer"""
    if len(match_obj.videos) < 1:
        return None
    retval = '---\n\n### Match Highlights\n'
    for g in match_obj.videos:
        retval += f'- [{g[0]}]({g[1]})\n'
    return retval


def recent_form(match_obj: match.Match):
    home = match_obj.home
    away = match_obj.away
    retval = '### Recent Form\n'
    retval += f'- {home.full_name}: {home.recent_form}\n'
    retval += f'- {away.full_name}: {away.recent_form}\n\n'
    return retval


def pre_match_thread(match_obj: match.Match):
    """Generate markdown for a pre-match thread."""
    home = match_obj.home.full_name
    away = match_obj.away.full_name
    comp = match_obj.comp
    date, time = match_obj.get_date_time()
    # TODO this will eventually need to handle different values
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    #title = f'Pre-Match Thread: {home} vs. {away} ({comp})'
    title = f'Matchday Thread: {home} vs. {away} ({comp}) [{date}]'
    markdown = ''
    markdown += match_header(match_obj, True)
    markdown += recent_form(match_obj)
    if len(match_obj.preview) > 0:
        markdown += '---\n\n### Match Facts\n'
        for comment in match_obj.preview:
            comment = comment.replace('\u2019', "'")
            comment = comment.replace('\u2014', '-')
            markdown += f'- {comment}\n'
    if match_obj.home.injuries or match_obj.away.injuries:
        markdown += f'\n---\n\n### [Player Availability Report]({INJ_URL})\n\n'
        markdown += f'#### {home}\n'
        for i in match_obj.home.injuries:
            markdown += f'- {i}\n'
        markdown += f'\n#### {away}\n'
        for i in match_obj.away.injuries:
            markdown += f'- {i}\n'
    if ('mls' in match_obj.comp.lower() or 'major league soccer' in match_obj.comp.lower()or 'regular season' in match_obj.comp.lower()) and (match_obj.home.discipline or match_obj.away.discipline):
        markdown += f'\n---\n\n### [Disciplinary Summary]({DISC_URL})\n\n'
        if match_obj.home.discipline:
            for player in match_obj.home.discipline.keys():
                markdown += f'- {player} ('
                for item in match_obj.home.discipline[player]:
                    markdown += f'{item}, '
                markdown = f'{markdown[:-2]})'
        if match_obj.away.discipline:
            for player in match_obj.away.discipline.keys():
                markdown += f'- {player} ('
                for item in match_obj.away.discipline[player]:
                    markdown += f'{item}, '
                markdown = f'{markdown[:-2]})'
    markdown += match_footer(match_obj)
    return title, markdown


def match_thread(match_obj: match.Match):
    home = match_obj.home.full_name
    away = match_obj.away.full_name
    comp = match_obj.comp
    # TODO this will eventually need to handle different values
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    date, time = match_obj.get_date_time()
    title = f'Match Thread: {home} vs. {away} ({comp}) [{date}, {time}]'
    # TODO: if pens, add to title
    markdown = match_header(match_obj)
    markdown += '### Lineups\n'
    markdown += match_obj.home.lineup_str()
    markdown += match_obj.away.lineup_str()
    if 'next pro' not in comp.lower():
        if match_obj.started:
            markdown += stats_table(match_obj)
        if len(match_obj.summary) > 0:
            markdown += '---\n\n### Match Events\n'
            for comment in match_obj.summary:
                markdown += f'- {comment}\n'
        videos = video_highlights(match_obj)
        if videos is not None:
            markdown += videos
    markdown += match_footer(match_obj)
    return title, markdown


def post_match_thread(match_obj: match.Match):
    home = match_obj.home
    away = match_obj.away
    comp = match_obj.comp
    date, time = match_obj.get_date_time()
    # TODO this will eventually need to handle different values
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    # TODO add period/result type
    title = f'Post-Match Thread: {home.full_name} {home.goals}-{away.goals} '
    # TODO if pens, add to title here
    title += f'{away.full_name} '
    # TODO is this necessary in the title?
    if match_obj.is_aggregate:
        title += f'({home.goals+home.previous_goals}-{away.goals+away.previous_goals} aggregate) '
    title += f'({comp}) [{date}]'
    markdown = match_header(match_obj)
    markdown += '### Lineups\n'
    markdown += match_obj.home.lineup_str()
    markdown += match_obj.away.lineup_str()
    markdown += stats_table(match_obj)
    videos = video_highlights(match_obj)
    if videos is not None:
        markdown += videos
    markdown += match_footer(match_obj)
    return title, markdown


def stats_table(match_obj: match.Match):
    """Format stats table based on /u/matchcaster
    https://www.reddit.com/r/MLS/comments/z2x0xs/match_thread_belgium_vs_canada/
    """
    home = match_obj.home
    away = match_obj.away
    markdown = '---\n\n### Match Stats:\n'
    table_header = ''
    if home.short_name == '' or away.short_name == '':
        table_header = f'{home.full_name}|{home.goals}-{away.goals}|{away.full_name}'
    else:
        # both short names are populated
        table_header = f'{home.short_name}|{home.goals}-{away.goals}|{away.short_name}'
    table_header += '\n:-:|:-:|:-:'
    markdown += table_header
    markdown += f'\n{home.possession_percentage}%|Ball Possession|{away.possession_percentage}%'
    markdown += f'\n{home.total_scoring_att}|Total Shots|{away.total_scoring_att}'
    markdown += f'\n{home.ontarget_scoring_att}|Shots on Target|{away.ontarget_scoring_att}'
    markdown += f'\n{home.corner_taken}|Corner Kicks|{away.corner_taken}'
    markdown += f'\n{home.total_offside}|Offside|{away.total_offside}'
    markdown += f'\n{home.fk_foul_lost}|Fouls|{away.fk_foul_lost}'
    markdown += f'\n{home.yellow_card}|Yellow Cards|{away.yellow_card}'
    markdown += f'\n{home.red_card}|Red Cards|{away.red_card}'
    markdown += f'\n{home.saves}|Goalkeeper Saves|{away.saves}'
    markdown += f'\n{"%.2f" % home.expected_goals}|Expected Goals (xG)|{"%.2f" % away.expected_goals}'
    markdown += f'\n{home.total_pass}|Total Passes|{away.total_pass}'
    markdown += f'\n{home.pass_accuracy}%|Pass Accuracy|{away.pass_accuracy}%'
    markdown += '\n'
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
