import argparse
import asyncio
import logging
import os
import sys
import time
from typing import Dict, List, Optional

import config
from match import Match
from models.event import SubstitutionEvent
from models.person import BasePerson

logger = logging.getLogger(__name__)

def _club_logo_markdown(club, size: int = 32) -> str:
    """Return inline Reddit image markdown for a club logo, or empty string if unavailable."""
    logo_url = club.get_logo_url(width=size, height=size)
    if not logo_url:
        return ""
    return f"![{club.abbreviation or club.shortName or club.fullName}]({logo_url})"

def generate_match_header(match_obj: Match, pre: bool = False) -> str:
    """Creates the main header markdown for a match thread."""
    home = match_obj.data.match_info.home
    away = match_obj.data.match_info.away
    joiner_string = "vs." if pre else match_obj.get_score()

    result_string = ""
    if not pre:
        result_type = match_obj.get_result_type()
        result_string = result_type or match_obj.get_status_display()

    home_display = home.fullName
    away_display = away.fullName
    seeds = match_obj.get_seeds()
    if seeds:
        home_display = f"#{seeds[match_obj.home_id]} {home_display}"
        away_display = f"#{seeds[match_obj.away_id]} {away_display}"
    if config.FEATURE_FLAGS.get('enable_inline_logos', False):
        home_logo = _club_logo_markdown(home)
        away_logo = _club_logo_markdown(away)
        if home_logo:
            home_display = f"{home_logo} {home_display}"
        if away_logo:
            away_display = f"{away_display} {away_logo}"

    prefix = f"{result_string}: " if result_string else ""
    header_parts = [f"## {prefix}{home_display} {joiner_string} {away_display}"]

    if pre:
        header_parts.append(generate_match_info(match_obj))
    else:
        round_line = generate_round_line(match_obj)
        if round_line:
            header_parts.append(round_line)

    return "\n".join(header_parts)

def generate_round_line(match_obj: Match) -> Optional[str]:
    """Playoff round and series status under the match/post-match header,
    e.g. "**Round One, Game 2 of 3** | San Diego FC leads the series 1-0"."""
    playoff_round = match_obj.get_playoff_round()
    if playoff_round is None:
        return None
    line = f"**{playoff_round}**"
    status = match_obj.get_series_status()
    if status:
        line += f" | {status}"
    return line

def generate_match_info(match_obj: Match) -> Optional[str]:
    """Generate the "Match Info" section for pre-match threads."""
    date = match_obj.get_local_date_string()
    time_str = match_obj.get_local_time_string()
    info_lines = ["### Match Info", f"- **Competition:** {match_obj.competition}"]
    playoff_round = match_obj.get_playoff_round()
    if playoff_round is not None:
        round_str = str(playoff_round)
        status = match_obj.get_series_status(include_current=False)
        if status:
            round_str += f" ({status})"
        info_lines.append(f"- **Round:** {round_str}")
    info_lines += [
        f"- **Date:** {date}",
        f"- **Time:** {time_str}",
        f"- **Venue:** {match_obj.data.match_info.venue.name}",
        "",
        f"TV/Streaming: {generate_broadcasters(match_obj)}"
    ]
    return "\n".join(info_lines)

def generate_scorers(match_obj: Match) -> Optional[str]:
    """Generate scorer display for match/post-match threads."""
    scorers = match_obj.get_goalscorers()
    if not scorers:
        return None

    home_display = match_obj.home.abbreviation or match_obj.home.shortName or match_obj.home.fullName
    away_display = match_obj.away.abbreviation or match_obj.away.shortName or match_obj.away.fullName

    lines = []
    home_scorers = scorers.get(match_obj.home_id, [])
    away_scorers = scorers.get(match_obj.away_id, [])

    if home_scorers:
        lines.append(f"\u26bd **{home_display}:** {', '.join(home_scorers)}")
    if away_scorers:
        lines.append(f"\u26bd **{away_display}:** {', '.join(away_scorers)}")

    return "\n".join(lines) if lines else None

def _team_display(match_obj: Match, team_id: str) -> str:
    club = match_obj.home if team_id == match_obj.home_id else match_obj.away
    return club.abbreviation or club.shortName or club.fullName

def _format_kick(kick) -> str:
    if kick.scored:
        return f"\u2705 {kick.taker}"
    return f"\u274c {kick.taker}{' (saved)' if kick.saved else ''}"

