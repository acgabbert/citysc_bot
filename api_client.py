import aiohttp
import asyncio
import backoff
import inspect
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urljoin
from pydantic import BaseModel, field_validator, model_validator

import config
from models.schedule import MatchSchedule
import util

logger = logging.getLogger(__name__)

class MLSApiError(Exception):
    """Base exception for MLS API errors"""
    pass

class MLSApiClientError(MLSApiError):
    """Client-side errors (4xx)"""
    pass

class MLSApiServerError(MLSApiError):
    """Server-side errors (5xx)"""
    pass

class MLSApiTimeoutError(MLSApiError):
    """Request timeout errors"""
    pass

class MLSApiRateLimitError(MLSApiError):
    """Rate limit exceeded errors"""
    pass

class ApiEndpoint(Enum):
    STATS = "stats"
    STATS_DEPRECATED = "stats"
    SPORT = "sport"
    VIDEO = "video"
    NEXT_PRO = "nextpro"

class Competition(Enum):
    MLS = 98
    LEAGUES_CUP = 1045
    US_OPEN_CUP = 557
    CONCACAF_CL = 549
    MLS_NEXT_PRO = 1164
    FRIENDLY = 34
    ALL_STAR_GAME = 355

class MatchType(Enum):
    REGULAR = "Regular"
    CUP = "Cup"

@dataclass
class MLSApiConfig:
    """Configuration for the MLS API client"""
    stats_base_url: str = "https://stats-api.mlssoccer.com"
    stats_base_url_deprecated: str = "https://stats-api.mlssoccer.com/v1/"
    sport_base_url: str = "https://sportapi.mlssoccer.com/api/"
    video_base_url: str = "https://dapi.mlssoccer.com/v2/"
    nextpro_base_url: str = "https://sportapi.mlsnextpro.com/api/matches"
    user_agent: str = config.USER_AGENT_STR
    timeout: int = 30
    max_retries: int = 3
    rate_limit_calls: int = 10
    rate_limit_period: int = 1  # seconds
    log_responses: bool = True

class MatchScheduleDeprecated(BaseModel):
    """Model for schedule response from sport API"""
    optaId: int
    matchDate: datetime
    slug: str
    competition: Dict[str, Any]
    appleSubscriptionTier: Optional[str]
    appleStreamURL: Optional[str]
    broadcasters: List[Dict[str, Any]]

    @field_validator('matchDate')
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
    
    @model_validator(mode='after')
    def validate_model(self) -> 'MatchScheduleDeprecated':
        if self.appleStreamURL and not self.appleStreamURL:
            raise ValueError("appleStreamURL must be set if appleSubscriptionTier is set")
        return self

