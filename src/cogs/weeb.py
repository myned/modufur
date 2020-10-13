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

    async def refresh(self, browser, urls):
            message = ''

            for item, url in urls.items():
                browser.get(url)
                status = browser.find_elements_by_css_selector('#addToCartText-product-template')[0].text

                if status != 'SOLD OUT':
                    message += f'{item} is in stock!\n{url}\n'

            return message

    async def start(self):
        try:
            opts = Options()
            opts.headless = True
            browser = Chrome(executable_path='/usr/bin/chromedriver', options=opts)
            urls = {
                'Novelties': 'https://switchmod.net/collections/ended-gbs/products/gmk-metaverse-2?variant=31671816880208',
                'Royal': 'https://switchmod.net/collections/ended-gbs/products/gmk-metaverse-2?variant=31671816945744'
            }

            while self.weebing:
                message = await self.refresh(browser, urls)

                if message:
                    await self.bot.get_user(self.id).send(message)
                    await self.bot.get_user(u.config['owner_id']).send('Message sent')

                    browser.quit()
                    self.weebing = False

                await asyncio.sleep(60)

        except Exception as e:
            tb.print_exc()
            await self.bot.get_user(u.config['owner_id']).send(f'! ERROR !\n\n{repr(e)}')
