from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict

from models.club import Club_Sport, ClubMatch_Base
from models.constants import FlexibleBool, UtcDatetime
from models.event import MatchEventResponse, MlsEvent
from models.match_stats import MatchStats
from models.person import BasePerson, NonPlayer
from models.schedule import Broadcaster, Competition, MatchSchedule, Season
from models.venue import MatchVenue


class Match_Sport(BaseModel):
    """Model for schedule response from Sport API"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    optaId: int
    sportecId: str
    leagueMatchTitle: Optional[str] = None
    slug: Optional[str] = None
    home: Club_Sport
    away: Club_Sport
    venue: MatchVenue
    season: Season
    competition: Competition
    broadcasters: Optional[List[Broadcaster]] = []
    matchDate: Optional[UtcDatetime] = None
    appleStreamURL: Optional[str] = None
    appleSubscriptionTier: Optional[str] = None
    roundName: Optional[str] = None
    roundNumber: Optional[int] = None
    roundGroup: Optional[str] = None
    matchDay: Optional[str] = None
    delayedMatch: Optional[FlexibleBool] = None

class MatchInformation(BaseModel):
    """Model for match information from Stats API base"""
    model_config = ConfigDict(extra="ignore", strict=False)

    competition_id: str
    competition_name: Optional[str] = None
    away_team_goals: int
    home_team_goals: int
    away_team_penalty_goals: Optional[int] = None
    home_team_penalty_goals: Optional[int] = None
    match_day: Optional[int] = None
    match_id: str
    match_title: str
    planned_kickoff_time: Optional[UtcDatetime] = None
    result: Optional[str] = None
    result_penalty: Optional[str] = None
    season: int
    season_id: str
    competition_type: str
    match_type: Optional[str] = None
    match_scheduled: Optional[FlexibleBool] = None
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

class BasicMatch(BaseModel):
    """Model for basic match data from the last_matches object"""
    model_config = ConfigDict(extra="ignore", strict=False)

    match_date: Optional[str] = None
    home_team_id: Optional[str] = None
    home_team_name: Optional[str] = None
    home_team_short_name: Optional[str] = None
    home_team_three_letter_code: Optional[str] = None
    away_team_id: Optional[str] = None
    away_team_name: Optional[str] = None
    away_team_short_name: Optional[str] = None
    away_team_three_letter_code: Optional[str] = None
    home_team_goals: Optional[int] = None
    away_team_goals: Optional[int] = None
    match_id: Optional[str] = None
    season_id: Optional[str] = None
    competition_id: Optional[str] = None

class Match_Base(BaseModel):
    """Model for match response from Stats API base"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    match_information: MatchInformation
    environment: MatchEnvironment
    home: ClubMatch_Base
    away: ClubMatch_Base
    referees: List[BasePerson]
    last_matches: List[BasicMatch]


class ComprehensiveMatchData(BaseModel):
    match_info: Optional[Match_Sport] = None
    match_base: Optional[Match_Base] = None
    match_stats: Optional[MatchStats] = None
    match_events: Optional[MatchEventResponse] = None
    errors: List[str] = [] # To track specific fetch errors