def generate_shootout(match_obj: Match) -> Optional[str]:
    """Kick-by-kick penalty shootout table for match/post-match threads."""
    shootout = match_obj.get_shootout()
    if shootout is None:
        return None
    home_kicks = shootout.get(match_obj.home_id, [])
    away_kicks = shootout.get(match_obj.away_id, [])
    home_display = _team_display(match_obj, match_obj.home_id)
    away_display = _team_display(match_obj, match_obj.away_id)
    lines = [
        "### Penalty Shootout",
        f"| {home_display} | | {away_display} |",
        "| :---: | :---: | :---: |",
    ]
    for i in range(max(len(home_kicks), len(away_kicks))):
        home = _format_kick(home_kicks[i]) if i < len(home_kicks) else ""
        away = _format_kick(away_kicks[i]) if i < len(away_kicks) else ""
        lines.append(f"| {home} | {i + 1} | {away} |")
    if not home_kicks and not away_kicks:
        lines.append("| | Shootout underway | |")
    return "\n".join(lines)

def generate_series_games(match_obj: Match) -> Optional[str]:
    """Results of earlier games in a best-of-3 series, linked to their threads."""
    if not match_obj.series_games:
        return None
    names = {match_obj.home_id: match_obj.home.fullName, match_obj.away_id: match_obj.away.fullName}
    threads = match_obj.series_threads or {}
    lines = ["### Series So Far"]
    for game in match_obj.series_games:
        line = (f"- **Game {game.game}:** {names.get(game.home_id, game.home_id)} "
                f"{game.home_goals}-{game.away_goals} {names.get(game.away_id, game.away_id)}")
        if game.home_pens is not None and game.away_pens is not None:
            line += f" ({game.home_pens}-{game.away_pens} pens)"
        thread_id = threads.get(game.match_id)
        if thread_id:
            line += f" ([thread](https://www.reddit.com/comments/{thread_id}))"
        lines.append(line)
    return "\n".join(lines)

def generate_next_match(match_obj: Match) -> Optional[str]:
    """The next match line for post-match threads, e.g. "**Next:** Portland
    Timbers vs. San Diego FC (MLS Cup Playoffs – Round One, Game 2 of 3) –
    Saturday, November 1, 8:30 PM CDT".
    """
    next_match = match_obj.next_match
    if next_match is None:
        return None
    tbd = (match_obj.next_match_tbd or '').lower()
    kickoff = next_match.get_local_datetime()
    if 'day' in tbd or kickoff is None:
        when = "date and time TBD"
    else:
        when = f"{kickoff:%A, %B} {kickoff.day}"
        if tbd or next_match.is_time_tbd():
            when += ", time TBD"
        else:
            when += f", {next_match.get_local_time_string().lstrip('0')}"
    return (f"**Next:** {next_match.home.fullName} vs. {next_match.away.fullName} "
            f"({next_match.get_competition_display()}) \u2013 {when}")

def generate_post_match_info(match_obj: Match) -> Optional[str]:
    """Next match, highlights link and attendance for post-match threads."""
    lines = []
    next_line = generate_next_match(match_obj)
    if next_line:
        lines.append(next_line)
    if match_obj.highlights_url:
        lines.append(f"\U0001f3a5 [Match highlights]({match_obj.highlights_url})")
    attendance = match_obj.get_attendance()
    if attendance:
        lines.append(f"**Attendance:** {attendance:,}")
    return "\n\n".join(lines) if lines else None

def generate_match_footer(match_obj: Match) -> str:
    footer = "Last Updated: "
    update = time.strftime('%b %d, %I:%M%p', time.localtime())
    footer += update + f'. All data via mlssoccer.com. Match ID: {str(match_obj.sportec_id)}'
    return f'^({footer})'

def generate_match_stats(match_obj: Match) -> Optional[str]:
    # Any competition the stats API covers (playoffs, cups) gets a table;
    # matches it doesn't cover have no stats and are skipped below.
    if match_obj.home_stats is None or match_obj.away_stats is None:
        return None
    home_display = match_obj.home.abbreviation or match_obj.home.shortName or match_obj.home.fullName
    away_display = match_obj.away.abbreviation or match_obj.away.shortName or match_obj.away.fullName

    header = f"| {home_display} | {match_obj.home_goals}-{match_obj.away_goals} | {away_display} |"
    header += "\n| :---: | :---: | :---: |"

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

    if markdown.endswith(":---:"):
        return None
    return markdown

