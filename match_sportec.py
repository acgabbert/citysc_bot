from collections import defaultdict
from datetime import datetime
import logging
import sys
from typing import Dict, List, Optional, Tuple
from api_client import MLSApiClient
from models.club import Club_Sport, ClubMatch_Base
from models.event import EventDetails, MlsEvent, SubstitutionEvent
from models.match import ComprehensiveMatchData
from models.person import BasePerson
from models.schedule import Broadcaster, Competition
from models.team_stats import TeamStats
from models.venue import MatchVenue

logging.basicConfig(
    level=logging.INFO,  # Set the minimum level of messages to handle (e.g., INFO, DEBUG)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', # Example format
    stream=sys.stdout  # Direct output to stdout
)

logger = logging.getLogger(__name__)


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

    def __init__(self, sportec_id: str):
        self.sportec_id = sportec_id
    
    @classmethod
    async def create(cls, sportec_id: str):
        match = cls(sportec_id)
        async with MLSApiClient() as client:
            data = await client.get_all_match_data(match.sportec_id)
            if data.errors:
                logger.error("\n".join(data.errors))
        match.data = data
        match._process_data(data)
        match.update_injuries()
        match.update_discipline()
        return match
    
    async def refresh(self):
        async with MLSApiClient() as client:
            data = await client.get_all_match_data(self.sportec_id)
            if data.errors:
                logger.error("\n".join(data.errors))
        self.data = data
        self._process_data(data)
    
    def _process_data(self, data: ComprehensiveMatchData) -> None:
        """
        Process comprehensive match data for easier access from other functions.
        """
        self.home = data.match_info.home
        self.home_id = self.home.sportecId
        self.away = data.match_info.away
        self.away_id = self.away.sportecId
        self.competition = data.match_info.competition.shortName or data.match_info.competition.name
        self.slug = data.match_info.slug
        if self.is_started():
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
        pass

    def update_discipline(self) -> None:
        pass
        
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
        
        
    def get_local_time_string(self) -> str:
        """
        Get the local time string for the match.
        """
        date = self.get_local_datetime()
        if not date:
            return "Unknown"
        time_string = date.strftime('%I:%M %p ')
        time_string += datetime.now().astimezone().tzname()
        return time_string

    def get_starting_lineups(self) -> Dict[str, List[BasePerson]]:
        """
        Retrieve the starting linups for both teams.
        
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

    def get_comp(self) -> Competition:
        """
        Get competition in which the match is being played.
        """
        return self.data.match_info.competition

    def get_events(self) -> List[MlsEvent] | None:
        """
        Get all events for a match.
        """
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
        if not self.data.match_events.events:
            return {}
        # Get goal events
        goal_event_details: List[EventDetails] = []
        for event in self.data.match_events.events:
            if event.sub_type == 'goals':
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
                    penalty = " pen" in minute_str
                    minute_part = minute_str.replace(" pen", "")
                    try:
                        if '+' in minute_part:
                            base, added = map(int, minute_part.split("+"))
                            numeric_minute = float(base) + float(added) / 10.0
                        elif minute_part == '?':
                            return float('inf')
                        else:
                            numeric_minute = float(minute_part.replace("'", ""))
                        return numeric_minute
                    except ValueError:
                        return float('inf')
                
                # TODO:
                # Have tried this both reversed and not -
                # still appears to sort goals in reverse order (latest first)
                sorted_goals = sorted(player_data["goals"], key=sort_key)
                goals_str = ", ".join(sorted_goals)
                output_by_team[team_id].append(f"{full_name} ({goals_str})")
        
        return output_by_team


    def get_venue(self) -> MatchVenue:
        """
        Get venue for a match
        """
        return self.data.match_info.venue

    def get_feed(self) -> List[str]:
        """
        Get all events for a match
        """
        if not self.data.match_events.events:
            return []

    def get_subs(self) -> Dict[str, List[SubstitutionEvent]]:
        """
        Get substitution events, ordered by team.
        """
        if not self.data.match_events or not self.data.match_events.events:
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
        result = ""
        if self.data.match_base.match_information.result:
            result = f"{self.data.match_info.home.fullName} {self.data.match_base.match_information.result} {self.data.match_info.away.fullName}"
        home_goals = self.data.match_base.match_information.home_team_goals
        away_goals = self.data.match_base.match_information.away_team_goals
        result = f"{home_goals}-{away_goals}"
        if self.data.match_base.match_information.home_team_penalty_goals is not None or self.data.match_base.match_information.away_team_penalty_goals is not None:
            home_pens = self.data.match_base.match_information.home_team_penalty_goals or 0
            away_pens = self.data.match_base.match_information.away_team_penalty_goals or 0
            result += f" ({home_pens}-{away_pens} pens)"
        return result

    def get_result_type(self) -> str:
        """
        Get result type if the match is finished.
        """
        if not self.data.match_events:
            return ""
        result = "FT"
        # check if any events are in extra time
        penalties = any('penalty' in event_obj.event.game_section.lower() for event_obj in self.data.match_events.events)
        extra_time = any('extra' in event_obj.event.game_section.lower() for event_obj in self.data.match_events.events)

        if extra_time:
            result = "AET"
        if penalties:
            result += " (Pens)"
        
        if self.is_final():
            return result
        else:
            return ""