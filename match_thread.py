import match
import time

def match_footer():
    retval = '\n\n---\n'
    retval += '^^Last ^^updated: '
    update = time.strftime('^^%b ^^%d, ^^%I:%M%p', time.localtime())
    retval += update
    return retval


def match_header(match_obj: match.Match):
    """Create a match thread header (used by all types of thread)"""
    home = match_obj.home.name
    away = match_obj.away.name
    comp = match_obj.comp
    date, time = match_obj.get_date_time()
    venue = match_obj.venue
    header = f'# {home} vs. {away}\n'
    header += f'### Match Info\n'
    header += f'**Competition:** {comp}\n\n'
    header += f'**Date:** {date}\n\n'
    header += f'**Time:** {time}\n\n'
    header += f'**Venue:** {venue}\n\n---\n'
    return header


def pre_match_thread(match_obj: match.Match):
    """Generate markdown for a pre-match thread."""
    match_obj = match.get_match_data(match_obj)
    home = match_obj.home.name
    away = match_obj.away.name
    comp = match_obj.comp
    # TODO this will eventually need to handle different values
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    title = f'Pre-Match Thread: {home} vs. {away} ({comp})'
    match_info = match_header(match_obj)
    match_obj = match.get_preview(match_obj)
    match_info += '### Match Facts\n'
    for comment in match_obj.preview:
        match_info += comment + '\n\n'
    match_info += match_footer()
    return title, match_info


def match_thread(match_obj: match.Match):
    match_obj = match.get_match_data(match_obj)
    match_obj = match.get_lineups(match_obj)
    home = match_obj.home.name
    away = match_obj.away.name
    comp = match_obj.comp
    # TODO this will eventually need to handle different values
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    # TODO add date to title?
    title = f'Match Thread: {home} vs. {away} ({comp})'
    match_info = match_header(match_obj)
    match_info += '### Lineups\n'
    match_info += match_obj.home.lineup_str()
    match_info += match_obj.away.lineup_str()
    match_info += '---\n'
    match_obj = match.get_feed(match_obj)
    match_info += '### Match Events\n'
    print(len(match_obj.feed))
    for comment in match_obj.feed:
        match_info += comment + '\n\n'
    match_info += match_footer()
    return title, match_info


def post_match_thread(match_obj: match.Match):
    return None


def main():
    opta_id = 2261385
    match_obj = match.Match(opta_id)
    title, markdown = match_thread(match_obj)
    print(markdown)


if __name__ == '__main__':
    main()
