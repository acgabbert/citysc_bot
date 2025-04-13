import asyncio
import time
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone

import discord as msg
import mls_api as mls
import util
import match_constants as const
import player
import club
import injuries
import discipline
from api_client import MLSApiClient

logger = logging.getLogger(__name__)


class Match(mls.MlsObject):

    def __init__(self, opta_id):
        super().__init__(opta_id)
        # Core properties
        self.home = club.ClubMatch(-1)
        self.away = club.ClubMatch(-1)
        self.id = -1

        # TV info
        self.apple_tier = ""
        self.apple_url = ""
        self.broadcasters: List[str] = []

        # Match metadata
        self.venue = ""
        self.comp = ""
        self.comp_id = -1
        self.date = -1
        self.slug = ""
        self.is_aggregate = False
        self.leg = ""
        self.round_name = ""
        self.round_number = 0
        self.previous_match_id = -1
        self.previous_match_opta_id = -1

        # Match state
        self.minute = ""
        self.result_type = ""
        self.started = False
        self.is_final = False

        # Match content
        self.preview: List[str] = []
        self.feed: List[str] = []
        self.videos: List[tuple[str, str]] = []
        self.summary: List[str] = []

    @classmethod
    async def create(cls, opta_id: int) -> "Match":
        """Factory method to create and populate a Match instance"""
        match = cls(opta_id)
        data = await get_full_match_data(opta_id)
        match.update_injuries()
        match.update_discipline()

        match.update_from_data(data.get("data"))
        match.update_from_stats(data.get("stats"))
        match.update_from_schedule_info(data.get("info"))
        match.update_from_preview(data.get("preview"))
        match.update_from_lineups(data.get("lineups"))
        # match.update_from_feed(data.get("commentary"))
        # match.update_from_feed(data.get("summary"))
        # match.update_from_subs(data.get("subs"))
        match.update_from_managers(data.get("managers"))
        match.update_from_videos(data.get("videos"))

        return match

    @classmethod
    async def create_prematch(cls, opta_id: int) -> "Match":
        """Factory method to create and populate a Match instance"""
        match = cls(opta_id)
        data = await get_prematch_data(opta_id)

        match.update_from_data(data.get("data"))
        match.update_from_stats(data.get("stats"))
        match.update_from_schedule_info(data.get("info"))
        match.update_from_recent_form(data.get("recent_form"))
        match.update_injuries()
        match.update_discipline()

        return match
    
    async def refresh(self) -> None:
        data = await get_match_update(self.opta_id)
        self.update_from_data(data.get("data"), update=True)
        self.update_from_stats(data.get("stats"))
        self.update_from_lineups(data.get("lineups"))
        self.update_from_feed(data.get("summary"))
        self.update_from_videos(data.get("videos"))

    
    def get_date_time(self):
        """Return date, time in match thread format."""
        secs = int(self.date)
        date = time.strptime(time.ctime(secs))
        date_val = time.strftime('%B %d, %Y', date)
        time_val = time.strftime('%I:%M %p ', date)
        time_val += datetime.now().astimezone().tzname()
        # remove leading zero from time
        if time_val[0] == '0':
            time_val = time_val[1:]
        return date_val, time_val
    
    def __str__(self):
        retval = ''
        if self.home.opta_id != -1:
            retval += f'{self.home.full_name} vs. {self.away.full_name}'
        else:
            return super().__str__()
        return retval
    
    def __lt__(self, other):
        """Required in order to properly sort matches by date."""
        if self.date < other.date:
            return True
        else:
            return False
    
    def update_from_data(self, data: List[Dict[str, Any]], update: bool = False) -> None:
        """Update existing Match object from API response"""
        if not update:
            self.home = process_club(data["home_club"], data["home_club_match"])
            self.away = process_club(data["away_club"], data["away_club_match"])
        
        # process core match data
        self.venue = data.get("venue", {}).get("name", "Unknown")
        self.comp = self._process_competition_name(data)
        self.comp_id = data.get("competition", {}).get("opta_id", -1)
        self.round_name = data.get("round_name", "")
        self.round_number = data.get("round_number", 0)
        
        if data.get("leg") and "leg" in data["leg"].lower():
            self.leg = data.get("type", "")
            
        self.id = data.get("id", -1)
        self.previous_match_id = data.get("previous_match_id", -1)
        self.is_aggregate = data.get("is_aggregate", False)
        
        # Process match state
        self.date = self._process_date(data.get("date", 0))
        self.minute = data.get("minute_display", "")
        self.result_type = self._process_result_type(data)
        self.started = data.get("first_half_start") is not None
        self.is_final = data.get("is_final", False)
        
        if data.get("period") == "HalfTime":
            self.minute = "HT"

    def update_from_stats(self, data: List[Dict[str, Any]]) -> None:
        """Update match stats from API response data"""
        if not data:
            logger.debug(f"No stats data available for match {self.opta_id}")
            return

        for team_data in data:
            try:
                team_side = team_data.get("side")
                if not team_side:
                    logger.error(f"Missing side information in stats for match {self.opta_id}")
                    continue

                # Update stats for the appropriate existing team object
                if team_side == "home":
                    self._process_team_stats(self.home, team_data)
                elif team_side == "away":
                    self._process_team_stats(self.away, team_data)
                else:
                    logger.error(f"Invalid team side '{team_side}' in match {self.opta_id}")

            except Exception as e:
                logger.error(f"Error processing stats for match {self.opta_id}: {str(e)}")
                continue
    
    def update_from_preview(self, data: Dict[str, Any]) -> None:
        # clear existing state
        self.preview.clear()

        for row in data:
            self.preview.append(row['fact'])
    

    def update_from_lineups(self, data: List[Dict[str, Any]]) -> None:
        # clear existing state
        self.home.lineup.clear()
        self.away.lineup.clear()

        for p in data:
            team_id: int = p.get("club", {}).get("opta_id", -1)
            status: str = p.get("status", "")
            name = get_player_name(p.get("player", {}))
            formation_place: int = p.get("formation_place", -1)
            player_id: int = p.get("player", {}).get("opta_id", -1)
            adder = player.Player(player_id, name, status, formation_place, team_id)
            if team_id == self.home.opta_id and adder not in self.home.lineup:
                self.home.lineup.append(adder)
            elif team_id == self.away.opta_id and adder not in self.away.lineup:
                self.away.lineup.append(adder)
            else:
                logger.error(f'Error: player {name}, game {self.opta_id} does not match either team. {team_id}')

    def update_from_feed(self, data: List[Dict[str, Any]]) -> None:
        """Process a feed (summary or full feed)"""
        # clear existing state
        self.summary.clear()
        self.home.goalscorers.clear()
        self.away.goalscorers.clear()

        # process new state
        comments, scorers = process_feed(data)
        for id in scorers.keys():
            if id == self.home.opta_id:
                for p in scorers[id]:
                    name = p.split('(')[0].strip()
                    added_away = any(name in g for g in self.away.goalscorers)
                    added_home = any(name in g for g in self.home.goalscorers)
                    if '(OG)' in p and not added_away:
                        self.away.goalscorers.append(p)
                    elif not added_home:
                        self.home.goalscorers.append(p)
            elif id == self.away.opta_id:
                for p in scorers[id]:
                    name = p.split('(')[0].strip()
                    added_away = any(name in g for g in self.away.goalscorers)
                    added_home = any(name in g for g in self.home.goalscorers)
                    if '(OG)' in p and not added_home:
                        self.home.goalscorers.append(p)
                    elif not added_away:
                        self.away.goalscorers.append(p)
            else:
                logger.error(f'Scorers ID {id} does not match either team - {scorers[id]}')
        self.summary = comments
    

    def update_from_subs(self, data: List[Dict[str, Any]]) -> None:
        for p in data:
            off_name = get_player_name(p.get("off_player"))
            on_name = get_player_name(p.get("on_player"))
            minute = p.get("minute_display", "0'")
            if p.get("club", {}).get("opta_id", -1) == self.home.opta_id:
                self.home.subs[off_name] = (on_name, minute)
            elif p.get("club", {}).get("opta_id", -1) == self.away.opta_id:
                self.away.subs[off_name] = (on_name, minute)
    

    def update_from_managers(self, data: List[Dict[str, Any]]) -> None:
        for manager in data:
            team_id = manager.get("club", {}).get("opta_id", -1)
            first = manager.get("manager", {}).get("first_name")
            last = manager.get("manager", {}).get("last_name")
            name = f'{first} {last}'
            if team_id == self.home.opta_id:
                self.home.manager = name
            elif team_id == self.away.opta_id:
                self.away.manager = name
    

    def update_from_schedule_info(self, data: Dict[str, Any]) -> None:
        self.broadcasters.clear()
        self.slug = data.get("slug")
        self.apple_tier = data.get("appleSubscriptionTier", "")
        self.apple_url = data.get("appleStreamURL", "").split("?")[0]
        broadcasters: List[Dict[str, Any]] = data.get("broadcasters", [])
        for b in broadcasters:
            if b.get("broadcasterType") not in ['US TV', 'International Streaming', 'US Streaming']:
                continue
            if 'Apple' in b['broadcasterName']:
                self.broadcasters.append(f'[{b["broadcasterName"]}]({data["appleStreamURL"]})')
            elif len(b['broadcasterStreamingURL']) > 1:
                self.broadcasters.append(f'[{b["broadcasterName"]}]({b["broadcasterStreamingURL"]}) (US)')
            else:
                self.broadcasters.append(f'{b["broadcasterName"]} (US)')
    

    def update_from_videos(self, data: List[Dict[str, Any]]) -> None:
        # clear existing state
        self.videos.clear()
        
        vid_url = 'https://mlssoccer.com/video/'
        for vid in data:
            self.videos.append((vid['title'],f'{vid_url}{vid["slug"]}'))
    
    def update_injuries(self) -> None:
        try:
            inj = util.read_json(injuries.INJ_FILE)
            date_format = '%m/%d/%Y, %H:%M'
            last_updated = datetime.strptime(inj.get('updated', ""), date_format)
            delta = datetime.now() - last_updated
            if delta.days > 3:
                return
            inj = inj.get('injuries')
            self.home.injuries = inj.get(str(self.home.opta_id))
            self.away.injuries = inj.get(str(self.away.opta_id))
        except Exception as e:
            message = f'Failed to find injuries for {self.home.short_name} - {self.away.short_name}'
            msg.send(message)
            logger.error(message)
    
    def update_discipline(self) -> None:
        try:
            disc = util.read_json(discipline.DISC_FILE)
            disc = disc.get('discipline')
            self.home.discipline = disc.get(str(self.home.opta_id))
            self.away.discipline = disc.get(str(self.away.opta_id))
        except Exception as e:
            message = f'Failed to find discipline for {self.home.short_name} - {self.away.short_name}'
            msg.send(message)
            logger.error(message)

    def update_from_recent_form(self, data: List[Dict[str, Any]]) -> None:
        self.home.recent_form = data.get("firstClubFormGuide", "")
        self.away.recent_form = data.get("secondClubFormGuide", "")

    @staticmethod
    def _process_competition_name(data: Dict[str, Any]) -> str:
        """Process competition name with business logic"""
        comp_name = data.get("competition", {}).get("name", "")
        comp_type = data.get("type", "")
        if "Major League Soccer" in comp_name:
            if "Cup" in comp_type or "Best of" in comp_type:
                return "MLS Cup Playoffs"
            return "MLS"
        elif comp_name == "Major League Soccer - Regular Season":
            return "MLS"
        return comp_name
    
    @staticmethod
    def _process_date(date: int) -> int:
        """Process date with business logic"""
        if date > 999999999999:
            return date / 1000
        return date
    
    @staticmethod
    def _process_result_type(data: Dict[str, Any]) -> str:
        """Process result type with business logic"""
        result = data.get("result_type")
        
        if result == "FullTime" or result == "Aggregate" or result == "NormalResult":
            return "FT"
        elif result == "PenaltyShootout":
            return "FT-Pens"
        elif result == "AfterExtraTime":
            return "AET"
        elif result is None and data.get("period") == "FullTime":
            return "FT"
        
        return ""
    
    
    def _process_team_stats(self, team: club.ClubMatch, team_data: Dict[str, Any]) -> None:
        """Update stats for a specific team"""
        # Update basic stats
        team.goals = team_data.get("score", -1)
        
        # Update shootout score if penalties occurred
        if team_data.get("first_penalty_kick") is not None:
            team.shootout_score = team_data.get("shootout_score")

        # Process detailed statistics
        statistics = team_data.get("statistics", {})
        if not statistics:
            logger.debug(f"No detailed statistics for team {team.opta_id}")
            return

        # Update all standard stats fields
        for stat_field in const.STATS_FIELDS:
            value = statistics.get(stat_field, 0)  # Default to 0 if stat doesn't exist
            setattr(team, stat_field, value)

        # Calculate pass accuracy
        if team.total_pass > 0:
            accuracy = (team.accurate_pass / team.total_pass) * 100
            team.pass_accuracy = f"{accuracy:.1f}"
        else:
            team.pass_accuracy = "0.0"


