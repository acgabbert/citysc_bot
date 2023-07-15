from datetime import datetime, timedelta
import discord as msg
import logging
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import EXE_PATH

logger = logging.getLogger(__name__)

standings_url = 'https://www.mlssoccer.com/standings/2023/conference#season=2023&live=false'
standings_xpath = f"//div[@class='mls-c-standings__wrapper']"

schedule_url = 'https://www.mlssoccer.com/schedule/scores#competition=all&club=17012&date='
schedule_url_ex = 'https://www.mlssoccer.com/schedule/scores#competition=all&club=17012&date=2023-07-10'
schedule_xpath = f"//div[@class='mls-c-schedule__matches']"

def get_mls_driver(url, width=375, height=2800):
    service = ChromeService(executable_path=EXE_PATH)
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-notifications')
    driver = webdriver.Chrome(options=options, service=service)
    driver.set_window_size(width, height)
    
    driver.get(url)
    # click the onetrust cookie banner and wait until it goes away
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[@id="onetrust-accept-btn-handler"]')))
    driver.find_element(By.XPATH, '//button[@id="onetrust-accept-btn-handler"]').click()
    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, '//div[@id="onetrust-banner-sdk"]')))
    
    return driver


def get_screenshot(url, outer_xpath, inner_xpath=None, title=None, driver=None):
    if driver is None:
        driver = get_mls_driver(url)
    logger.debug(f'getting {url}\nfinding elements by {outer_xpath}')
    elements = driver.find_elements(By.XPATH, outer_xpath)
    i = 0
    logger.debug(f'found {len(elements)} elements')
    for element in elements:
        if inner_xpath is not None:
            title = element.find_elements(By.XPATH, inner_xpath)
            title = title[i].text
            i += 1
        screenshot = element.screenshot_as_png
        logger.debug(f'writing {title} to file')
        write_screenshot(screenshot, title)
    driver.quit()


# TODO consider changing tag to xpath since it might not always be a div@class=
def get_standings(url=standings_url, xpath=standings_xpath, driver=None):
    get_screenshot(url, xpath, '//tr[@class="mls-o-table__header-group mls-o-table__header-group--main"]')


# TODO add a "this week"/"next week" screenshot
# base url https://www.mlssoccer.com/schedule/scores#competition=all&club=17012&date=
def get_schedule(url=schedule_url, xpath=schedule_xpath, driver=None):
    now = datetime.now()
    this_week_url = f'{url}{now.year}-{now.month}-{now.day}'
    get_screenshot(this_week_url, xpath, title="This Week")
    next_week = datetime.now() + timedelta(days=7)
    next_week_url = f'{url}{next_week.year}-{next_week.month}-{next_week.day}'
    get_screenshot(next_week_url, xpath, title="Next Week")
    logger.debug(f'Schedule images complete, now padding them')
    pad_image(f'png/This Week-{now.month}-{now.day}.png')
    pad_image(f'png/Next Week-{now.month}-{now.day}.png')


def write_screenshot(data, filename):
    now = datetime.now()
    filename = f'png/{filename}-{now.month}-{now.day}.png'
    with open(filename, 'wb') as f:
        f.write(data)
        f.close()


def pad_image(filename):
    im = Image.open(filename)
    size = im.size
    # new white image
    padded = Image.new('RGB', (size[0]+10, size[1]+10), (255,255,255))
    padded.paste(im, (5,5))
    padded.save(filename)


def main():
    try:
        get_standings()
        message = "Successfully got standings via Selenium."
        logger.info(message)
        msg.send(message)
    except Exception as e:
        message = (
            f'Error getting standings via Selenium.\n'
            f'{str(e)}'
        )
        logger.error(message)
        msg.send(message)
    try:
        get_schedule()
        message = "Successfully got schedule via Selenium."
        logger.info(message)
        msg.send(message)
    except Exception as e:
        message = (
            f'Error getting schedule via Selenium.\n'
            f'{str(e)}'
        )
        logger.error(message)
        msg.send(message)



if __name__ == '__main__':
    main()