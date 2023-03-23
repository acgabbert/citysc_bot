import requests
from datetime import datetime
from bs4 import BeautifulSoup

from util import names

INJ_URL = 'https://www.mlssoccer.com/news/mlssoccer-com-injury-report'

class MlsInjuries:
    def __init__(self, last_update, injuries):
        self.last_update = last_update
        self.injuries = injuries
    

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
    return BeautifulSoup(data.text, 'html.parser')


def populate_injuries(soup):
    last_update = parse_datetime(soup)
    injury_obj = parse_injuries(soup)
    injury_obj = match_teams(injury_obj)
    injuries_obj = MlsInjuries(last_update, injury_obj)
    return injuries_obj


def parse_datetime(soup):
    """Returns a datetime object for when the article was last updated"""
    last_update = soup.find('div', class_='oc-c-article__date')
    last_update = last_update.find('p')
    last_update = datetime.strptime(last_update['data-datetime'], '%m/%d/%Y %H:%M:%S')
    return last_update


def parse_injuries(soup):
    """Returns a dict with team names as key, injury list as value"""
    tags = soup.find_all('div', class_='d3-l-col__col-12')

    injury_list = {}

    for tag in tags:
        team_name = ''
        team_injuries = []
        name = tag.find(class_='mls-c-ranking-header__title')
        # there is a d3-l-col__col-12 within the outer d3-l-col__col-12 for a team name
        if name and tag.next_sibling.next_sibling:
            content = name.stripped_strings
            for string in content:
                if '\n' not in string:
                    team_name = string
            injuries = tag.next_sibling.next_sibling
            injuries = injuries.find_all('li')
            for inj in injuries:
                team_injuries.append(inj.text)
        injury_list[team_name] = team_injuries
    return injury_list


def match_teams(injury_obj):
    """Returns a dict with team opta ID as key, injury list as value"""
    teams = names.items()
    opta_injuries = {}

    for item in injury_obj.items():
        team = item[0]
        print(team)
        for t in teams:
            if team.lower() == t[1][0].lower():
                print(f'matched: {t[1][0]}, {team}')
                opta_injuries[t[0]] = item[1]
                break
    
    return opta_injuries


def main():
    soup = get_injury_content()
    inj_obj = populate_injuries(soup)
    print(inj_obj)


if __name__ == '__main__':
    main()


'''
data = requests.get(INJ_URL)

soup = BeautifulSoup(data.text, 'html.parser')

last_update = soup.find('div', class_='oc-c-article__date')
last_update = last_update.find('p')
last_update = datetime.strptime(last_update['data-datetime'], '%m/%d/%Y %H:%M:%S')
print(last_update.day)

tags = soup.find_all('div', class_='d3-l-col__col-12')

injury_list = {}

for tag in tags:
    team_name = ''
    team_injuries = []
    name = tag.find(class_='mls-c-ranking-header__title')
    # there is a d3-l-col__col-12 within the outer d3-l-col__col-12 for a team name
    if name and tag.next_sibling.next_sibling:
        content = name.stripped_strings
        for string in content:
            if '\n' not in string:
                team_name = string
        injuries = tag.next_sibling.next_sibling
        injuries = injuries.find_all('li')
        for inj in injuries:
            team_injuries.append(inj.text)
    injury_list[team_name] = team_injuries

teams = names.items()
opta_injuries = {}

for item in injury_list.items():
    team = item[0]
    print(team)
    for t in teams:
        if team.lower() == t[1][0].lower():
            print(f'matched: {t[1][0]}, {team}')
            opta_injuries[t[0]] = item[1]
            break

print(opta_injuries)

# if class mls-c-ranking-header__title in contents, then it's the name of a club
# if <ul> in contents, then it's a list of injured players
'''