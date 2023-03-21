import requests
from datetime import datetime
from bs4 import BeautifulSoup

INJ_URL = 'https://www.mlssoccer.com/news/mlssoccer-com-injury-report'

data = requests.get(INJ_URL)

soup = BeautifulSoup(data.text, 'html.parser')

last_update = soup.find('div', {'class': 'oc-c-article__date'})
last_update = last_update.find('p')
last_update = datetime.strptime(last_update['data-datetime'], '%m/%d/%Y %H:%M:%S')
print(last_update.day)