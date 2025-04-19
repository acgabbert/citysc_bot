from collections import defaultdict
import time
from typing import Dict, List, Optional
from match_sportec import Match
from models.event import SubstitutionEvent
from models.person import BasePerson

def generate_match_header(match_obj: Match, pre: bool = False) -> str:
    """Creates the main header markdown for a match thread."""
    home = match_obj.data.match_info.home
    away = match_obj.data.match_info.away
    header_parts = []

    if pre:
        # Pre-match thread
        header_parts.append(f"{home.fullName} vs. {away.fullName}")
        header_parts.append(generate_match_info(match_obj))

def generate_match_info(match_obj: Match) -> Optional[str]:
    """Generate the "Match Info" section for pre-match threads."""
    date, time_str = match_obj.get_date_time()
    info_lines = [
        "### Match Info",
        f"- **Competition:** {match_obj.data.match_base.match_information.competition_name}",
        f"_ **Date:** {date}",
        f"- **Time:** {time_str}",
        f"- **Venue:** {match_obj.data.match_info.venue.name}"
    ]

    tv_streaming = "No data via mlssoccer.com."
    pass

def generate_match_footer(match_obj: Match) -> str:
    footer = "Last Updated: "
    update = time.strftime('%b %d, %I:%M%p', time.localtime())
    footer += update + f'. All data via mlssoccer.com. Match ID: {str(match_obj.sportec_id)}'
    retval += f'^({footer})'
    return retval

def generate_match_stats(match_obj: Match) -> str:
    home_display = match_obj.home.abbreviation or match_obj.home.shortName or match_obj.home.fullName
    away_display = match_obj.away.abbreviation or match_obj.away.shortName or match_obj.away.fullName

    header = f"{home_display}|{match_obj.home_goals}-{match_obj.away_goals}|{away_display}"
    header += "\n:-:||:-:|:-:"

    markdown = f"### Match Stats:\n{header}"
    markdown += add_stat(match_obj, 'possession_ratio', 'Ball Possession', True)
    markdown += add_stat(match_obj, 'shots_at_goal_sum', 'Total Shots')
    markdown += add_stat(match_obj, 'shots_on_target', 'Shots on Target')
    markdown += add_stat(match_obj, 'corner_kicks_sum', 'Corner Kicks')
    markdown += add_stat(match_obj, 'offsides', 'Offsides')
    markdown += add_stat(match_obj, 'fouls_sum', 'Fouls')
    markdown += add_stat(match_obj, 'cards_yellow', 'Yellow Cards')
    markdown += add_stat(match_obj, 'cards_red', 'Red Cards')
    markdown += add_stat(match_obj, 'goalkeeper_saves', 'Saves')
    markdown += add_stat(match_obj, 'xG', 'Expected Goals (xG)')
    markdown += add_stat(match_obj, 'passes_from_play_successful', 'Successful Passes')
    markdown += add_stat(match_obj, 'passes_sum', 'Total Passes')
    markdown += add_stat(match_obj, 'passes_from_play_conversion_rate', 'Pass Accuracy', True)
    
    return markdown

def generate_lineups(match_obj: Match) -> str:
    starting_lineups = match_obj.get_starting_lineups()
    subs = match_obj.get_subs()
    home_lineup = generate_team_lineup(starting_lineups[match_obj.home_id], subs.get(match_obj.home_id))
    away_lineup = generate_team_lineup(starting_lineups[match_obj.away_id], subs.get(match_obj.away_id))
    if len(starting_lineups[match_obj.home_id]) < 1:
        home_lineup = "Not yet available via mlssoccer.com."
    if len(starting_lineups[match_obj.away_id]) < 1:
        away_lineup = "Not yet available via mlssoccer.com."
    return "\n".join([
        "### Lineups",
        f"**{match_obj.home.fullName}**: {home_lineup}"
        "",
        f"**{match_obj.away.fullName}**: {away_lineup}"
    ])

def generate_team_lineup(lineup: List[BasePerson], subs: List[SubstitutionEvent]) -> str:
    retval = []
    subs_mapping: Dict[str, SubstitutionEvent] = {}
    for s in subs:
        print(s)
        subs_mapping[s.event.player_out_id] = s
    for p in lineup:
        if p.person_id in subs_mapping:
            retval.append(format_sub_event(subs_mapping.get(p.person_id)))
        else:
            retval.append(str(p))
    
    return ", ".join(retval)

def format_sub_event(event: SubstitutionEvent) -> str:
    event_details = event.event
    return f"{event_details.player_out_first_name} {event_details.player_out_last_name} ({event_details.player_in_first_name} {event_details.player_in_last_name} {event_details.minute_of_play}')"


def add_stat(match_obj: Match, stat: str, display: str = None, isPercentage=False) -> str:
    if hasattr(match_obj.home_stats, stat) and hasattr(match_obj.away_stats, stat):
        home_stat = getattr(match_obj.home_stats, stat)
        away_stat = getattr(match_obj.away_stats, stat)

        if isinstance(home_stat, float) and isPercentage:
            if home_stat < 1:
                home_stat *= 100
        if isinstance(away_stat, float) and isPercentage:
            if away_stat < 1:
                away_stat *= 100
        retval = f"\n{home_stat:g}{'%' if isPercentage else ''}"
        retval += f"|{display}|{away_stat:g}{'%' if isPercentage else ''}"
        return retval
    return ""