def process_formation(data):
    """Process the formation matrix"""
    formation = []
    for row in data:
        for i in row:
            formation.append(i)
    return formation


def process_feed(data) -> list[str]:
    """Process a feed (summary or full feed)."""
    comments = []
    scorers = {}
    for comment in data:
        # in order from earliest to latest
        adder = ''
        if comment['minute_display'] is None or comment['period'] == 'FullTime':
            adder = f'⏱️ {comment["comment"]}'
        else:
            adder = f'{comment["minute_display"]} '
            if comment['type'] in const.FEED_EMOJI:
                adder += const.FEED_EMOJI[comment['type']]
            adder += f' {comment["comment"]}'
        if comment['type'] in ['goal', 'own goal', 'penalty goal']:
            p = comment['first_player'] # goalscorer
            name = get_player_name(p)
            minute = comment['minute_display']
            scorer = f'{name} ({minute}'
            if comment['type'] == 'own goal':
                scorer += ' OG'
            if comment['type'] == 'penalty goal':
                scorer += ' PEN'
            scorer += ')'
            tm = comment['first_club']['opta_id']
            if tm in scorers.keys():
                found = False
                for i, x in enumerate(scorers[tm]):
                    if name in x:
                        found = True
                        scorers[tm][i] = scorers[tm][i][:-1] + f', {scorer.split("(")[1][:-1]})'
                if not found:
                    scorers[tm].append(scorer)
            else:
                scorers[tm] = [scorer]
        comments.append(adder)
    return comments, scorers