def generate_lineups(match_obj: Match) -> str:
    starting_lineups = match_obj.get_starting_lineups()
    subs = match_obj.get_subs()
    home_lineup = "Not yet available via mlssoccer.com."
    away_lineup = "Not yet available via mlssoccer.com."
    if starting_lineups:
        cards = match_obj.get_cards()
        home_lineup = generate_team_lineup(getattr(match_obj.data.match_base.home, "players", []), subs.get(match_obj.home_id, []), cards)
        away_lineup = generate_team_lineup(getattr(match_obj.data.match_base.away, "players", []), subs.get(match_obj.away_id, []), cards)
        if len(starting_lineups[match_obj.home_id]) < 1:
            home_lineup = "Not yet available via mlssoccer.com."
        if len(starting_lineups[match_obj.away_id]) < 1:
            away_lineup = "Not yet available via mlssoccer.com."
    return "\n".join([
        "### Lineups",
        f"**{match_obj.home.fullName}**:",
        home_lineup,
        "",
        f"**{match_obj.away.fullName}**:",
        away_lineup,
    ])

def generate_team_lineup(lineup: List[BasePerson], subs: List[SubstitutionEvent],
                         cards: Optional[Dict[str, List[str]]] = None) -> str:
    """Starters (with subs and cards inline), then the bench. A player who came
    on is listed with any cards on the bench line."""
    if not lineup:
        return "Not yet available via mlssoccer.com."
    cards = cards or {}
    starters = []
    bench = []
    subs_mapping: Dict[str, SubstitutionEvent] = {}
    for s in subs:
        subs_mapping[s.event.player_out_id] = s
    for p in lineup:
        player = str(p)
        if cards.get(p.person_id):
            player += " " + " ".join(cards[p.person_id])
        if p.person_id in subs_mapping:
            starters.append(format_sub_event(subs_mapping.get(p.person_id), player))
        elif p.starting:
            starters.append(player)
        else:
            bench.append(player)

    parts = [", ".join(starters)]
    if bench:
        parts.append("")
        parts.append("*Subs:* " + ", ".join(bench))
    return "\n".join(parts)

def format_sub_event(event: SubstitutionEvent, player_out: Optional[str] = None) -> str:
    """'Player Out (🔄 Player In 70')'; player_out replaces the name from the event."""
    event_details = event.event
    if player_out is None:
        player_out = f"{event_details.player_out_first_name} {event_details.player_out_last_name}"
    return f"{player_out} (\U0001f504 {event_details.player_in_first_name} {event_details.player_in_last_name} {event_details.minute_of_play}')"


def add_stat(match_obj: Match, stat: str, display: str = None, isPercentage=False) -> str:
    home_stat = getattr(match_obj.home_stats, stat, None)
    away_stat = getattr(match_obj.away_stats, stat, None)
    if home_stat is not None and away_stat is not None:
        logger.debug(f"attr {stat} is valid")

        if isinstance(home_stat, float) and isPercentage:
            if home_stat < 1:
                home_stat *= 100
        if isinstance(away_stat, float) and isPercentage:
            if away_stat < 1:
                away_stat *= 100
        retval = f"\n| {home_stat:g}{'%' if isPercentage else ''}"
        retval += f" | {display} | {away_stat:g}{'%' if isPercentage else ''} |"
        return retval
    return ""

def generate_broadcasters(match_obj: Match) -> str:
    broadcasters = match_obj.get_broadcasters()
    if not broadcasters:
        return "No data via mlssoccer.com."

    retval = []

    for b in broadcasters:
        disp = b.broadcasterName
        if "Apple" in disp and match_obj.data.match_info.appleStreamURL:
            disp = f"[{disp}]({match_obj.data.match_info.appleStreamURL})"
        retval.append(disp)

    return ", ".join(retval)

def generate_previous_matchups(match_obj: Match) -> Optional[str]:
    return None

def generate_injuries(match_obj: Match) -> Optional[str]:
    """Generate injury report section for pre-match threads."""
    if not match_obj.injuries:
        return None

    lines = ["### Injury Report"]
    for team_id, team_name in [(match_obj.home_id, match_obj.home.fullName), (match_obj.away_id, match_obj.away.fullName)]:
        opta_id = match_obj._sportec_to_opta.get(team_id)
        if opta_id and opta_id in match_obj.injuries:
            injury_list = match_obj.injuries[opta_id]
            if injury_list:
                lines.append(f"**{team_name}:** {', '.join(injury_list)}")

    return "\n\n".join(lines) if len(lines) > 1 else None

