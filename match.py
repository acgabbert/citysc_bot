from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
import os
import re
from typing import Dict, List, Optional
import config
from api_client import MLSApiClient
from models.club import Club_Sport
from models.constants import MlsCompetition
from models.event import CardEvent, EventDetails, MlsEvent, PenaltyEvent, SubstitutionEvent
from models.match import ComprehensiveMatchData
from models.person import BasePerson
from models.schedule import Broadcaster, Competition
from models.team_stats import TeamStats
from models.venue import MatchVenue
import util

logger = logging.getLogger(__name__)

PLAYOFFS_COMPETITION_ID = MlsCompetition.MLS_CUP_PLAYOFFS.competition_id

# MLS Cup Playoffs rounds: (display name, what the winner advances to)
_PLAYOFF_ROUNDS = {
    'wild_card': ('Wild Card', 'Round One'),
    'round_one': ('Round One', 'the Conference Semifinals'),
    'semifinal': ('Conference Semifinal', 'the Conference Final'),
    'final': ('Conference Final', 'MLS Cup'),
    'cup': ('MLS Cup', None),
}
# The sport API's roundNumber, used when roundName isn't a slug we know.
# Round One is roundNumber 2-4 (Games 1-3).
_PLAYOFF_ROUND_NUMBERS = {
    1: 'wild_card', 2: 'round_one', 3: 'round_one', 4: 'round_one',
    5: 'semifinal', 6: 'final', 7: 'cup',
}
ROUND_ONE_GAMES = 3


def _playoff_round_key(round_name: Optional[str], round_number: Optional[int]) -> Optional[str]:
    """Map the sport API's roundName slug (or roundNumber) to a _PLAYOFF_ROUNDS key.

    The slugs change between seasons ('match-round-bo3' in 2025, 'best_of_3'
    in 2026), so match loosely and fall back to roundNumber.
    """
    slug = (round_name or '').lower()
    if 'wild' in slug:
        return 'wild_card'
    if 'bo3' in slug or 'best_of' in slug or 'best-of' in slug:
        return 'round_one'
    if 'semi' in slug:
        return 'semifinal'
    if 'final' in slug:
        return 'final'
    if 'cup' in slug:
        return 'cup'
    return _PLAYOFF_ROUND_NUMBERS.get(round_number)


@dataclass
class PlayoffRound:
    name: str
    next_round: Optional[str] = None
    game: Optional[int] = None
    best_of: Optional[int] = None

    @property
    def is_series(self) -> bool:
        return self.best_of is not None

    def __str__(self) -> str:
        if self.is_series and self.game:
            return f"{self.name}, Game {self.game} of {self.best_of}"
        return self.name


@dataclass
class SeriesGame:
    """An earlier, finished game in a best-of-3 series."""
    game: int
    match_id: str
    home_id: str
    away_id: str
    home_goals: int
    away_goals: int
    winner_id: str
    home_pens: Optional[int] = None
    away_pens: Optional[int] = None


@dataclass
class ShootoutKick:
    taker: str
    scored: bool
    # The API's shot_result for a miss, e.g. "SavedShot"
    shot_result: Optional[str] = None

    @property
    def saved(self) -> bool:
        return self.shot_result == 'SavedShot'


# card_color / card_rating values from the events API
CARD_EMOJI = {
    'yellow': '\U0001f7e8',
    'yellowRed': '\U0001f7e8\U0001f7e5',  # second yellow
    'red': '\U0001f7e5',
}

# Full-match highlight videos have slugs like
# "highlights-st-louis-city-sc-vs-la-galaxy-october-11-2026"
HIGHLIGHTS_SLUG_PREFIX = 'highlights-'
# How far ahead to look for the next match
NEXT_MATCH_WINDOW = timedelta(days=60)
VIDEO_URL = 'https://www.mlssoccer.com/video/{slug}'


