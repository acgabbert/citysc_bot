from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from models.person import BasePerson, NonPlayer


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
    logoBWSlug: Optional[str] = None
    logoColorSlug: Optional[str] = None
    logoColorUrl: Optional[str] = None
    crestColorSlug: Optional[str] = None

    def get_logo_url(self, width: int = 128, height: int = 128) -> Optional[str]:
        """Format the logoColorUrl with the given dimensions.

        Replaces {formatInstructions} with Cloudinary transform params.
        """
        if not self.logoColorUrl:
            return None
        return self.logoColorUrl.replace(
            "{formatInstructions}",
            f"w_{width},h_{height},c_pad/f_auto"
        )

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