def process_scorers(match_obj: Match, scorers: dict) -> Match:
    retval = match_obj
    tms = scorers.keys()
    for id in tms:
        # TODO do this more gracefully
        if id == match_obj.home.opta_id:
            for p in scorers[id]:
                name = p.split('(')[0].strip()
                added_away = any(name in g for g in retval.away.goalscorers)
                added_home = any(name in g for g in retval.home.goalscorers)
                if '(OG)' in p and not added_away:
                    retval.away.goalscorers.append(p)
                elif not added_home:
                    retval.home.goalscorers.append(p)
        elif id == match_obj.away.opta_id:
            for p in scorers[id]:
                name = p.split('(')[0].strip()
                added_away = any(name in g for g in retval.away.goalscorers)
                added_home = any(name in g for g in retval.home.goalscorers)
                if '(OG)' in p and not added_home:
                    retval.home.goalscorers.append(p)
                elif not added_away:
                    retval.away.goalscorers.append(p)
        else:
            logger.error(f'Scorers ID {id} does not match either team - {scorers[id]}')
    return retval


def process_club(club_obj: Dict[str, Any], club_match: Dict[str, Any]) -> club.ClubMatch:
    """Process club data. Should be called from get_match_data."""
    opta_id = club_obj['opta_id']
    retval = club.ClubMatch(opta_id=opta_id)
    retval.match_id = club_match['match_id']
    if retval.full_name == '':
        retval.full_name = club_obj['name']
        retval.abbrev = club_obj['abbreviation']
    formation = club_match['formation_matrix']
    if formation is not None:
        retval.formation_matrix = process_formation(formation)
    return retval


