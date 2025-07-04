from typing import Optional
from pydantic import BaseModel, ConfigDict

from models.constants import FlexibleBool


class BasePerson(BaseModel):
    """Model for any person"""
    model_config = ConfigDict(extra="ignore", strict=False)

    first_name: str
    last_name: str
    person_id: str
    short_name: str

    playing_position: Optional[str] = None
    shirt_number: Optional[int] = None
    starting: Optional[FlexibleBool] = None
    team_leader: Optional[FlexibleBool] = None
    role: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

class Player(BaseModel):
    """Model for a player"""
    model_config = ConfigDict(extra="ignore", strict=False)

    first_name: str
    last_name: str
    person_id: str
    short_name: str

    playing_position: str
    shirt_number: int

class NonPlayer(BaseModel):
    """Model for a member of training staff"""
    model_config = ConfigDict(extra="ignore", strict=False)

    first_name: str
    last_name: str
    person_id: str
    short_name: str
    
    role: str