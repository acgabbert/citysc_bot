from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from models.club import MatchClub
from models.schedule import Competition, Season


class MatchResponse(BaseModel):
    """Model for schedule response from Sport API"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    optaId: int
    sportecId: str
    leagueMatchTitle: Optional[str] = None
    home: MatchClub
    away: MatchClub
    season: Season
    competition: Competition
    appleStreamURL: Optional[str] = None
    appleSubscriptionTier: Optional[str] = None
    roundName: Optional[str] = None
    roundNumber: Optional[int] = None
    roundGroup: Optional[str] = None
    matchDay: Optional[str] = None
    delayedMatch: Optional[bool] = None