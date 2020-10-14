from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options

import asyncio
import traceback as tb
from discord.ext import commands as cmds
from utils import utils as u


class Weeb(cmds.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.weebing = False

        with open('id.json') as f:
            self.id = int(f.readline())
            print('LOADED : id.json')

        if not self.weebing:
            self.weebing = True
            self.bot.loop.create_task(self.start())
            print('STARTED : weebing')

    async def refresh_switchmod(self, browser):
        message = ''
        urls = {
            'Novelties': 'https://switchmod.net/collections/ended-gbs/products/gmk-metaverse-2?variant=31671816880208',
            'Royal': 'https://switchmod.net/collections/ended-gbs/products/gmk-metaverse-2?variant=31671816945744'
        }

        for item, url in urls.items():
            browser.get(url)
            status = browser.find_elements_by_css_selector('#addToCartText-product-template')[0].text

            if status != 'SOLD OUT':
                message += f'{item} is in stock at Switchmod!\n<{url}>\n'

            await asyncio.sleep(5)

        return message

    async def refresh_deskhero(self, browser):
        message = ''
        url = 'https://www.deskhero.ca/products/gmk-metaverse-2'

        browser.get(url)
        royal_soldout = browser.find_elements_by_css_selector('#data-product-option-1-1')[0].get_attribute('data-soldout')
        novelties_soldout = browser.find_elements_by_css_selector('#data-product-option-1-3')[0].get_attribute('data-soldout')

        if royal_soldout != 'true':
            message += f'Royal is in stock at Deskhero!\n<{url}>\n'
        if novelties_soldout != 'true':
            message += f'Novelties is in stock at Deskhero!\n<{url}>\n'

        return message

    async def start(self):
        try:
            opts = Options()
            opts.headless = True
            browser = Chrome(executable_path='/usr/bin/chromedriver', options=opts)

            while self.weebing:
                message = await self.refresh_switchmod(browser)
                await asyncio.sleep(5)
                message += await self.refresh_deskhero(browser)

                if message:
                    await self.bot.get_user(self.id).send(message)
                    await self.bot.get_user(u.config['owner_id']).send('Something is in stock. Restart to keep checking')

                    browser.quit()
                    self.weebing = False

                await asyncio.sleep(60)

        except Exception as e:
            tb.print_exc()
            await self.bot.get_user(u.config['owner_id']).send(f'! ERROR !\n\n{repr(e)}')
