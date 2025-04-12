from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, field_validator


class MatchVenue(BaseModel):
    """Model for venue object from Sport API match call"""
    model_config = ConfigDict(extra="ignore", strict=False)

    venueSportecId: str
    name: str
    city: Optional[str]