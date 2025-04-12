from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, field_validator


class MatchSchedule(BaseModel):
    """Model for schedule response from Stats API"""
    competition_id: str
    competition_name: str
    competition_type: str
    end_date: Optional[datetime]
    away_team_id: str
    away_team_name: str
    away_team_short_name: Optional[str]
    away_team_three_letter_code: Optional[str]
    home_team_id: str
    home_team_name: str
    home_team_short_name: Optional[str]
    home_team_three_letter_code: Optional[str]
    match_scheduled: Optional[bool]
    match_day: Optional[int]
    match_day_id: Optional[str]
    match_id: str
    planned_kickoff_time: Optional[datetime]
    season: Optional[int]
    season_id: Optional[str]
    stadium_id: Optional[str]
    stadium_name: Optional[str]
    neutral_venue: Optional[bool]
    start_date: Optional[datetime]
    group: Optional[str]
    match_date_time_status: Optional[str]
    result: Optional[str]
    away_team_goals: Optional[int]
    home_team_goals: Optional[int]
    match_status: str
    minute_of_play: Optional[str]
    stadium_city: Optional[str]
    stadium_country: Optional[str]

    @field_validator('start_date')
    @classmethod
    def validate_match_date(cls, v: Any) -> datetime:
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc)
                else:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception as e:
                raise ValueError(f"Invalid date format: {v}") from e
        elif isinstance(v, datetime):
            if v.tzinfo is not None:
                return v.astimezone(timezone.utc)
            return v.replace(tzinfo=timezone.utc)
        raise ValueError(f"Expected string or datetime, got {type(v)}")

