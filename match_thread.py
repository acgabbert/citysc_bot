import match
import time

def match_footer():
    retval = '\n\n---\n'
    retval += '^^Last ^^updated: '
    update = time.strftime('^^%b ^^%d, ^^%I:%M%p', time.localtime())
    retval += update
    return retval


def pre_match_thread(opta_id):
    """Generate markdown for a pre-match thread."""
    match_data = match.get_match_data(opta_id)
    match_data = match_data[0]
    home = match_data['home_club']['name']
    away = match_data['away_club']['name']
    comp = match_data['competition']['name']
    title = 'Pre-Match Thread: {} vs. {} ({comp})'
    # from the api, date comes as epoch time in milliseconds
    date = int(match_data['date']) / 1000
    date = time.strptime(time.ctime(date))
    date_val = time.strftime('%B %d, %Y', date)
    time_val = time.strftime('%I:%M%p', date)
    # remove leading zero from time
    if time_val[0] == '0':
        time_val = time_val[1:]
    venue = match_data['venue']['name']
    # TODO this needs to handle different values too
    if comp == 'US Major League Soccer':
        comp = 'MLS Regular Season'
    title = f'Pre-Match Thread: {home} vs. {away} ({comp})'
    header = f'# {home} vs. {away}\n'
    match_info = header
    match_info += f'### Match Info\n'
    match_info += f'**Competition:** {comp}\n\n'
    match_info += f'**Date:** {date_val}\n\n'
    match_info += f'**Time:** {time_val}\n\n'
    match_info += f'**Venue:** {venue}\n\n---\n'
    comments = match.get_preview(opta_id)
    match_info += '### Match Facts\n'
    for comment in comments:
        match_info += comment + '\n\n'
    return title, match_info


def post_match_thread(opta_id):
    return None

def main():
    title, markdown = pre_match_thread('2261385')
    print(markdown)
    print(match_footer())


if __name__ == '__main__':
    main()
