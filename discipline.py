import requests
from datetime import datetime
from bs4 import BeautifulSoup
import re
import logging
import unicodedata

import util
from util import names

logger = logging.getLogger(__name__)

DISC_URL = 'https://www.mlssoccer.com/news/mls-disciplinary-summary'
DISC_FILE = 'data/discipline.json'
YELLOWS_TITLE = 'Yellow Accumulation'

class MlsDiscipline:
    date_format = '%m/%d/%Y, %H:%M'

    def __init__(self, last_update, discipline):
        self.last_update = last_update
        self.discipline = discipline
    

    def to_dict(self):
        retval = {}
        retval['updated'] = self.last_update.strftime(self.date_format)
        retval['discipline'] = self.discipline
        return retval
    

    def __str__(self):
        retval = f'---------------\nLast updated: {self.last_update}\n---------------\n'
        for team in self.discipline.items():
            retval += f'{team[0]}:\n'
            for player in team[1].items():
                retval += f'{player[0]}\n'
                for disc in player[1]:
                    retval += f'- {disc}\n'
            retval += '\n'
        return retval



def get_discipline_content() -> BeautifulSoup:
    data = requests.get(DISC_URL)
    data.encoding = 'utf-8'
    return BeautifulSoup(data.text, 'html.parser')


def populate_discipline(soup):
    last_update = parse_datetime(soup)
    disc_obj = parse_discipline(soup)
    disc_obj = match_teams(disc_obj)
    discipline_retval = MlsDiscipline(last_update, disc_obj)
    return discipline_retval


def parse_datetime(soup):
    """Returns a datetime object for when the article was last updated"""
    str_id = 'As of'
    last_update = soup.find(string=re.compile(str_id)).split(f'{str_id} ')[1]
    last_update = datetime.strptime(last_update, '%B %d, %Y')
    return last_update


def parse_discipline(soup: BeautifulSoup):
    """Returns a dict with team names as key, discipline list as value"""
    tags = soup.find('div', class_='oc-c-article__body d3-l-grid--inner').find_all('div', class_='d3-l-col__col-12')
    #soup.prettify(formatter=lambda s: s.translate(str.maketrans('', '', '\u00c2\u00a0\xa0')))
    susp = tags[0]#.find_all('div', class_='oc-c-body-part oc-c-body-part--text')
    yellows = tags[1]#.find_all('div', class_='oc-c-body-part oc-c-body-part--text')
    disc_list = {}

    #susp_pattern = r'(?!\d)\w[\w\s\-\.]*\([A-Z]{2,4}\).*\n\n\n\n.*'#vs.\s[A-Z]{2,4}'
    susp_pattern = r'.*\(([A-Z]{2,4})\).*'
    susp_pattern_2 = r'.*vs\.\s+([A-Z]{2,4}).*(\n.*vs\.\s+[A-Z]{2,4}.*)*'
    # how to match accent marks??
    yellow = r'([\w\s\-\.]*)\(([A-Z]{2,4})\)'
    for i, tag in enumerate(susp):
        # suspension notices
        player = re.search(susp_pattern, tag.text)
        matches = None
        if player:
            matches = tag.find_next_sibling()
            #matches = re.search(susp_pattern_2, susp[i+2].text)
        else:
            continue
        if not matches:
            logger.debug(f'No matches for {tag}')
            continue
        name = player[0]
        team = player[1]
        #print(name, team)
        if team in disc_list:
            disc_list[team][name] = []
        else:
            disc_list[team] = {name: []}
        logger.debug(f'player: {player[0]}')
        logger.debug(f'team: {player[1]}')
        matches = matches.text.strip().splitlines()
        new_matches = []
        #print(u'\xa0' in name)
        for match in matches:
            new_match = match
            new_matches.append(new_match)
        disc_list[team][name] = new_matches
    for tag in yellows:
        # can't use capture groups here (with parentheses) - 
        # otherwise the returned strings will be empty
        players = tag.text
        yellow_list = re.findall(yellow, players)
        #yellow_stripped = list(map(str.strip, re.findall(yellow, players)))
        for p, t in yellow_list:
            p = str.strip(p)
            if t in disc_list:
                if YELLOWS_TITLE in disc_list[t]:
                    disc_list[t][YELLOWS_TITLE].append(p)
                else:
                    disc_list[t][YELLOWS_TITLE] = [p]
            else:
                disc_list[t] = {YELLOWS_TITLE: [p]}
    return disc_list


def match_teams(disc_obj):
    """Returns a dict with team opta ID as key, injury list as value"""
    teams = names.items()
    opta_disc = {}

    for item in disc_obj.items():
        team = item[0]
        for t in teams:
            if team.lower() == t[1][0].lower():
                opta_disc[t[0]] = item[1]
                break
            if t[1][2].lower() in team.lower():
                opta_disc[t[0]] = item[1]
                break
    
    return opta_disc


def main():
    soup = get_discipline_content()
    disc_obj = populate_discipline(soup)
    util.write_json(disc_obj.to_dict(), DISC_FILE)
    return util.file_changed(DISC_FILE)


if __name__ == '__main__':
    main()
