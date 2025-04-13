from typing import List, Optional, Tuple
from api_client import MLSApiClient
from models.match import ComprehensiveMatchData


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

    def get_lineups(self) -> Tuple[str, str]:
        pass

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

