from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict

from models.club import Club_Sport, ClubMatch_Base
from models.event import MlsEvent
from models.match_stats import MatchStats
from models.person import BasePerson, NonPlayer
from models.schedule import Competition, Season


class Match_Sport(BaseModel):
    """Model for schedule response from Sport API"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    optaId: int
    sportecId: str
    leagueMatchTitle: Optional[str] = None
    home: Club_Sport
    away: Club_Sport
    season: Season
    competition: Competition
    appleStreamURL: Optional[str] = None
    appleSubscriptionTier: Optional[str] = None
    roundName: Optional[str] = None
    roundNumber: Optional[int] = None
    roundGroup: Optional[str] = None
    matchDay: Optional[str] = None
    delayedMatch: Optional[bool] = None

class MatchInformation(BaseModel):
    """Model for match information from Stats API base"""
    model_config = ConfigDict(extra="ignore", strict=False)

    competition_id: str
    competition_name: Optional[str] = None
    away_team_goals: int
    home_team_goals: int
    match_day: Optional[int] = None
    match_id: str
    match_title: str
    result: Optional[str] = None
    season: int
    season_id: str
    competition_type: str
    match_type: Optional[str] = None
    match_scheduled: Optional[bool] = None
    match_status: str
    minute_of_play: Optional[str] = None


class MatchEnvironment(BaseModel):
    """Model for match environment from Stats API base"""
    model_config = ConfigDict(extra="ignore", strict=False)

    air_humidity: Optional[int] = None
    air_pressure: Optional[int] = None
    country: Optional[str] = None
    floodlight: Optional[str] = None
    pitch_erosion: Optional[str] = None
    pitch_x: Optional[float] = None
    pitch_y: Optional[float] = None
    roof: Optional[str] = None
    sold_out: Optional[bool] = None
    stadium_address: Optional[str] = None
    stadium_capacity: Optional[int] = None
    stadium_id: Optional[str] = None
    stadium_name: Optional[str] = None
    temperature: Optional[float] = None
    number_of_spectators: Optional[int] = None

class Match_Base(BaseModel):
    """Model for match response from Stats API base"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    match_information: MatchInformation
    environment: MatchEnvironment
    home: ClubMatch_Base
    away: ClubMatch_Base
    referees: List[BasePerson]


class ComprehensiveMatchData(BaseModel):
    match_base: Optional[Match_Base] = None
    match_stats: Optional[MatchStats] = None
    match_events: Optional[List[MlsEvent]] = None
    errors: List[str] = [] # To track specific fetch errors