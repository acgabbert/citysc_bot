from datetime import datetime, timedelta
import logging
from PIL import Image
import asyncio
from playwright.async_api import async_playwright, Browser, Page
import discord as msg

logger = logging.getLogger(__name__)

standings_url = 'https://www.mlssoccer.com/standings/2025/conference#season=2025&live=false'
schedule_url = 'https://www.mlssoccer.com/schedule/scores#competition=all&club=MLS-CLU-00001L&date='
schedule_no_matches = 'mls-c-schedule__no-results-text'

async def setup_browser():
    """Initialize and return a Playwright browser instance with proper configuration"""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage']
    )
    return browser, playwright

async def get_page(browser: Browser, url: str, width=375, height=2800) -> Page:
    """Create and configure a new page with the given dimensions"""
    page = await browser.new_page()
    await page.set_viewport_size({"width": width, "height": height})
    await page.goto(url)
    
    # Handle cookie banner
    try:
        accept_button = page.locator('button#onetrust-accept-btn-handler')
        await accept_button.click()
    except Exception as e:
        logger.debug(f"Cookie banner handling error: {e}")
    
    # Wait for loading states to complete
    await page.wait_for_selector('div[data-testid="loading"]', state='hidden')
    for loading_class in [
        'img-responsive mls-o-loading mls-o-loading--glow',
        'mls-o-loading mls-o-loading--glow mls-o-loading--line mls-o-loading--5rem',
        'mls-o-loading mls-o-loading--glow mls-o-loading--line mls-o-loading--4rem',
        'mls-o-loading mls-o-loading--glow mls-o-loading--line mls-o-loading--2rem',
        'mls-o-loading mls-o-loading--glow mls-o-loading--table-cell',
        'mls-o-loading mls-o-loading--glow mls-o-loading--50 mls-o-loading--table-cell'
    ]:
        await page.wait_for_selector(f'.{loading_class}', state='hidden', timeout=10000)
    
    return page

async def get_screenshot(url: str, outer_selector: str, inner_selector: str = None, title: str = None) -> str:
    """Take a screenshot of specified elements on the page"""
    browser, playwright = await setup_browser()
    try:
        page = await get_page(browser, url)
        elements = await page.query_selector_all(outer_selector)
        logger.debug(f'Found {len(elements)} elements')
        
        filename = ''
        for i, element in enumerate(elements):
            if inner_selector:
                titles = await page.query_selector_all(inner_selector)
                title = await titles[i].text_content()
            
            screenshot = await element.screenshot()
            filename = write_screenshot(screenshot, title)
            
        return filename
    finally:
        await browser.close()
        await playwright.stop()

async def get_standings():
    """Get standings screenshot"""
    return await get_screenshot(
        standings_url,
        'div.mls-c-standings__wrapper',
        'tr.mls-o-table__header-group.mls-o-table__header-group--main'
    )

async def schedule_controller():
    """Get schedule screenshots for current and next week"""
    shots = 0
    tries = 0
    date = datetime.now()
    browser, playwright = await setup_browser()
    
    try:
        while (shots < 2 and tries < 4) and date.year == datetime.now().year:
            dated_url = f'{schedule_url}{date.year}-{date.month}-{date.day}'
            logger.debug(f'Checking {dated_url}')
            
            page = await get_page(browser, dated_url)
            
            no_matches = await page.query_selector(f'.{schedule_no_matches}')
            if no_matches:
                msg.send(f'No matches for {dated_url}')
            else:
                title = 'This Week' if shots == 0 else 'Next Week'
                matches = await page.query_selector('div.mls-c-schedule__matches')
                if matches:
                    screenshot = await matches.screenshot()
                    file = write_screenshot(screenshot, title)
                    pad_image(file)
                    shots += 1
            
            date += timedelta(days=7)
            tries += 1
            
    finally:
        await browser.close()
        await playwright.stop()

def write_screenshot(data: bytes, filename: str) -> str:
    """Write screenshot data to a file"""
    now = datetime.now()
    filename = f'png/{filename}-{now.month}-{now.day}.png'
    with open(filename, 'wb') as f:
        f.write(data)
    return filename

def pad_image(filename: str):
    """Add padding to an image"""
    im = Image.open(filename)
    size = im.size
    padded = Image.new('RGB', (size[0]+10, size[1]+10), (255,255,255))
    padded.paste(im, (5,5))
    padded.save(filename)

async def main():
    try:
        await get_standings()
        message = "Successfully got standings via Playwright."
        logger.info(message)
        msg.send(message)
    except Exception as e:
        message = f'Error getting standings via Playwright.\n{str(e)}'
        logger.error(message)
        msg.send(message)

    try:
        await schedule_controller()
        message = "Successfully got schedule via Playwright."
        logger.info(message)
        msg.send(message)
    except Exception as e:
        message = f'Error getting schedule via Playwright.\n{str(e)}'
        logger.error(message)
        msg.send(message)

if __name__ == '__main__':
    asyncio.run(main())