class Match:
    data: Optional[ComprehensiveMatchData] = None
    home: Optional[Club_Sport] = None
    away: Optional[Club_Sport] = None
    competition: Optional[str] = None
    slug: Optional[str] = None
    minute_display: Optional[str] = None
    home_id: Optional[str] = None
    away_id: Optional[str] = None
    home_stats: Optional[TeamStats] = None
    away_stats: Optional[TeamStats] = None
    home_goals: int = 0
    away_goals: int = 0
    home_starters: List[BasePerson] = None
    away_starters: List[BasePerson] = None
    injuries: Optional[Dict] = None
    discipline: Optional[Dict] = None
    # Winner team IDs of earlier games in a best-of-3 series, oldest first.
    # None until loaded (or if they couldn't be worked out).
    series_winners: Optional[List[str]] = None
    # The same earlier games with their scores, oldest first.
    series_games: Optional[List[SeriesGame]] = None
    # Reddit thread IDs of earlier series games, by match ID: set by
    # match_thread.py from threads.json, used to link them.
    series_threads: Optional[Dict[str, str]] = None
    # mlssoccer.com page for the full-match highlights, once it's published
    highlights_url: Optional[str] = None
    # The followed team's next match (sport API data only), for post-match
    # threads, and its schedule status if the date or time is TBD
    next_match: Optional['Match'] = None
    next_match_tbd: Optional[str] = None
    _sportec_to_opta: Dict[str, str] = None

    def __init__(self, sportec_id: str):
        self.sportec_id = sportec_id
        self._sportec_to_opta = {
            entry.sportec_id: str(opta_id)
            for opta_id, entry in util.names.items()
            if entry.sportec_id
        }
    
    async def _fetch_data(self, client: Optional[MLSApiClient] = None) -> ComprehensiveMatchData:
        if client is not None:
            data = await client.get_all_match_data(self.sportec_id)
        else:
            async with MLSApiClient() as new_client:
                data = await new_client.get_all_match_data(self.sportec_id)
        if data.errors:
            logger.error("\n".join(data.errors))
        return data

    @classmethod
    async def create(cls, sportec_id: str, client: Optional[MLSApiClient] = None):
        match = cls(sportec_id)
        data = await match._fetch_data(client)
        if data.match_info is None:
            raise ValueError(f"Failed to fetch match_info for {sportec_id}")
        match.data = data
        match._process_data(data)
        match.update_injuries()
        match.update_discipline()
        await match._load_series(client)
        return match

    async def refresh(self, client: Optional[MLSApiClient] = None):
        data = await self._fetch_data(client)
        self.data = data
        self._process_data(data)
        await self._load_series(client)
    
    def _process_data(self, data: ComprehensiveMatchData) -> None:
        """
        Process comprehensive match data for easier access from other functions.
        """
        if data.match_info is None:
            logger.warning("match_info is None, skipping _process_data")
            return
        self.home = data.match_info.home
        self.home_id = self.home.sportecId
        self.away = data.match_info.away
        self.away_id = self.away.sportecId
        self.competition = data.match_info.competition.shortName or data.match_info.competition.name
        self.slug = data.match_info.slug
        if self.is_started() and data.match_base is not None:
            self.home_goals = data.match_base.match_information.home_team_goals
            self.away_goals = data.match_base.match_information.away_team_goals
            self.minute_display = data.match_base.match_information.minute_of_play
        
        if data.match_stats is not None:
            for stats in data.match_stats.team_statistics:
                if stats.team_id == self.home_id:
                    self.home_stats = stats
                    continue
                if stats.team_id == self.away_id:
                    self.away_stats = stats
                    continue
                logger.info(f"Team {stats.team_id} ({stats.team_name}) does not match home or away.")
        
        lineups = self.get_starting_lineups()
        self.home_starters = lineups.get(self.home_id, [])
        self.away_starters = lineups.get(self.away_id, [])
    
    def update_injuries(self) -> None:
        inj_file = 'data/injuries.json'
        if not os.path.exists(inj_file):
            logger.warning(f"{inj_file} not found, skipping injury data")
            return
        try:
            data = util.read_json(inj_file)
            self.injuries = data.get('injuries', {})
        except Exception as e:
            logger.warning(f"Failed to read injury data: {e}")
            self.injuries = {}

    def update_discipline(self) -> None:
        disc_file = 'data/discipline.json'
        if not os.path.exists(disc_file):
            logger.warning(f"{disc_file} not found, skipping discipline data")
            return
        try:
            data = util.read_json(disc_file)
            self.discipline = data.get('discipline', {})
        except Exception as e:
            logger.warning(f"Failed to read discipline data: {e}")
            self.discipline = {}
        
    def is_started(self) -> bool:
        if not self.data.match_base:
            return False
        
        if self.data.match_base.match_information.match_status in ['scheduled']:
            return False
        
        return True
        
    def is_final(self) -> bool:
        if not self.data.match_base:
            return False
        
        if self.data.match_base.match_information.match_status == 'finalWhistle':
            return True
        
        return False
    
    def get_utc_datetime(self) -> datetime | None:
        """
        Get the scheduled date and time of the match (UTC).
        """
        if not self.data.match_base:
            return None
        return self.data.match_base.match_information.planned_kickoff_time
    
    def get_local_datetime(self) -> datetime | None:
        """
        Get the scheduled date and time of the match (local).
        """
        return self.data.match_info.matchDate.astimezone()
    
    def get_local_date_string(self) -> str:
        """
        Get the local date string for the match.
        """
        date = self.get_local_datetime()
        if not date:
            return "Unknown"
        return date.strftime('%B %d, %Y')
        
        
    def is_time_tbd(self) -> bool:
        """True while the league hasn't set a kickoff time (matchDate is a placeholder)."""
        return bool(self.data.match_info and self.data.match_info.isTimeTbd)

    def get_local_time_string(self) -> str:
        """
        Get the local time string for the match, or "TBD" if the kickoff
        time hasn't been set.
        """
        if self.is_time_tbd():
            return "TBD"
        date = self.get_local_datetime()
        if not date:
            return "Unknown"
        # The zone name for the match date (CDT vs. CST), not for today
        return date.strftime('%I:%M %p %Z')

    def get_starting_lineups(self) -> Dict[str, List[BasePerson]]:
        """
        Retrieve the starting lineups for both teams.
        
        Returns:
            A dictionary mapping team IDs (str) to lists of starting players (BasePerson)
            Returns an empty dictionary if essential match data is missing.
        """
        lineups: Dict[str, List[BasePerson]] = {}
        if not self.data or not self.data.match_base:
            return lineups
        
        home_team = self.data.match_base.home
        away_team = self.data.match_base.away

        if home_team and home_team.team_id and hasattr(home_team, 'players') and home_team.players is not None:
            home_lineup = []
            try:
                home_lineup = [
                    p for p in home_team.players
                    if hasattr(p, 'starting') and p.starting
                ]
            except TypeError:
                logger.error(f"Failed to create starting lineup for team {home_team.team_name}")
            lineups[home_team.team_id] = home_lineup

        if away_team and away_team.team_id and hasattr(away_team, 'players') and away_team.players is not None:
            away_lineup = []
            try:
                away_lineup = [
                    p for p in away_team.players
                    if hasattr(p, 'starting') and p.starting
                ]
            except TypeError:
                logger.error(f"Failed to create starting lineup for team {away_team.team_name}")
            lineups[away_team.team_id] = away_lineup

        return lineups

    def get_playoff_round(self) -> Optional[PlayoffRound]:
        """The MLS Cup Playoffs round this match is in, or None for any other match."""
        info = self.data.match_info if self.data else None
        if info is None or info.competition.sportecId != PLAYOFFS_COMPETITION_ID:
            return None
        key = _playoff_round_key(info.roundName, info.roundNumber)
        if key is None:
            return None
        name, next_round = _PLAYOFF_ROUNDS[key]
        if key != 'round_one':
            return PlayoffRound(name, next_round)
        return PlayoffRound(name, next_round, game=self._series_game_number(), best_of=ROUND_ONE_GAMES)

    def _series_game_number(self) -> Optional[int]:
        """Game number within a Round One series.

        2025 data has roundGroup 'game_2' and match_type 'Match 2'; the 2026
        placeholders have neither, but roundNumber 2-4 is Games 1-3 either way.
        """
        info = self.data.match_info
        candidates = [info.roundGroup]
        if self.data.match_base is not None:
            candidates.append(self.data.match_base.match_information.match_type)
        for text in candidates:
            found = re.search(r'(?:game|match)[\s_-]*(\d)', text or '', re.IGNORECASE)
            if found:
                return int(found.group(1))
        if info.roundNumber in (2, 3, 4):
            return info.roundNumber - 1
        return None

    def get_competition_display(self) -> str:
        """Competition for thread titles, with the playoff round if there is one."""
        playoff_round = self.get_playoff_round()
        if playoff_round is None:
            return self.competition
        if playoff_round.name == 'MLS Cup':
            return 'MLS Cup'
        return f"{self.competition} \u2013 {playoff_round}"

    def get_seeds(self) -> Optional[Dict[str, int]]:
        """Playoff seeds by team ID, or None outside the playoffs or before they're set."""
        if self.get_playoff_round() is None:
            return None
        info = self.data.match_info
        if info.homeClubRank is None or info.awayClubRank is None:
            return None
        return {self.home_id: info.homeClubRank, self.away_id: info.awayClubRank}

    def get_attendance(self) -> Optional[int]:
        """Announced attendance, or None if the API doesn't have it (it reports 0)."""
        if self.data.match_base is None:
            return None
        spectators = self.data.match_base.environment.number_of_spectators
        return spectators if spectators else None

    def get_cards(self) -> Dict[str, List[str]]:
        """
        Cards by player ID, oldest first, each as an emoji and the minute,
        e.g. {"MLS-OBJ-...": ["\U0001f7e829'", "\U0001f7e8\U0001f7e5109'"]}.
        """
        cards: Dict[str, List[str]] = defaultdict(list)
        # Events come from the API newest first
        for event in reversed(self.get_events() or []):
            if not isinstance(event, CardEvent) or not event.event.player_id:
                continue
            color = event.event.card_color or event.event.card_rating
            emoji = CARD_EMOJI.get(color)
            if emoji is None:
                logger.warning(f"Unknown card color {color} on event {event.event.event_id}")
                continue
            cards[event.event.player_id].append(f"{emoji}{event.event.minute_of_play}'")
        return dict(cards)

    def get_shootout(self) -> Optional[Dict[str, List[ShootoutKick]]]:
        """Penalty shootout kicks by team ID in the order taken, or None if there wasn't one."""
        events = self.get_events() or []
        if not any(e.type == 'start_penalty_shoot_out' for e in events):
            return None
        # Events come from the API newest first
        kicks = [
            e for e in reversed(events)
            if isinstance(e, PenaltyEvent) and e.event.game_section == 'penalty'
        ]
        by_team: Dict[str, List[ShootoutKick]] = {self.home_id: [], self.away_id: []}
        for e in kicks:
            shot = e.event.shot_at_goal
            team_id = shot.team_id or e.event.team_id
            if team_id not in by_team:
                logger.warning(f"Shootout kick {e.event.event_id} has unknown team {team_id}, skipping")
                continue
            taker = f"{shot.player_first_name or ''} {shot.player_last_name or 'Unknown player'}".strip()
            scored = shot.shot_result == 'SuccessfulShot'
            by_team[team_id].append(ShootoutKick(taker, scored, None if scored else shot.shot_result))
        return by_team

    async def load_highlights(self, client: Optional[MLSApiClient] = None) -> Optional[str]:
        """Look up the full-match highlights video and set highlights_url if it's out."""
        try:
            if client is not None:
                data = await client.get_videos(self.sportec_id)
            else:
                async with MLSApiClient() as new_client:
                    data = await new_client.get_videos(self.sportec_id)
        except Exception as e:
            logger.warning(f"Failed to look up highlights for {self.sportec_id}: {e}")
            return self.highlights_url
        for item in (data or {}).get('items', []):
            slug = item.get('slug') or ''
            if slug.startswith(HIGHLIGHTS_SLUG_PREFIX):
                self.highlights_url = VIDEO_URL.format(slug=slug)
                break
        return self.highlights_url

    async def load_next_match(self, client: Optional[MLSApiClient] = None) -> Optional['Match']:
        """Look up the next match on the schedule and set next_match."""
        try:
            if client is not None:
                await self._load_next_match(client)
            else:
                async with MLSApiClient() as new_client:
                    await self._load_next_match(new_client)
        except Exception as e:
            logger.warning(f"Failed to look up the next match after {self.sportec_id}: {e}")
        return self.next_match

    def _next_match_team_ids(self) -> List[str]:
        """Teams whose next match to look for: the ones we follow, or both if neither is."""
        followed = {str(team) for team in getattr(config, 'TEAMS', [])}
        teams = [club.sportecId for club in (self.home, self.away) if str(club.optaId) in followed]
        return teams or [self.home_id, self.away_id]

    async def _load_next_match(self, client: MLSApiClient) -> None:
        info = self.data.match_info
        kickoff = info.matchDate
        if kickoff is None:
            return
        # A Game 3 can stay on the schedule after a 2-0 series
        score = self.get_series_score()
        series_over = bool(score) and max(score.values()) > ROUND_ONE_GAMES // 2
        this_pairing = {self.home_id, self.away_id}

        entry = None
        for team_id in self._next_match_team_ids():
            schedule = await client.get_schedule(
                info.season.sportecId,
                match_date_gte=kickoff.date().isoformat(),
                # The API rejects a start date without an end date
                match_date_lte=(kickoff + NEXT_MATCH_WINDOW).date().isoformat(),
                team_id=team_id,
            )
            candidates = [
                m for m in schedule
                if m.match_id != self.sportec_id
                and m.planned_kickoff_time is not None
                and m.planned_kickoff_time > kickoff
                # The league schedules "MLS Test" matches for its own testing
                and 'test' not in m.competition_name.lower()
                and not (series_over and {m.home_team_id, m.away_team_id} == this_pairing)
            ]
            if candidates:
                entry = min(candidates, key=lambda m: m.planned_kickoff_time)
                break
        if entry is None:
            return

        next_match = Match(entry.match_id)
        next_match.data = ComprehensiveMatchData(match_info=await client.get_match_by_id(entry.match_id))
        next_match._process_data(next_match.data)
        self.next_match = next_match
        status = entry.match_date_time_status or ''
        self.next_match_tbd = status if 'tbd' in status.lower() else None

    def get_winner_id(self) -> Optional[str]:
        """Team ID of the winner of a finished match (including on penalties)."""
        if not self.is_final():
            return None
        info = self.data.match_base.match_information
        home, away = info.home_team_goals, info.away_team_goals
        if home == away:
            home, away = info.home_team_penalty_goals, info.away_team_penalty_goals
            if home is None or away is None:
                return None
        if home == away:
            return None
        return self.home_id if home > away else self.away_id

    async def _load_series(self, client: Optional[MLSApiClient] = None) -> None:
        """Work out who won the earlier games of a best-of-3 series.

        Earlier games come from match_base.last_matches (head-to-head results).
        They don't include shootouts, so drawn games are looked up individually.
        """
        if self.series_winners is not None or self.data.match_base is None:
            return
        playoff_round = self.get_playoff_round()
        if playoff_round is None or not playoff_round.is_series or not playoff_round.game:
            return
        if playoff_round.game == 1:
            self.series_winners = []
            self.series_games = []
            return

        info = self.data.match_base.match_information
        teams = {self.home_id, self.away_id}
        earlier = [
            m for m in self.data.match_base.last_matches
            if m.competition_id == info.competition_id
            and m.season_id == info.season_id
            and {m.home_team_id, m.away_team_id} == teams
            and m.match_id != self.sportec_id
        ]
        earlier.sort(key=lambda m: m.match_date or '')
        earlier = earlier[-(playoff_round.game - 1):]
        if len(earlier) != playoff_round.game - 1:
            logger.warning(f"Found {len(earlier)} earlier series games for {self.sportec_id}, "
                           f"expected {playoff_round.game - 1}")
            return

        try:
            games = []
            for number, m in enumerate(earlier, start=1):
                if m.home_team_goals is None or m.away_team_goals is None:
                    return
                game = SeriesGame(number, m.match_id, m.home_team_id, m.away_team_id,
                                  m.home_team_goals, m.away_team_goals, winner_id=None)
                if m.home_team_goals != m.away_team_goals:
                    game.winner_id = m.home_team_id if m.home_team_goals > m.away_team_goals else m.away_team_id
                    games.append(game)
                    continue
                if client is not None:
                    base = await client.get_match(m.match_id)
                else:
                    async with MLSApiClient() as new_client:
                        base = await new_client.get_match(m.match_id)
                pens = base.match_information
                if pens.home_team_penalty_goals is None or pens.away_team_penalty_goals is None:
                    logger.warning(f"No shootout result for drawn series game {m.match_id}")
                    return
                game.home_pens = pens.home_team_penalty_goals
                game.away_pens = pens.away_team_penalty_goals
                game.winner_id = m.home_team_id if game.home_pens > game.away_pens else m.away_team_id
                games.append(game)
        except Exception as e:
            logger.warning(f"Failed to load series results for {self.sportec_id}: {e}")
            return
        self.series_games = games
        self.series_winners = [game.winner_id for game in games]

    def get_series_score(self, include_current: bool = True) -> Optional[Dict[str, int]]:
        """Series wins by team ID, or None if this isn't a series or results are unknown."""
        if self.series_winners is None:
            return None
        winners = list(self.series_winners)
        if include_current and self.get_winner_id():
            winners.append(self.get_winner_id())
        return {team_id: winners.count(team_id) for team_id in (self.home_id, self.away_id)}

    def is_unneeded_series_game(self) -> bool:
        """True for a Game 3 whose series was already won 2-0."""
        score = self.get_series_score(include_current=False)
        return bool(score) and max(score.values()) > ROUND_ONE_GAMES // 2

    def get_series_status(self, include_current: bool = True) -> Optional[str]:
        """
        One-line playoff status, e.g. "Series tied 1-1",
        "San Diego FC leads the series 1-0", "San Diego FC wins the series 2-1
        and advances to the Conference Semifinals", or for a single-game round
        once it's finished, "Vancouver Whitecaps FC advances to the Conference Final".
        With include_current=False the result of this match is ignored (for
        pre-match threads).
        """
        playoff_round = self.get_playoff_round()
        if playoff_round is None:
            return None
        names = {self.home_id: self.home.fullName, self.away_id: self.away.fullName}

        if not playoff_round.is_series:
            winner = self.get_winner_id() if include_current else None
            if winner is None:
                return None
            if playoff_round.next_round is None:
                return f"{names[winner]} wins MLS Cup!"
            return f"{names[winner]} advances to {playoff_round.next_round}"

        score = self.get_series_score(include_current)
        if not score or not any(score.values()):
            return None
        (leader, leader_wins), (_, trailer_wins) = sorted(score.items(), key=lambda kv: -kv[1])
        if leader_wins == trailer_wins:
            return f"Series tied {leader_wins}-{trailer_wins}"
        if leader_wins > ROUND_ONE_GAMES // 2:
            return (f"{names[leader]} wins the series {leader_wins}-{trailer_wins} "
                    f"and advances to {playoff_round.next_round}")
        return f"{names[leader]} leads the series {leader_wins}-{trailer_wins}"

    def get_comp(self) -> Competition:
        """
        Get competition in which the match is being played.
        """
        return self.data.match_info.competition

    def get_events(self) -> List[MlsEvent] | None:
        """
        Get all events for a match.
        """
        if not self.data.match_events:
            return None
        return self.data.match_events.events

    def get_broadcasters(self) -> List[Broadcaster]:
        """
        Get broadcasters for a match
        """
        if not self.data.match_info:
            return []
        return getattr(self.data.match_info, 'broadcasters', [])

    def get_goalscorers(self) -> Dict[str, List[str]]:
        """
        Get goalscorers for a match.

        Returns:
            A dictionary mapping team ID to a list of strings
        """
        if not self.data.match_events or not self.data.match_events.events:
            return {}
        if self.data.match_base is None:
            return {}
        # Get goal events
        goal_event_details: List[EventDetails] = []
        for event in self.data.match_events.events:
            if event.sub_type == 'goals':
                # Shootout kicks are 'penalties' events with sub_type 'goals'
                # but don't count toward the score.
                if event.event.game_section == 'penalty':
                    continue
                if event.type == 'penalties':
                    goal_event_details.append(event.event.shot_at_goal)
                else: #if event.type == 'shot_at_goals':
                    goal_event_details.append(event.event)
            
        # goal_event_details = [event.event for event in self.data.match_events.events if event.sub_type == 'goals']
        # Use default dict to easily group goals by player ID
        scorers_by_team = {
            self.data.match_base.home.team_id: defaultdict(lambda: {"first_name": "Unknown", "last_name": "Player", "goals": []}),
            self.data.match_base.away.team_id: defaultdict(lambda: {"first_name": "Unknown", "last_name": "Player", "goals": []})
        }

        for event in goal_event_details:
            player_id = event.player_id or f"{event.player_first_name}_{event.player_last_name}"
            team_id = event.team_id
            if team_id not in scorers_by_team:
                logger.warning(f"Goal event {event.event_id} has unknown team {team_id}, skipping")
                continue

            if not scorers_by_team[team_id][player_id]["goals"] or scorers_by_team[team_id][player_id]["first_name"] == "Unknown":
                scorers_by_team[team_id][player_id]["first_name"] = event.player_first_name or "Unknown"
                scorers_by_team[team_id][player_id]["last_name"] = event.player_last_name or "Player"
            
            minute_str = f"{event.minute_of_play}'" if event.minute_of_play is not None else "?"

            if hasattr(event, 'origin') and event.origin == "Penalty":
                minute_str += " pen"
            
            scorers_by_team[team_id][player_id]["goals"].append(minute_str)
        
        output_by_team = {
            self.data.match_base.home.team_id: [],
            self.data.match_base.away.team_id: []
        }
        for team_id, team_scorers in scorers_by_team.items():
            for player_id, player_data in team_scorers.items():
                # Skip if no goals for this player
                if not player_data.get("goals"):
                    continue

                full_name = f"{player_data['first_name']} {player_data['last_name']}".strip()
                # Sort goals numerically by minute
                def sort_key(minute_str: str):
                    minute_part = minute_str.replace(" pen", "").replace("'", "")
                    try:
                        if '+' in minute_part:
                            base, added = map(int, minute_part.split("+"))
                            numeric_minute = float(base) + float(added) / 100.0
                        elif minute_part == '?':
                            return float('inf')
                        else:
                            numeric_minute = float(minute_part)
                        return numeric_minute
                    except ValueError:
                        return float('inf')
                
                sorted_goals = sorted(player_data["goals"], key=sort_key)
                goals_str = ", ".join(sorted_goals)
                output_by_team[team_id].append((sort_key(sorted_goals[0]), f"{full_name} ({goals_str})"))

        # Events come from the API newest first; list scorers by their first goal.
        return {
            team_id: [line for _, line in sorted(scorers, key=lambda scorer: scorer[0])]
            for team_id, scorers in output_by_team.items()
        }


    def get_venue(self) -> MatchVenue:
        """
        Get venue for a match
        """
        return self.data.match_info.venue

    def get_feed(self) -> List[str]:
        """
        Get all events for a match
        """
        if not self.data.match_events or not self.data.match_events.events:
            return []
        return [str(event) for event in self.data.match_events.events]

    def get_subs(self) -> Dict[str, List[SubstitutionEvent]]:
        """
        Get substitution events, ordered by team.
        """
        if not self.data.match_events or not self.data.match_events.events:
            return {}
        if self.data.match_base is None:
            return {}
        subs_by_team = {
            self.data.match_base.home.team_id: [],
            self.data.match_base.away.team_id: []
        }
        if not self.data.match_events.events:
            return {}
        # Get sub events
        for event in self.data.match_events.events:
            if event.type == 'substitutions':
                subs_by_team[event.event.team_id].append(event)
        return subs_by_team

    def get_score(self) -> str:
        """
        Get a score string, including penalties if applicable.
        """
        if self.data.match_base is None:
            return "0-0"
        home_goals = self.data.match_base.match_information.home_team_goals
        away_goals = self.data.match_base.match_information.away_team_goals
        result = f"{home_goals}-{away_goals}"
        if self.data.match_base.match_information.home_team_penalty_goals is not None or self.data.match_base.match_information.away_team_penalty_goals is not None:
            home_pens = self.data.match_base.match_information.home_team_penalty_goals or 0
            away_pens = self.data.match_base.match_information.away_team_penalty_goals or 0
            result += f" ({home_pens}-{away_pens} pens)"
        return result

    def get_status_display(self) -> str:
        """
        Short live-status label for the thread header: "HT" during the
        halftime break, otherwise the current minute (e.g. "33'").
        Empty if the match hasn't started or no minute is available.
        """
        if not self.is_started():
            return ""
        if self.data.match_base.match_information.match_status == 'half':
            return "HT"
        if self.minute_display is not None:
            return f"{self.minute_display}'"
        return ""

    def get_result_type(self) -> str:
        """
        Get result type if the match is finished.
        """
        if not self.is_final():
            return ""
        result = "FT"
        # check if any events are in extra time
        events = self.data.match_events.events if self.data.match_events else []
        sections = [(event_obj.event.game_section or '').lower() for event_obj in events]
        penalties = any('penalty' in section for section in sections)
        extra_time = any('extra' in section for section in sections)

        if extra_time:
            result = "AET"
        if penalties:
            result += " (Pens)"
        return result
    
    def get_data_string(self) -> str:
        retval = []
        if self.data.match_events:
            # TODO how can we consolidate this more...
            # don't care about: 
            # - kickoff events
            # - certain fields (team ID, player ID, player alias)
            events = []
            for e in self.data.match_events.events:
                if e.type in ['kick_off']:
                    continue
                include_events = [
                    "card_color",
                    "card_rating",
                    "final_result",
                    "minute_of_play",
                    "player_first_name",
                    "player_last_name",
                    "team_name",
                    "team_role",
                    "foul_type",
                    "fouled_first_name",
                    "fouled_last_name",
                    "fouler_first_name",
                    "fouler_last_name",
                    "team_fouled_name",
                    "team_fouler_name",
                    "side",
                    "assist_player_first_name",
                    "assist_player_last_name",
                    "inside_box",
                    "distance_to_goal",
                    "shot_result",
                    "type_of_shot",
                    "xG",
                ]
                event = {"type": e.type, "sub_type": e.sub_type, "event": e.event.model_dump(include=include_events)}
                events.append(event)
            retval.append({"match_events": events})
        
        if self.data.match_stats:
            stats = []
            for team in self.data.match_stats.team_statistics:
                include_stats = [
                    "team_name",
                    "team_role",
                    "counter_attacks",
                    "substitutions_in",
                    "substitutions_out",
                    "offsides",
                    "fouls_against_opponent",
                    "goals",
                    "shots_at_goal_sum",
                    "assists",
                    "passes_sum",
                    "crosses_sum",
                    "own_goals",
                    "defensive_clearances",
                    "penalties_successful",
                    "penalties_not_successful",
                    "corner_kicks_sum",
                    "free_kicks_sum",
                    "xG",
                    "distance_covered",
                    "goal_opportunities",
                    "chances",
                    "sitters"
                ]
                stats.append(team.model_dump(include=include_stats))
            retval.append({"match_stats": stats})
        
        return json.dumps(retval, ensure_ascii=False, indent=1)