class MLSApiClient:
    def __init__(self, config: MLSApiConfig = MLSApiConfig()):
        self.config = config
        self._sessions: Dict[ApiEndpoint, Optional[aiohttp.ClientSession]] = {
            ApiEndpoint.STATS: None,
            ApiEndpoint.STATS_DEPRECATED: None,
            ApiEndpoint.SPORT: None,
            ApiEndpoint.VIDEO: None,
            ApiEndpoint.NEXT_PRO: None
        }
        self._rate_limiters: Dict[ApiEndpoint, asyncio.Semaphore] = {
            ApiEndpoint.STATS: asyncio.Semaphore(self.config.rate_limit_calls),
            ApiEndpoint.STATS_DEPRECATED: asyncio.Semaphore(self.config.rate_limit_calls),
            ApiEndpoint.SPORT: asyncio.Semaphore(self.config.rate_limit_calls),
            ApiEndpoint.VIDEO: asyncio.Semaphore(self.config.rate_limit_calls),
            ApiEndpoint.NEXT_PRO: asyncio.Semaphore(self.config.rate_limit_calls)
        }
        self._last_requests: Dict[ApiEndpoint, List[float]] = {
            ApiEndpoint.STATS: [],
            ApiEndpoint.STATS_DEPRECATED: [],
            ApiEndpoint.SPORT: [],
            ApiEndpoint.VIDEO: [],
            ApiEndpoint.NEXT_PRO: []
        }

    async def __aenter__(self):
        # Initialize sessions for both APIs
        self._sessions[ApiEndpoint.STATS] = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent}
        )
        self._sessions[ApiEndpoint.STATS_DEPRECATED] = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent}
        )
        self._sessions[ApiEndpoint.SPORT] = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent}
        )
        self._sessions[ApiEndpoint.VIDEO] = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent}
        )
        self._sessions[ApiEndpoint.NEXT_PRO] = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Close all sessions
        for session in self._sessions.values():
            if session:
                await session.close()

    def _get_base_url(self, endpoint: ApiEndpoint) -> str:
        if endpoint == ApiEndpoint.STATS:
            return self.config.stats_base_url
        if endpoint == ApiEndpoint.STATS_DEPRECATED:
            return self.config.stats_base_url_deprecated
        if endpoint == ApiEndpoint.VIDEO:
            return self.config.video_base_url
        if endpoint == ApiEndpoint.NEXT_PRO:
            return self.config.nextpro_base_url
        return self.config.sport_base_url

    @backoff.on_exception(
        backoff.expo,
        (MLSApiServerError, MLSApiTimeoutError),
        max_tries=3
    )
    async def _make_request(
        self, 
        endpoint: ApiEndpoint,
        path: str, 
        params: Optional[Dict[str, Any]] = None,
        allow_404: bool = False
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Make an API request to either endpoint
        
        Returns:
            Union[Dict[str, Any], List[Dict[str, Any]]]: The JSON response, 
            which may be either a dictionary or a list of dictionaries
        """
        base_url = self._get_base_url(endpoint)
        url = urljoin(base_url, path)
        session = self._sessions[endpoint]
        rate_limiter = self._rate_limiters[endpoint]
        
        async with rate_limiter:
            now = datetime.now().timestamp()
            last_requests = self._last_requests[endpoint]
            
            if len(last_requests) >= self.config.rate_limit_calls:
                oldest = last_requests[0]
                if now - oldest < self.config.rate_limit_period:
                    await asyncio.sleep(self.config.rate_limit_period - (now - oldest))
                last_requests.pop(0)
            last_requests.append(now)
            
            try:
                async with session.get(
                    url,
                    params=params,
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 204:  # No content
                        return {}
                    if response.status == 404 and allow_404:
                        return {}
                    if response.status != 200:
                        text = await response.text()
                        if response.status == 429:
                            raise MLSApiRateLimitError(f"Rate limit exceeded for {endpoint.value}")
                        elif 400 <= response.status < 500:
                            raise MLSApiClientError(f"Client error {response.status}: {text}\n{url}\n{params}")
                        else:
                            raise MLSApiServerError(f"Server error {response.status}: {text}\n{url}\n{params}")
                    
                    response_data = await response.json()

                    # Log responses to assets/ directory
                    if hasattr(self.config, "log_responses") and self.config.log_responses:
                        try:
                            caller_name = inspect.stack()[2].function
                            # Extract match_id or club opta ID from params if it exists
                            id = params.get('match_game_id', params.get('clubOptaId', '')) if params else ''
                            if id == '':
                                id = path.split('/')[1]
                            filename = f"assets/{caller_name.split('get_')[1]}_{id}.json"
                            util.write_json(response_data, filename)
                        except Exception as e:
                            logger.error(f"Failed to log response: {str(e)}")

                    return response_data
                    
            except asyncio.TimeoutError as e:
                raise MLSApiTimeoutError(f"Request to {url} timed out") from e
            except aiohttp.ClientError as e:
                raise MLSApiError(f"Request to {url} failed: {str(e)}") from e

    # Stats API endpoints
    async def get_match_stats(self, match_id: int) -> List[Dict[str, Any]]:
        """Get match statistics from stats API"""
        response = await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "clubs/matches",
            params={
                "match_game_id": match_id,
                "include": [
                    'club',
                    'match',
                    'competition',
                    'statistics'
                ]
            }
        )
        # response is formatted as an array
        if not response:
            return []
        return response

    async def get_match_data(self, match_id: int) -> Dict[str, Any]:
        """Get match data from stats API"""
        response = await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "matches",
            params={
                "match_game_id": match_id,
                "include": [
                    "competition",
                    "venue",
                    "home_club",
                    "away_club",
                    "home_club_match",
                    "away_club_match"
                ]
            }
        )
        # response is formatted as an array
        if not response:
            return {}
        return response[0]  # Return the first match object

    async def get_match_commentary(self, match_id: int) -> List[Dict[str, Any]]:
        """Get match commentary from stats API"""
        return await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "commentaries",
            params={
                "match_game_id": match_id,
                "include": ["club", "player"]
            }
        )
    
    async def get_preview(self, match_id: int) -> List[Dict[str, Any]]:
        """Get the preview (match facts) for a match."""
        return await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "matchfacts",
            params={
                "match_game_id": match_id,
                "matchfact_language": "en"
            }
        )
    
    async def get_feed(self, match_id: int) -> List[Dict[str, Any]]:
        """Get the full feed from a match."""
        return await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "commentaries",
            params={
                "match_game_id": match_id,
                'commentary_type': ['secondyellow card', 'penalty goal', 'own goal',
                                    'yellow card', 'red card', 'substitution', 'goal',
                                    'penalty miss', 'penalty saved', 'lineup', 'start',
                                    'end 1', 'end 2', 'end 3', 'end 4', 'end 5', 'end 14',
                                    'start delay', 'end delay', 'postponed',
                                    'free kick lost', 'free kick won', 'attempt blocked',
                                    'attempt saved', 'miss', 'post', 'corner', 'offside',
                                    'penalty won', 'penalty lost', 'penalty miss',
                                    'penalty saved', 'player retired',
                                    'contentious referee decision', 'VAR cancelled goal'],
                'include': ['club', 'player', 'player_match'],
                'order_by': ['commentary_period', 'commentary_minute', 'commentary_second',
                            'commentary_timestamp', 'commentary_opta_id']
            }
        )
    
    async def get_summary(self, match_id: int) -> List[Dict[str, Any]]:
        """Get the summary feed from a match."""
        return await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "commentaries",
            params={
                "match_game_id": match_id,
                'commentary_type': ['secondyellow card', 'penalty goal', 'own goal',
                                    'yellow card', 'red card', 'substitution', 'goal',
                                    'penalty miss', 'penalty saved', 'lineup', 'start',
                                    'end 1', 'end 2', 'end 3', 'end 4', 'end 5', 'end 14',
                                    'start delay', 'end delay', 'postponed'],
                'include': ['club', 'player'],
                'order_by': ['commentary_period', 'commentary_minute', 'commentary_second',
                            'commentary_timestamp', 'commentary_opta_id']
            }
        )
    
    async def get_lineups(self, match_id: int) -> List[Dict[str, Any]]:
        """Get the lineups from a match."""
        return await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "players/matches",
            params={
                "match_game_id": match_id,
                'include': ['player', 'club']
            }
        )
    
    async def get_subs(self, match_id: int) -> List[Dict[str, Any]]:
        """Get the subs from a match."""
        return await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "substitutions",
            params={
                "match_game_id": match_id,
                'include': ['player_match', 'club', 'player']
            }
        )
    
    async def get_managers(self, match_id: int) -> List[Dict[str, Any]]:
        """Get managers for a match."""
        return await self._make_request(
            ApiEndpoint.STATS_DEPRECATED,
            "managers/matches",
            params={
                "match_game_id": match_id,
                "include": ["manager", "club"]
            }
        )

    # Sport API endpoints
    async def get_schedule_deprecated(
        self,
        club_opta_id: Optional[int] = None,
        competition: Optional[Competition] = None,
        match_type: Optional[MatchType] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[MatchScheduleDeprecated]:
        """Get schedule from sport API"""
        params = {
            "culture": "en-us"
        }
        if club_opta_id:
            params["clubOptaId"] = club_opta_id
        if competition:
            params["competition"] = competition.value
        if match_type:
            params["matchType"] = match_type.value
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to

        data = await self._make_request(
            ApiEndpoint.SPORT,
            "matches",
            params=params
        )
        return [MatchScheduleDeprecated.model_validate(match) for match in data]

    async def get_match_info(self, match_id: int) -> Dict[str, Any]:
        """Get match info from sport API"""
        return await self._make_request(
            ApiEndpoint.SPORT,
            f"matches/{match_id}"
        )

    async def get_standings(
        self,
        season_id: int,
        competition: Competition = Competition.MLS,
        is_live: bool = True
    ) -> Dict[str, Any]:
        """Get standings from sport API"""
        return await self._make_request(
            ApiEndpoint.SPORT,
            "standings/live",
            params={
                "isLive": str(is_live).lower(),
                "seasonId": season_id,
                "competitionId": competition.value
            }
        )
    
    async def get_recent_form(
        self,
        club_id: int,
        second_club_id: int,
        match_date: datetime
    ) -> Dict[str, Any]:
        """Get recent form for the teams participating in a match"""
        print(f"received {club_id}, {second_club_id}, {match_date}")
        return await self._make_request(
            ApiEndpoint.SPORT,
            f"previousMatches/{club_id}",
            params={
                "culture": "en-us",
                "secondClub": second_club_id,
                "matchDate": match_date.isoformat(),
                "maxItems": 3,
                "formGuideMatchesCount": 5
            }
        )
    
    # Video API endpoints
    async def get_videos(self, match_id: int) -> Dict[str, Any]:
        """Get standings from sport API"""
        return await self._make_request(
            ApiEndpoint.SPORT,
            "content/en-us/brightcovevideos",
            params={
                'fields.optaMatchId': match_id
            },
            allow_404=True
        )
    
    async def get_competitions(self) -> Dict[str, Any]:
        """Get current competitions"""
        return await self._make_request(
            ApiEndpoint.STATS,
            "/competitions"
        )
    
    async def get_seasons(self, competition_id: str) -> Dict[str, Any]:
        """Get MLS seasons"""
        return await self._make_request(
            ApiEndpoint.STATS,
            f"/competitions/{competition_id}/seasons"
        )
    
    async def get_schedule(self, season: str, **kwargs) -> Dict[str, Any]:
        """Get schedule"""
        params = {
            "per_page": 100,
            "sort": "planned_kickoff_time:asc,home_team_name:asc"
        }
        if kwargs.get("match_date_gte"):
            params["match_date[gte]"] = kwargs["match_date_gte"]
        if kwargs.get("match_date_lte"):
            params["match_date[lte]"] = kwargs["match_date_lte"]
        
        data = await self._make_request(
            ApiEndpoint.STATS,
            f"/matches/seasons/{season}",
            params=params
        )
        data = data.get("schedule", None)
        return [MatchSchedule.model_validate(match) for match in data]
    
    # MLS Next Pro API endpoints
    async def get_nextpro_match_info(self, match_id: int) -> Dict[str, Any]:
        """Get match info for an MLS Next Pro match"""
        data = await self._make_request(
            ApiEndpoint.NEXT_PRO,
            f"matches/{match_id}"
        )
        return MatchScheduleDeprecated.model_validate(data)
    
    async def get_nextpro_schedule(
        self,
        club_opta_id: Optional[int] = None,
        match_type: Optional[MatchType] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> List[MatchScheduleDeprecated]:
        """Get schedule from MLS Next Pro API"""
        params = {
            "culture": "en-us"
        }
        if club_opta_id:
            params["clubOptaId"] = club_opta_id
        if match_type:
            params["matchType"] = match_type.value
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to

        data = await self._make_request(
            ApiEndpoint.NEXT_PRO,
            "matches",
            params=params
        )
        return [MatchScheduleDeprecated.model_validate(match) for match in data]


# Example usage:
async def main():
    async with MLSApiClient() as client:
        try:
            # Get match data from both APIs
            match_id = 2261385
            match_stats = await client.get_match_stats(match_id)
            match_info = await client.get_match_info(match_id)
            
            # Get schedule for a team
            schedule = await client.get_schedule_deprecated(
                club_opta_id=17012,  # St. Louis City SC
                competition=Competition.MLS,
                match_type=MatchType.REGULAR,
                date_from="2025-02-15",
                date_to="2025-11-23"
            )
            
            # Get standings
            #standings = await client.get_standings(2025)
            
            print(f"Match info: {match_info}")
            print(f"Schedule: Found {len(schedule)} matches")
            
        except MLSApiError as e:
            logger.error(f"API error: {e}")

if __name__ == "__main__":
    asyncio.run(main())