import requests
import json
import logging

import config
import discord as msg
import util


USER_AGENT = config.USER_AGENT_STR
filename = 'assets/standings.json'
BASE_URL = 'https://sportapi.mlssoccer.com/api/'
standings = 'https://sportapi.mlssoccer.com/api/standings/live?isLive=true&'
commentary = 'https://stats-api.mlssoccer.com/v1/commentaries?'
MLS = '&competition=98'
MLS_REGULAR = MLS + '&matchType=Regular'
MLS_CUP = MLS + '&matchType=Cup'
USOPEN_CUP = '&competition=557'
CONCACAF_CL = '&competition=549'
LEAGUES_CUP = '&competition=1045'
ALL_STAR_GAME = '&competition=355'
FRIENDLY = '&competition=34'
# format: YYYY-MM-DD
DATE_FROM = '&dateFrom='
DATE_TO = '&dateTo='
SEASON = '&seasonId='


class MlsObject:
    def __init__(self, opta_id):
        self.opta_id = opta_id
    
    def __str__(self):
        return str(self.opta_id)


def call_api(url: str, params=None):
    """Call the MLS API at the given url, and return the json data and status code.

    Positional arguments:
    url -- the url to call

    Keyword arguments:
    params -- a dict of the http query parameters
    """
    headers = {
        'user-agent': USER_AGENT,
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.5'
    }
    r = None
    if params is not None:
        r = requests.get(url, headers=headers, params=params)
    else:
        r = requests.get(url, headers=headers)
    if r.status_code != 200:
        message = f'{url}\n{params}\n{r.status_code}: {r.reason}'
        logging.error(message)
        msg.send(message)
        return None, r.status_code
    else:
        data = r.json()
        return data, r.status_code

@util.time_dec(False)
def main():
    params = {
        'match_game_id': 2261459,
        'include': ['club', 'player', 'player_match'],
        'order_by': ['-commentary_period', '-commentary_minute', '-commentary_second', '-commentary_timestamp', '-commentary_opta_id']
    }
    request_url = 'https://stats-api.mlssoccer.com/v1/commentaries'
    data, status = call_api(request_url, params)
    print(status)
    print(data)


from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
import asyncio
from urllib.parse import urljoin
import logging
import aiohttp
import backoff
from pydantic import BaseModel, Field

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

class Competition(Enum):
    MLS = 98
    LEAGUES_CUP = 1045
    US_OPEN_CUP = 557
    CONCACAF_CL = 549

class MatchPeriod(Enum):
    NOT_STARTED = "NotStarted"
    FIRST_HALF = "FirstHalf"
    HALF_TIME = "HalfTime"
    SECOND_HALF = "SecondHalf"
    FULL_TIME = "FullTime"
    EXTRA_TIME = "ExtraTime"
    PENALTIES = "Penalties"

class Club(BaseModel):
    opta_id: int
    name: str
    abbreviation: str
    
class Venue(BaseModel):
    name: str
    city: Optional[str]
    
class MatchData(BaseModel):
    match_id: int = Field(alias="id")
    opta_id: int
    venue: Venue
    home_club: Club
    away_club: Club
    date: datetime
    period: MatchPeriod
    minute: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    is_final: bool

@dataclass
class MLSApiConfig:
    """Configuration for the MLS API client"""
    base_url: str = "https://stats-api.mlssoccer.com/v1/"
    user_agent: str = "MLSApiClient/1.0"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_calls: int = 10
    rate_limit_period: int = 1  # seconds
    
class MLSApiClient:
    def __init__(self, config: MLSApiConfig = MLSApiConfig()):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(self.config.rate_limit_calls)
        self._last_requests: List[float] = []

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": self.config.user_agent}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            
    def _handle_response_error(self, status: int, message: str):
        """Handle different HTTP error status codes"""
        if 400 <= status < 500:
            if status == 429:
                raise MLSApiRateLimitError(f"Rate limit exceeded: {message}")
            raise MLSApiClientError(f"Client error {status}: {message}")
        elif 500 <= status < 600:
            raise MLSApiServerError(f"Server error {status}: {message}")
        raise MLSApiError(f"Unknown error {status}: {message}")

    @backoff.on_exception(
        backoff.expo,
        (MLSApiServerError, MLSApiTimeoutError),
        max_tries=3
    )
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an API request with rate limiting and retries"""
        url = urljoin(self.config.base_url, endpoint)
        
        # Rate limiting
        async with self._rate_limiter:
            now = datetime.now().timestamp()
            if len(self._last_requests) >= self.config.rate_limit_calls:
                oldest = self._last_requests[0]
                if now - oldest < self.config.rate_limit_period:
                    await asyncio.sleep(self.config.rate_limit_period - (now - oldest))
                self._last_requests = self._last_requests[1:]
            self._last_requests.append(now)
            
            try:
                async with self._session.request(
                    method,
                    url,
                    params=params,
                    timeout=self.config.timeout
                ) as response:
                    if response.status != 200:
                        self._handle_response_error(
                            response.status,
                            await response.text()
                        )
                    return await response.json()
                    
            except asyncio.TimeoutError as e:
                raise MLSApiTimeoutError(f"Request to {url} timed out") from e
            except aiohttp.ClientError as e:
                raise MLSApiError(f"Request to {url} failed: {str(e)}") from e

    async def get_match(self, match_id: int) -> MatchData:
        """Get detailed match information"""
        data = await self._make_request(
            "GET",
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
        return MatchData.model_validate(data[0])

    async def get_matches(
        self,
        competition: Optional[Competition] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        club_id: Optional[int] = None
    ) -> List[MatchData]:
        """Get matches based on filters"""
        params = {}
        if competition:
            params["competition"] = competition.value
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        if club_id:
            params["club_id"] = club_id
            
        data = await self._make_request("GET", "matches", params=params)
        return [MatchData.model_validate_json(match) for match in data]

# Example usage:
async def main():
    async with MLSApiClient() as client:
        try:
            # Get a specific match
            match = await client.get_match(12345)
            print(f"Match: {match.home_club.name} vs {match.away_club.name}")
            
            # Get recent MLS matches
            matches = await client.get_matches(
                competition=Competition.MLS,
                date_from=datetime.now()
            )
            for match in matches:
                print(f"Found match: {match.home_club.name} vs {match.away_club.name}")
                
        except MLSApiError as e:
            logger.error(f"API error: {e}")

if __name__ == "__main__":
    asyncio.run(main())


if __name__ == '__main__':
    main()
