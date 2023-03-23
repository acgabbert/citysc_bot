import requests
from datetime import datetime
from bs4 import BeautifulSoup

from util import names

INJ_URL = 'https://www.mlssoccer.com/news/mlssoccer-com-injury-report'

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