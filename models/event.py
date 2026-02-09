from typing import Annotated, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator

from models.constants import FlexibleBool, UtcDatetime


class EventDetails(BaseModel):
    """Base event details for key events"""
    model_config = ConfigDict(extra="allow", strict=False)
    
    event_id: int
    minute_of_play: Optional[str] = None
    event_time: Optional[UtcDatetime] = None
    game_section: Optional[str] = None
    player_first_name: Optional[str] = None
    player_last_name: Optional[str] = None
    player_id: Optional[str] = None
    result: Optional[str] = None
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    team_role: Optional[str] = None
    team_short_name: Optional[str] = None
    team_three_letter_code: Optional[str] = None
    three_letter_code: Optional[str] = None

    @model_validator(mode='after')
    def set_minute_of_play_for_half(self) -> 'EventDetails':
        """
        Sets minute_of_play to '46' if game_section is 'half'
        and minute_of_play was not provided (is None).
        """
        if self.minute_of_play is None:
            if self.game_section == "half":
                self.minute_of_play = "46"
            else:
                self.minute_of_play = "?"
        return self

class ShotEventDetails(EventDetails):
    assist_player_first_name: Optional[str] = None
    assist_player_last_name: Optional[str] = None
    assist_player_id: Optional[str] = None
    chance_evaluation: Optional[str] = None
    distance_to_goal: Optional[float] = None
    inside_box: Optional[FlexibleBool] = None
    origin: Optional[str] = None
    result: Optional[str] = None
    shot_result: Optional[str] = None
    type_of_shot: Optional[str] = None
    woodwork_location: Optional[str] = None
    xG: Optional[float] = None

    def __str__(self) -> str:
        retval = f"{self.minute_of_play or '?'}': "
        first_name = self.player_first_name or ''
        last_name = self.player_last_name or 'Unknown player'
        team = self.team_three_letter_code or self.team_name or ''
        shot_taker = f"{first_name} {last_name} {f"({team})" if team else ""}".strip()

        shot_description = ""
        match self.type_of_shot:
            case "leftLeg":
                shot_description += "left-footed shot"
            case "rightLeg":
                shot_description += "right-footed shot"
            case "head":
                shot_description += "headed shot"
        
        if self.shot_result == 'SuccessfulShot':
            retval += "Goal!"
            retval += f" {self.result}." or ''
            retval += f" {shot_taker} scores with a {shot_description}"
        else:
            retval += f" {shot_taker} shoots with a {shot_description}"
        xg = f" with an xG of {self.xG}." if self.xG else "."
        retval += xg
        return retval

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

class OwnGoalEvent(BaseEventData):
    type: Literal['own_goals']
    sub_type: Optional[str] = None
    event: EventDetails

class PenaltyEvent(BaseEventData):
    """Penalty event"""

    type: Literal['penalties']
    sub_type: Optional[str] = None

    class PenaltyEventDetails(EventDetails):
        causing_player_alias: Optional[str] = None
        causing_player_first_name: Optional[str] = None
        causing_player_id: Optional[str] = None
        causing_player_last_name: Optional[str] = None
        decision_timestamp: Optional[str] = None
        prospective_taker_first_name: Optional[str] = None
        prospective_taker_id: Optional[str] = None
        prospective_taker_last_name: Optional[str] = None
        shot_at_goal: ShotEventDetails

    event: PenaltyEventDetails

class ShotEvent(BaseEventData):
    """Shot event"""

    type: Literal['shot_at_goals']
    sub_type: Optional[str] = None

    event: ShotEventDetails

class StartShootoutEvent(BaseEventData):
    """Start of penalty shootout event"""
    type: Literal['start_penalty_shoot_out']
    sub_type: Optional[str] = None

    event: EventDetails

class PenaltyNotSuccessfulEvent(BaseEventData):
    """Unsuccessful penalty event"""
    type: Literal['penalties_not_successful']
    sub_type: Optional[str] = None

    event: EventDetails

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
    OwnGoalEvent,
    PenaltyEvent,
    PenaltyNotSuccessfulEvent,
    StartShootoutEvent,
    ShotEvent,
    SubstitutionEvent
]

class MatchEventResponse(BaseModel):
    model_config = ConfigDict(extra="allow", strict=False)
    events: List[Annotated[MlsEvent, Field(discriminator='type')]]

    class EventsMatchInfo(BaseModel):
        model_config = ConfigDict(extra="allow", strict=False)
        
        match_id: str
        game_title: Optional[str] = None
        planned_kick_off: Optional[UtcDatetime] = None
        kick_off: Optional[UtcDatetime] = None
        competition: Optional[str] = None
        competition_id: Optional[str] = None
        match_day: Optional[int] = None
        match_day_id: Optional[str] = None
        season: Optional[int] = None
        creation_date: Optional[UtcDatetime] = None
        match_status: Optional[str] = None
        minute_of_play: Optional[str] = None
        result: Optional[str] = None
        home_team_goals: Optional[int] = None
        away_team_goals: Optional[int] = None
        home_team_id: Optional[str] = None
        home_team_name: Optional[str] = None
        away_team_id: Optional[str] = None
        away_team_name: Optional[str] = None

        class GameSection(BaseModel):
            model_config = ConfigDict(extra="allow", strict=False)

            name: Optional[str] = None
            result: Optional[str] = None
            kick_off_time: Optional[UtcDatetime] = None
            final_whistle_time: Optional[UtcDatetime] = None

        game_section: Optional[List[GameSection]] = None

    
    match_info: Optional[EventsMatchInfo] = None