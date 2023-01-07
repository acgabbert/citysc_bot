import match
import time

def match_footer():
    retval = '\n\n---\n'
    retval += '^^Last ^^updated: '
    update = time.strftime('^^%b ^^%d, ^^%I:%M%p', time.localtime())
    retval += update
    return retval


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
    date, time = match_obj.get_date_time()
    venue = match_obj.venue
    header = f'# {home} vs. {away}\n'
    match_info = header
    match_info += f'### Match Info\n'
    match_info += f'**Competition:** {comp}\n\n'
    match_info += f'**Date:** {date}\n\n'
    match_info += f'**Time:** {time}\n\n'
    match_info += f'**Venue:** {venue}\n\n---\n'
    match_obj = match.get_preview(match_obj)
    match_info += '### Match Facts\n'
    for comment in match_obj.preview:
        match_info += comment + '\n\n'
    return title, match_info


def post_match_thread(opta_id):
    return None

def main():
    opta_id = 2261385
    match_obj = match.Match(opta_id)
    title, markdown = pre_match_thread(match_obj)
    print(markdown)
    print(match_footer())


if __name__ == '__main__':
    main()
