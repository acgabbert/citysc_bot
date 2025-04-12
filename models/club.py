from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, field_validator


class MatchClub(BaseModel):
    """Model for club object from Sport API match call"""
    model_config = ConfigDict(extra="ignore", strict=False)
    
    optaId: int
    sportecId: str
    fullName: str
    slug: str
    shortName: Optional[str] = None
    abbreviation: Optional[str] = None
    backgroundColor: Optional[str] = None