def get_player_name(player):
    name = player['full_name']
    if name is None:
        name = player['first_name'] + ' ' + player['last_name']
    return name


def process_stats(data, team: club.ClubMatch) -> club.ClubMatch:
    """Process stats fields from const.STATS_FIELDS"""
    team.goals = data.get("score", -1)
    if data['first_penalty_kick'] is not None:
        team.shootout_score = data['shootout_score']
    stats = data['statistics']
    for stat in const.STATS_FIELDS:
        try:
            setattr(team, stat, stats[stat])
        except KeyError:
            # field does not exist from api
            # set to 0 so we know it was attempted
            setattr(team, stat, 0)
    # calculate pass accuracy and save it as a string
    if team.total_pass > 0:
        pass_accuracy = (team.accurate_pass / team.total_pass) * 100
        team.pass_accuracy = '%.1f' % pass_accuracy
    return team


def get_injuries(match_obj: Match, force: bool = False) -> Match:
    retval = match_obj
    inj = util.read_json(injuries.INJ_FILE)
    date_format = '%m/%d/%Y, %H:%M'
    last_updated = datetime.strptime(inj['updated'], date_format)
    delta = datetime.now() - last_updated
    if delta.days > 2 and not force:
        return retval
    inj = inj['injuries']
    home_inj = []
    away_inj = []
    try:
        home_inj = inj[str(retval.home.opta_id)]
        away_inj = inj[str(retval.away.opta_id)]
    except Exception as e:
        # did not match
        logger.error(f'Failed to match injury opta IDs for {retval.home.opta_id}, {retval.away.opta_id}')
        logger.error(e)
    retval.home.injuries = home_inj
    retval.away.injuries = away_inj
    return retval


