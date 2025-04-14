from typing import Dict, List, Optional, Tuple
from api_client import MLSApiClient
from models.match import ComprehensiveMatchData
from models.person import BasePerson


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
    
    def get_date_time(self) -> str:
        pass

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

    def get_comp(self) -> str:
        pass

    def get_events(self) -> List[str]:
        pass

    def get_broadcasters(self) -> List[str]:
        pass

    def get_goalscorers(self):
        pass

    def get_venue(self):
        pass

    def get_feed(self):
        pass

    def get_lineups(self):
        pass