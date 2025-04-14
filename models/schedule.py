from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from models.constants import UtcDatetime


class MatchSchedule(BaseModel):
    """Model for schedule response from Stats API"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    competition_id: str
    competition_name: str
    competition_type: str
    end_date: Optional[UtcDatetime] = None
    away_team_id: str
    away_team_name: str
    away_team_short_name: Optional[str] = None
    away_team_three_letter_code: Optional[str] = None
    home_team_id: str
    home_team_name: str
    home_team_short_name: Optional[str] = None
    home_team_three_letter_code: Optional[str] = None
    match_scheduled: Optional[bool] = None
    match_day: Optional[int] = None
    match_day_id: Optional[str] = None
    match_id: str
    planned_kickoff_time: Optional[UtcDatetime] = None
    season: Optional[int] = None
    season_id: Optional[str] = None
    stadium_id: Optional[str] = None
    stadium_name: Optional[str] = None
    neutral_venue: Optional[bool] = None
    start_date: Optional[UtcDatetime] = None
    group: Optional[str] = None
    match_date_time_status: Optional[str] = None
    result: Optional[str] = None
    away_team_goals: Optional[int] = None
    home_team_goals: Optional[int] = None
    match_status: str
    minute_of_play: Optional[str] = None
    stadium_city: Optional[str] = None
    stadium_country: Optional[str] = None


class Season(BaseModel):
    """Model for season object from Sport API match call"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    slug: str
    optaId: int
    sportecId: str
    competitionOptaId: str
    name: str

class Competition(BaseModel):
    """Model for competition object from Sport API match call"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    optaId: int
    sportecId: str
    name: str
    slug: Optional[str] = None
    shortName: Optional[str] = None
    matchType: Optional[str] = None

class Broadcaster(BaseModel):
    """Model for broadcaster object from Sport API match call"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    broadcasterTypeLabel: Optional[str]
    broadcasterName: str
    broadcasterStreamingURL: Optional[str] = None
    broadcasterType: str
