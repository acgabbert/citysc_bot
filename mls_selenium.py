from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from PIL import Image

from config import EXE_PATH

standings_url = 'https://www.mlssoccer.com/standings/2023/conference#season=2023&live=false'
standings_tag = 'mls-c-standings__wrapper'

schedule_url = 'https://www.mlssoccer.com/schedule/scores#competition=all&club=17012&date='
schedule_url_ex = 'https://www.mlssoccer.com/schedule/scores#competition=all&club=17012&date=2023-07-10'
schedule_tag = 'mls-c-schedule__matches'

def config_selenium_driver(width=375, length=2800):
    service = ChromeService(executable_path=EXE_PATH)
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-notifications')
    driver = webdriver.Chrome(options=options, service=service)
    # TODO this may need to be tweaked depending on how the screenshots turn out
    # widths:
    # - 325 = until PPG
    # - 375 = until GP
    # length = 2800 gets all of the standings
    driver.set_window_size(width, length)
    return driver


def get_mls_driver(url):
    driver = config_selenium_driver()
    driver.get(url)
    # click the onetrust cookie banner and wait until it goes away
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[@id="onetrust-accept-btn-handler"]')))
    driver.find_element(By.XPATH, '//button[@id="onetrust-accept-btn-handler"]').click()
    WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, '//div[@id="onetrust-banner-sdk"]')))
    
    return driver


# TODO consider changing tag to xpath since it might not always be a div@class=
def get_standings(url=standings_url, tag=standings_tag, driver=None):
    if driver is None:
        driver = get_mls_driver(url)
    #write_screenshot(driver.get_screenshot_as_png(), 'whole-page')
    elements = driver.find_elements(By.XPATH, f"//div[@class='{tag}']")
    i = 0
    for element in elements:
        # TODO find element for table title and add to filename
        # mls-o-table__header-text 
        title = element.find_elements(By.XPATH, '//tr[@class="mls-o-table__header-group mls-o-table__header-group--main"]')
        title = title[i].text
        i += 1
        #actions = ActionChains(driver)
        #actions.move_to_element(element).perform()
        screenshot = element.screenshot_as_png
        write_screenshot(screenshot, f'{title}')
    driver.quit()


# TODO add a "this week"/"next week" screenshot
# url https://www.mlssoccer.com/schedule/scores#competition=all&club=17012
def get_schedule(url=schedule_url, tag=schedule_tag, driver=None):
    now = datetime.now()
    this_week_url = f'{url}{now.year}-{now.month}-{now.day}'
    if driver is None:
        driver = get_mls_driver(this_week_url)
    element = driver.find_element(By.XPATH, f"//div[@class='{tag}']")
    screenshot = element.screenshot_as_png
    write_screenshot(screenshot, 'This Week')
    driver.quit()
    now = datetime.now() + timedelta(days=7)
    next_week_url = f'{url}{now.year}-{now.month}-{now.day}'
    driver = get_mls_driver(next_week_url)
    element = driver.find_element(By.XPATH, f"//div[@class='{tag}']")
    screenshot = element.screenshot_as_png
    write_screenshot(screenshot, 'Next Week')
    driver.quit()


def write_screenshot(data, filename):
    now = datetime.now()
    filename = f'png/{filename}-{now.month}-{now.day}.png'
    with open(filename, 'wb') as f:
        f.write(data)


def pad_image(filename):
    im = Image.open(filename)
    size = im.size
    # new white image
    padded = Image.new('RGB', (size[0]+10, size[1]+10), (255,255,255))
    padded.paste(im, (5,5))
    padded.save(filename)


if __name__ == '__main__':
    get_standings()
    get_schedule()
    pad_image('png/This Week-7-14.png')
    pad_image('png/Next Week-7-14.png')