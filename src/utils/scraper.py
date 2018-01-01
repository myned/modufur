import asyncio
import re

from bs4 import BeautifulSoup
from lxml import html
from hurry.filesize import size, alternative

from misc import exceptions as exc
from utils import utils as u


async def get_post(url):
    try:
        image = await u.fetch(url, response=True)
        filesize = int(image.headers['Content-Length'])
        if filesize > 8192 * 1024:
            raise exc.SizeError(size(filesize, system=alternative))
        
    except ValueError:
        raise exc.MissingArgument

    await asyncio.sleep(u.RATE_LIMIT)

    content = await u.fetch('http://iqdb.harry.lu', params={'url': url})

    try:
        value = BeautifulSoup(content, 'html.parser').find_all('a')[1].get('href')
        if value != '#':
            ident = re.search('show/([0-9]+)', value).group(1)
            post = await u.fetch('http://e621.net/post/show.json', params={'id': ident}, json=True)
            return post
        else:
            raise IndexError

    except IndexError:
        try:
            raise exc.MatchError(re.search('\/([^\/]+)$', url).group(1))

        except AttributeError:
            raise exc.MissingArgument


async def get_image(url):
    content = await u.fetch(url)

    value = html.fromstring(content).xpath(
        'string(/html/body/div[@id="content"]/div[@id="post-view"]/div[@class="content"]/div[2]/img/@src)')

    return value
