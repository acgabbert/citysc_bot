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

    def __str__(self) -> str:
        minute = self.event.minute_of_play or '?'
        first_name = self.event.player_first_name or ''
        last_name = self.event.player_last_name or 'Unknown player'
        color = self.event.card_color or self.event.card_rating or 'unknown'
        return f"{minute}': {first_name} {last_name}".strip() + f" receives a {color} card."

class CornerEvent(BaseEventData):
    """Corner event"""

    type: Literal['corner_kicks']
    sub_type: Optional[str] = None
    
    class CornerEventDetails(EventDetails):
        side: Optional[str] = None

    event: CornerEventDetails
    
    def __str__(self) -> str:
        minute = self.event.minute_of_play or '?'
        first_name = self.event.player_first_name or ''
        last_name = self.event.player_last_name or 'Unknown player'
        side = f" from the {self.event.side} side" if self.event.side else ""

        return f"{minute}': {first_name} {last_name}".strip() + f" takes a corner kick{side}."

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

    def __str__(self) -> str:
        retval = f"{self.event.minute_of_play or '?'}': "
        first_name = self.event.player_first_name or ''
        last_name = self.event.player_last_name or 'Unknown player'
        team = self.event.team_three_letter_code or self.event.team_name or ''
        shot_taker = f"{first_name} {last_name} {f"({team})" if team else ""}".strip()

        shot_description = ""
        match self.event.type_of_shot:
            case "leftLeg":
                shot_description += "left-footed shot"
            case "rightLeg":
                shot_description += "left-footed shot"
            case "head":
                shot_description += "headed shot"
        
        if self.event.shot_result == 'SuccessfulShot':
            retval += "Goal!"
            retval += f" {self.event.result}." or ''
            retval += f" {shot_taker} scores with a {shot_description}"
        else:
            retval += f" {shot_taker} shoots with a {shot_description}"
        xg = f" with an xG of {self.event.xG}." if self.event.xG else "."
        retval += xg
        return retval


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
    
    def __str__(self) -> str:
        team_name = self.event.team_name or ''
        minute = self.event.minute_of_play or '?'
        in_first = self.event.player_in_first_name or ''
        in_last = self.event.player_in_last_name or 'Unknown player'
        out_first = self.event.player_out_first_name or ''
        out_last = self.event.player_out_last_name or 'Unknown player'

        retval = f"{minute}': Subsitution{f", {team_name}" if team_name else ""}: "
        retval += f"{in_first} {in_last}".strip()
        retval += " "
        retval += f"{out_first} {out_last}.".strip()
        return retval

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