def get_discipline(match_obj: Match) -> Match:
    retval = match_obj
    disc = util.read_json(discipline.DISC_FILE)
    date_format = '%m/%d/%Y, %H:%M'
    last_updated = datetime.strptime(disc['updated'], date_format)
    """
    delta = datetime.now() - last_updated
    if delta.days > 2:
        return retval
    """
    disc = disc['discipline']
    home_disc = []
    away_disc = []
    if str(retval.home.opta_id) in disc.keys():
        home_disc = disc[str(retval.home.opta_id)]
    if str(retval.away.opta_id) in disc.keys():
        away_disc = disc[str(retval.away.opta_id)]
    retval.home.discipline = home_disc
    retval.away.discipline = away_disc
    return retval


async def get_prematch_data(match_id: int) -> Dict[str, Any]:
    """Get data for a pre-match thread (no stats, lineups, etc)"""
    async with MLSApiClient() as client:
        # first get match info that other requests may depend on
        match_info = await client.get_match_info(match_id)

        # Extract data needed for recent form
        home_club = match_info.get("home", {}).get("optaId")
        away_club = match_info.get("away", {}).get("optaId")
        match_date = match_info.get("matchDate", "")

        if isinstance(match_date, str):
            try:
                match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
                if match_date.tzinfo is not None:
                    match_date = match_date.astimezone(timezone.utc)
                else:
                    match_date = match_date.replace(tzinfo=timezone.utc)
            except Exception as e:
                logger.error(f"Invalid date format: {match_date}")

        if not isinstance(match_date, datetime):
            match_date = datetime.now()
        
        print(home_club, away_club, match_date.isoformat())
        tasks = {
            'recent_form': client.get_recent_form(
                club_id=home_club,
                second_club_id=away_club,
                match_date=match_date
            ),
            'data': client.get_match_data(match_id),
            'stats': client.get_match_stats(match_id),
            'preview': client.get_preview(match_id),
            'lineups': client.get_lineups(match_id),
            'managers': client.get_managers(match_id)
        }
        results = await asyncio.gather(*tasks.values())

        results_dict = {
            'info': match_info,
            **dict(zip(
                [k for k in tasks.keys()],
                results
            ))
        }

        return results_dict