def generate_discipline(match_obj: Match) -> Optional[str]:
    """Generate discipline section for pre-match threads."""
    if not match_obj.discipline:
        return None

    lines = ["### Discipline"]
    for team_id, team_name in [(match_obj.home_id, match_obj.home.fullName), (match_obj.away_id, match_obj.away.fullName)]:
        opta_id = match_obj._sportec_to_opta.get(team_id)
        if opta_id and opta_id in match_obj.discipline:
            team_disc = match_obj.discipline[opta_id]
            if team_disc:
                parts = []
                for reason, players in team_disc.items():
                    if isinstance(players, list):
                        parts.append(f"{reason}: {', '.join(players)}")
                    else:
                        parts.append(f"{reason}: {players}")
                if parts:
                    lines.append(f"**{team_name}:** {'; '.join(parts)}")

    return "\n\n".join(lines) if len(lines) > 1 else None

def pre_match_thread(match_obj: Match):
    """
    Generate markdown for a pre-match thread.
    """
    home = match_obj.home.fullName
    away = match_obj.away.fullName
    comp = match_obj.get_competition_display()
    date = match_obj.get_local_date_string()

    title = f'Matchday Thread: {home} vs. {away} ({comp}) [{date}]'

    markdown_components = [
        generate_match_header(match_obj, pre=True),
        generate_series_games(match_obj),
        generate_previous_matchups(match_obj),
        generate_injuries(match_obj),
        generate_discipline(match_obj),
        generate_match_footer(match_obj)
    ]

    valid_markdown_components = [
        component for component in markdown_components if component is not None
    ]

    return title, "\n\n".join(valid_markdown_components)

def match_thread(match_obj: Match):
    """
    Generate markdown for a match thread.
    """
    home = match_obj.home.fullName
    away = match_obj.away.fullName
    comp = match_obj.get_competition_display()
    date = match_obj.get_local_date_string()

    title = f'Match Thread: {home} vs. {away} ({comp}) [{date}]'

    markdown_components = [
        generate_match_header(match_obj),
        generate_scorers(match_obj),
        generate_shootout(match_obj),
        generate_lineups(match_obj),
        generate_match_stats(match_obj),
        generate_series_games(match_obj),
        generate_match_footer(match_obj)
    ]

    valid_markdown_components = [
        component for component in markdown_components if component is not None
    ]

    return title, "\n\n".join(valid_markdown_components)

def post_match_thread(match_obj: Match):
    """
    Generate markdown for a post-match thread.
    """
    home = match_obj.home.fullName
    away = match_obj.away.fullName
    comp = match_obj.get_competition_display()
    date = match_obj.get_local_date_string()

    title = f'Post-Match Thread: {home} vs. {away} ({comp}) [{date}]'

    markdown_components = [
        generate_match_header(match_obj),
        generate_post_match_info(match_obj),
        generate_scorers(match_obj),
        generate_shootout(match_obj),
        generate_lineups(match_obj),
        generate_match_stats(match_obj),
        generate_series_games(match_obj),
        generate_match_footer(match_obj)
    ]

    valid_markdown_components = [
        component for component in markdown_components if component is not None
    ]

    return title, "\n\n".join(valid_markdown_components)


THREAD_TYPES = {
    'pre': pre_match_thread,
    'match': match_thread,
    'post': post_match_thread,
}


async def dry_run(sportec_id: str, thread_type: str = 'match', output_dir: str = 'data') -> str:
    """Generate match markdown and save to a file without posting to Reddit."""
    from api_client import MLSApiClient

    generator = THREAD_TYPES[thread_type]

    async with MLSApiClient() as client:
        match_obj = await Match.create(sportec_id, client=client)

    title, body = generator(match_obj)

    os.makedirs(output_dir, exist_ok=True)
    filename = f"{thread_type}_{sportec_id}.md"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w') as f:
        f.write(f"# {title}\n\n")
        f.write(body)

    return filepath


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='match_markdown.py',
        description='Generate match thread markdown (dry run, no Reddit posting)'
    )
    parser.add_argument('-i', '--id', required=True, help='Match Sportec ID')
    parser.add_argument('-t', '--type', choices=['pre', 'match', 'post'], default='match',
                        help='Thread type (default: match)')
    parser.add_argument('-o', '--output', default='data',
                        help='Output directory (default: data)')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    filepath = asyncio.run(dry_run(args.id, args.type, args.output))
    print(f'Markdown saved to {filepath}')
