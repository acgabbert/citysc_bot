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

standings_url = 'https://www.mlssoccer.com/standings/2024/conference#season=2024&live=false'
standings_xpath = f"//div[@class='mls-c-standings__wrapper']"

schedule_url = 'https://www.mlssoccer.com/schedule/scores#competition=all&club=17012&date='
schedule_url_ex = 'https://www.mlssoccer.com/schedule/scores#competition=all&club=17012&date=2023-07-10'
schedule_xpath = f"//div[@class='mls-c-schedule__matches']"
schedule_no_matches = 'mls-c-schedule__no-results-text'

def get_mls_driver(url, width=375, height=2800):
    service = ChromeService()
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-notifications')
    options.add_argument('--remote-debugging-port=9222')
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(width, height)
    
    driver.get(url)
    # click the onetrust cookie banner and wait until it goes away
    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[@id="onetrust-accept-btn-handler"]')))
        driver.find_element(By.XPATH, '//button[@id="onetrust-accept-btn-handler"]').click()
    except Exception as e:
        logger.debug(e)
    WebDriverWait(driver, 10).until(EC.all_of(
        # no cookie overlay
        EC.invisibility_of_element_located((By.XPATH, '//div[@id="onetrust-banner-sdk"]')),
        # nothing is loading
        EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div[data-testid="loading"]')),
        EC.invisibility_of_element_located((By.CLASS_NAME, 'img-responsive mls-o-loading mls-o-loading--glow')),
        EC.invisibility_of_element_located((By.CLASS_NAME, 'mls-o-loading mls-o-loading--glow mls-o-loading--line mls-o-loading--5rem')),
        EC.invisibility_of_element_located((By.CLASS_NAME, 'mls-o-loading mls-o-loading--glow mls-o-loading--line mls-o-loading--4rem')),
        EC.invisibility_of_element_located((By.CLASS_NAME, 'mls-o-loading mls-o-loading--glow mls-o-loading--line mls-o-loading--2rem')),
        EC.invisibility_of_element_located((By.CLASS_NAME, 'mls-o-loading mls-o-loading--glow mls-o-loading--table-cell')),
        EC.invisibility_of_element_located((By.CLASS_NAME, 'mls-o-loading mls-o-loading--glow mls-o-loading--50 mls-o-loading--table-cell')),
    ))
    
    return driver


def get_screenshot(url, outer_xpath, inner_xpath=None, title=None, driver=None):
    if driver is None:
        driver = get_mls_driver(url)
    logger.debug(f'getting {url}\nfinding elements by {outer_xpath}')
    elements = driver.find_elements(By.XPATH, outer_xpath)
    i = 0
    logger.debug(f'found {len(elements)} elements')
    filename = ''
    for element in elements:
        if inner_xpath is not None:
            title = element.find_elements(By.XPATH, inner_xpath)
            title = title[i].text
            i += 1
        screenshot = element.screenshot_as_png
        logger.debug(f'writing {title} to file')
        filename = write_screenshot(screenshot, title)
    return filename


def get_standings(url=standings_url, xpath=standings_xpath, driver=None):
    get_screenshot(url, xpath, '//tr[@class="mls-o-table__header-group mls-o-table__header-group--main"]', driver=driver)


def schedule_controller(url=schedule_url, xpath=schedule_xpath, driver=None):
    shots = 0
    date = datetime.now()
    while shots < 2 and date.year == datetime.now().year:
        dated_url = f'{url}{date.year}-{date.month}-{date.day}'
        logger.debug(f'checking {dated_url}')
        driver = get_mls_driver(dated_url)
        if len(driver.find_elements(By.CLASS_NAME, schedule_no_matches)) > 0:
            msg.send(f'No matches for {url}')
        else:
            title = ''
            if shots == 0:
                title = f'This Week'
            else:
                title = f'Next Week'
            file = get_screenshot(dated_url, xpath, title=title, driver=driver)
            pad_image(file)
            shots += 1
        date += timedelta(days=7)
        driver.quit()


def write_screenshot(data, filename):
    now = datetime.now()
    filename = f'png/{filename}-{now.month}-{now.day}.png'
    with open(filename, 'wb') as f:
        f.write(data)
        f.close()
    return filename


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
        schedule_controller()
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