async def get_full_match_data(opta_id: int) -> Dict[str, Any]:
    async with MLSApiClient() as client:
        tasks = {
            'stats': client.get_match_stats(opta_id),
            'data': client.get_match_data(opta_id),
            'info': client.get_match_info(opta_id),
            'preview': client.get_preview(opta_id),
            'lineups': client.get_lineups(opta_id),
            #'commentary': client.get_match_commentary(opta_id),
            'summary': client.get_summary(opta_id),
            'subs': client.get_subs(opta_id),
            'managers': client.get_managers(opta_id),
            'videos': client.get_videos(opta_id)
        }
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))
    
async def get_match_update(opta_id: int) -> Dict[str, Any]:
    async with MLSApiClient() as client:
        tasks = {
            'data': client.get_match_data(opta_id),
            'stats': client.get_match_stats(opta_id),
            'lineups': client.get_lineups(opta_id),
            'summary': client.get_summary(opta_id),
            'videos': client.get_videos(opta_id)
        }
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))

async def get_previous_match_data(opta_id: int) -> Dict[str, Any]:
    async with MLSApiClient() as client:
        tasks = {
            'data': client.get_match_data(opta_id),
            'stats': client.get_match_stats(opta_id)
        }
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))
    
async def get_match(opta_id: int) -> Match:
    m = Match(opta_id)
    data = await get_full_match_data(opta_id)
    m.update_from_data(data.get("data"))
    m.update_from_feed(data.get("feed"))
    m.update_from_stats(data.get("stats"))
    m.update_from_preview(data.get("preview"))
    m.update_from_lineups(data.get("lineups"))
    m.update_from_managers(data.get("managers"))
    m.update_from_subs(data.get("subs"))
    m.update_from_schedule_info(data.get("info"))

    return m


async def get_previous_match(match_obj: Match) -> Match:
    date = datetime.fromtimestamp(int(match_obj.date))
    date_from = date - timedelta(days=31)
    date_from = f'{date_from.year}-{date_from.month}-{date_from.day}'
    date_to = f'{date.year}-{date.month}-{date.day}'
    async with MLSApiClient() as client:
        sched = await client.get_schedule_deprecated(team=match_obj.home.opta_id, comp=match_obj.comp_id, date_from=date_from, date_to=date_to)
    
    prev_match = Match(-1)
    for m in sched:
        prev_match = await Match.create_prematch(m['optaId'])
        if prev_match.id == match_obj.previous_match_id:
            match_obj.previous_match_opta_id = prev_match.opta_id
            break
    if prev_match.home.opta_id == match_obj.away.opta_id:
        match_obj.away.previous_goals = prev_match.home.goals
        match_obj.home.previous_goals = prev_match.away.goals
    else:
        message = f'Previous match does not match!'
        logger.error(message)
        msg.send(message)
    return prev_match



@util.time_dec(False)
async def main():
    opta_id = 2415296
    match_obj: Match = await Match.create(opta_id)
    print(match_obj.away.lineup_str())
    print(match_obj.home.goals)


if __name__ == '__main__':
    asyncio.run(main())
