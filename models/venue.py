from typing import Optional
from pydantic import BaseModel, ConfigDict


class MatchVenue(BaseModel):
    """Model for venue object from Sport API match call"""
    model_config = ConfigDict(extra="ignore", strict=False)

    venueSportecId: str
    name: str
    city: Optional[str] = None