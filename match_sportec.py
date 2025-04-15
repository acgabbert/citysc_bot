from datetime import datetime
from typing import Dict, List, Optional, Tuple
from api_client import MLSApiClient
from models.event import MlsEvent
from models.match import ComprehensiveMatchData
from models.person import BasePerson
from models.schedule import Broadcaster, Competition
from models.venue import MatchVenue


class Match:
    data: Optional[ComprehensiveMatchData] = None

    def __init__(self, sportec_id: str):
        self.sportec_id = sportec_id
    
    @classmethod
    async def create(cls, sportec_id: str):
        match = cls(sportec_id)
        async with MLSApiClient() as client:
            match.data = await client.get_all_match_data(match.sportec_id)
            if match.data.errors:
                print("\n".join(match.data.errors))
        
        return match
    
    def started(self) -> bool:
        if not self.data.match_base:
            return False
        
        if self.data.match_base.match_information.match_status in ['scheduled']:
            return False
        
        return True
        
    def final(self) -> bool:
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
        return self.data.match_base.match_information.planned_kickoff_time.astimezone()
    
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
                    if hasattr(p, 'starting') and p.starting == 'true'
                ]
            except TypeError:
                pass
            lineups[home_team.team_id] = home_lineup

        if away_team and away_team.team_id and hasattr(away_team, 'players') and away_team.players is not None:
            away_lineup = []
            try:
                away_lineup = [
                    p for p in away_team.players
                    if hasattr(p, 'starting') and p.starting == 'true'
                ]
            except TypeError:
                pass
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
        return self.data.match_events

    def get_broadcasters(self) -> List[Broadcaster] | None:
        """
        Get broadcasters for a match
        """
        return self.data.match_info.broadcasters

    def get_goalscorers(self) -> List[str]:
        """
        Get goalscorers for a match.
        """
        if not self.data.match_events:
            return []
        goal_events = [event for event in self.data.match_events if event.sub_type == 'goals']


    def get_venue(self) -> MatchVenue:
        """
        Get venue for a match
        """
        return self.data.match_info.venue

    def get_feed(self) -> List[str]:
        """
        Get all events for a match
        """
        if not self.data.match_events:
            return []

    def get_lineups(self):
        """
        Get 
        """