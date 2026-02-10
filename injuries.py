import logging
import re
from typing import Dict, Optional
import requests
from datetime import datetime
from bs4 import BeautifulSoup

import util
from util import names

root = logging.getLogger('root')

INJ_URL = 'https://www.mlssoccer.com/news/mlssoccer-com-injury-report'
INJ_FILE = 'data/injuries.json'

class MlsInjuries:
    date_format = '%m/%d/%Y, %H:%M'

    def __init__(self, last_update: datetime, injuries: Dict, matchday: int = None):
        self.last_update = last_update
        self.injuries = injuries
        self.matchday = matchday
    

    def to_dict(self):
        retval = {}
        retval['updated'] = self.last_update.strftime(self.date_format) if self.last_update else 'Unknown'
        retval['injuries'] = self.injuries
        return retval
    

    def __str__(self):
        retval = f'---------------\nLast updated: {self.last_update}\n---------------'
        for team in self.injuries.items():
            retval += f'{team[0]}:\n'
            for inj in team[1]:
                retval += f'{inj}\n'
            retval += '\n'
        return retval



def get_injury_content() -> BeautifulSoup:
    data = requests.get(INJ_URL)
    data.encoding = 'utf-8'
    return BeautifulSoup(data.text, 'html.parser')


def populate_injuries(soup: BeautifulSoup) -> MlsInjuries:
    last_update = parse_datetime(soup)
    injury_obj = parse_injuries(soup)
    injury_obj = match_teams(injury_obj)
    matchday_int = parse_matchday(soup)
    injuries_obj = MlsInjuries(last_update, injury_obj, matchday_int)
    return injuries_obj


def parse_datetime(soup: BeautifulSoup) -> Optional[datetime]:
    """Returns a datetime object for when the article was last updated"""
    last_update = soup.find('div', class_='oc-c-article__date')
    if not last_update:
        root.warning('Could not find article date element on injury report page')
        return None
    p_tag = last_update.find('p')
    if not p_tag or not p_tag.get('data-datetime'):
        root.warning('Could not find datetime data in article date element')
        return None
    try:
        return datetime.strptime(p_tag['data-datetime'], '%m/%d/%Y %H:%M:%S')
    except (ValueError, KeyError) as e:
        root.warning(f'Could not parse injury report datetime: {e}')
        return None


def parse_matchday(soup: BeautifulSoup) -> int:
    pattern = re.compile(r"UPDATED\s+THROUGH:?\s+Matchday\s+(\d+)")
    matchday_number = None
    found_elements = soup.find_all(string=pattern)
    if found_elements:
        print(f"Found {len(found_elements)} matching elements.")
        first_match_text = found_elements[0].strip()
        match = pattern.search(first_match_text)
        if match:
            try:
                # group(1) corresponds to the first capturing group (\d+)
                matchday_number_str = match.group(1)
                matchday_number = int(matchday_number_str)
                print(f"Found text: '{first_match_text}'")
                print(f"Extracted Matchday Number: {matchday_number}")
            except ValueError:
                print(f"Found text '{first_match_text}', but could not convert '{matchday_number_str}' to an integer.")
            except IndexError:
                print(f"Found text '{first_match_text}', but couldn't extract the number group.")
        else:
            print(f"Found element with text '{first_match_text}', but regex couldn't extract number.")

    else:
        print("No text matching the pattern 'UPDATED THROUGH: Matchday [number]' found.")

    # You can now use the variable 'matchday_number' which holds the integer (or None if not found/extracted)
    if matchday_number is not None:
        print(f"\nThe extracted number is: {matchday_number}")
    return matchday_number

def parse_injuries(soup: BeautifulSoup) -> Dict:
    """Returns a dict with team names as key, injury list as value"""
    tags = soup.find_all('div', class_='d3-l-col__col-12')

    injury_list = {}

    for tag in tags:
        team_name = ''
        team_injuries = []
        name = tag.find(class_='mls-c-ranking-header__title')
        # if class mls-c-ranking-header__title in contents, then it's the name of a club
        # if <ul> in contents, then it's a list of injured players
        # there is a d3-l-col__col-12 within the outer d3-l-col__col-12 for a team name
        sibling = tag.next_sibling.next_sibling if tag.next_sibling else None
        if name and sibling:
            content = name.stripped_strings
            for string in content:
                if '\n' not in string:
                    team_name = string
            injury_items = sibling.find_all('li')
            for inj in injury_items:
                team_injuries.append(inj.text)
        injury_list[team_name] = team_injuries
    return injury_list


def match_teams(injury_obj: Dict) -> Dict:
    """Returns a dict with team opta ID as key, injury list as value"""
    teams = names.items()
    opta_injuries = {}

    for item in injury_obj.items():
        team = item[0]
        for t in teams:
            if team.lower() == t[1][0].lower():
                opta_injuries[t[0]] = item[1]
                break
            if t[1][1].lower() in team.lower():
                opta_injuries[t[0]] = item[1]
                break
    
    return opta_injuries


def main():
    retval = False
    soup = get_injury_content()
    inj_obj = populate_injuries(soup)
    newest_inj = {'matchday': inj_obj.matchday if inj_obj.matchday else "Unknown", 'injuries': {}}
    new_inj = inj_obj.to_dict()
    for key in new_inj['injuries']:
        new_key = str(key)
        newest_inj['injuries'][new_key] = new_inj['injuries'][key]
    util.write_json(newest_inj, INJ_FILE)
    return retval


if __name__ == '__main__':
    main()
