from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from models.person import BasePerson, NonPlayer
from player import Player


class Club_Sport(BaseModel):
    """Model for club object from Sport API match call"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    optaId: int
    sportecId: str
    fullName: str
    slug: str
    shortName: Optional[str] = None
    abbreviation: Optional[str] = None
    backgroundColor: Optional[str] = None

class ClubMatch_Base(BaseModel):
    """Model for club object from Stats API base match call"""
    model_config = ConfigDict(extra="ignore", strict=False)

    initial_line_up: Optional[str] = None
    latest_line_up: Optional[str] = None
    player_shirt_type: Optional[str] = None
    role: Optional[str] = None
    team_id: str
    team_name: str
    team_short_name: Optional[str] = None
    team_three_letter_code: Optional[str] = None
    players: List[BasePerson]
    trainer_staff: List[BasePerson]