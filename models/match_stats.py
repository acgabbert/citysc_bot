from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from models.team_stats import TeamStats


class MatchStats(BaseModel):
    """Model for match stats object from stats API call"""
    model_config = ConfigDict(extra="ignore", strict=False)

    match_id: str
    game_title: Optional[str] = None
    planned_kick_off: Optional[str] = None
    kick_off: Optional[str] = None
    competition: str
    competition_id: str
    match_day: Optional[int] = None
    match_day_id: Optional[str] = None
    season: int
    season_id: str
    match_status: str
    data_status: Optional[str] = None
    minute_of_play: Optional[str] = None
    scope: Optional[str] = None
    result: Optional[str] = None
    team_statistics: List[TeamStats]