from typing import Optional
from match_sportec import Match

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