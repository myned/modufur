import aiohttp as aio
from bs4 import BeautifulSoup
from lxml import html

from misc import exceptions as exc
from utils import utils as u


async def check_match(url):
    r = await u.fetch('http://iqdb.harry.lu/?url={}'.format(url))
    soup = BeautifulSoup(await r.read(), 'html.parser')
    value = soup.find_all('a')[1].get('href')

    if value != '#':
        return value
    else:
        raise exc.MatchError(value)
