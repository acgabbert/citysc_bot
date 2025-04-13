from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class EventDetails(BaseModel):
    """Base event details for key events"""
    model_config = ConfigDict(extra="allow", strict=False)
    
    event_id: int
    event_time: str
    minute_of_play: Optional[str] = None
    event_time: Optional[str] = None
    game_section: Optional[str] = None
    player_first_name: Optional[str] = None
    player_last_name: Optional[str] = None
    player_id: Optional[str] = None
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    team_role: Optional[str] = None
    team_short_name: Optional[str] = None
    team_three_letter_code: Optional[str] = None
    three_letter_code: Optional[str] = None

class BaseEventData(BaseModel):
    """Base event model"""
    model_config = ConfigDict(extra="ignore", strict=False)

    type: str
    sub_type: Optional[str] = None
    event: EventDetails

class CardEvent(BaseEventData):
    """Card event"""

    type: Literal['cards']
    sub_type: Optional[str] = None
    
    class CardEventDetails(EventDetails):
        card_color: Optional[str] = None
        card_rating: Optional[str] = None

    event: CardEventDetails

class CornerEvent(BaseEventData):
    """Corner event"""

    type: Literal['corner_kicks']
    sub_type: Optional[str] = None
    
    class CornerEventDetails(EventDetails):
        side: Optional[str] = None

    event: CornerEventDetails

class FinalWhistleEvent(BaseEventData):
    """Final whistle event"""

    type: Literal['final_whistle']
    sub_type: Optional[str] = None
    
    class FinalWhistleEventDetails(EventDetails):
        breaking_off: Optional[bool] = None

    event: FinalWhistleEventDetails

class FoulEvent(BaseEventData):
    """Foul event"""

    type: Literal['fouls']
    sub_type: Optional[str] = None
    
    class FoulEventDetails(EventDetails):
        foul_type: str
        fouled_first_name: Optional[str] = None
        fouled_last_name: Optional[str] = None
        fouled_id: Optional[str] = None
        fouler_first_name: Optional[str] = None
        fouler_last_name: Optional[str] = None
        fouler_id: Optional[str] = None
        team_fouled_id: Optional[str] = None
        team_fouled_name: Optional[str] = None
        team_fouled_role: Optional[str] = None
        team_fouled_short_name: Optional[str] = None
        team_fouled_three_letter_code: Optional[str] = None
        team_fouler_id: Optional[str] = None
        team_fouler_name: Optional[str] = None
        team_fouler_role: Optional[str] = None
        team_fouler_short_name: Optional[str] = None
        team_fouler_three_letter_code: Optional[str] = None

    event: FoulEventDetails

class KickOffEvent(BaseEventData):
    """Kickoff event"""

    type: Literal['kick_off']
    sub_type: Optional[str] = None
    event: EventDetails

class OffsideEvent(BaseEventData):
    """Offside event"""

    type: Literal['offsides']
    sub_type: Optional[str] = None
    event: EventDetails

class ShotEvent(BaseEventData):
    """Shot event"""

    type: Literal['shot_at_goals']
    sub_type: Optional[str] = None
    
    class ShotEventDetails(EventDetails):
        assist_player_first_name: Optional[str] = None
        assist_player_last_name: Optional[str] = None
        assist_player_id: Optional[str] = None
        chance_evaluation: Optional[str] = None
        distance_to_goal: Optional[float] = None
        inside_box: Optional[str] = None
        origin: Optional[str] = None
        result: Optional[str] = None
        shot_result: Optional[str] = None
        type_of_shot: Optional[str] = None
        woodwork_location: Optional[str] = None
        xG: Optional[float] = None

    event: ShotEventDetails

class SubstitutionEvent(BaseEventData):
    """Sub event"""

    type: Literal['substitutions']
    sub_type: Optional[str] = None
    
    class SubstitutionEventDetails(EventDetails):
        player_in_first_name: Optional[str] = None
        player_in_last_name: Optional[str] = None
        player_in_id: Optional[str] = None
        player_out_first_name: Optional[str] = None
        player_out_last_name: Optional[str] = None
        player_out_id: Optional[str] = None

    event: SubstitutionEventDetails

MlsEvent = Union[
    CardEvent,
    CornerEvent,
    FinalWhistleEvent,
    FoulEvent,
    KickOffEvent,
    OffsideEvent,
    ShotEvent,
    SubstitutionEvent
]

class MatchEventResponse(BaseModel):
    events: List[Annotated[MlsEvent, Field(discriminator='type')]]