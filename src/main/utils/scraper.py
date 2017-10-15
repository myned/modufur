from bs4 import BeautifulSoup
from lxml import html

from misc import exceptions as exc
from utils import utils as u


async def check_match(url):
    content = await u.fetch('http://iqdb.harry.lu', params={'url': url})

    try:
        value = BeautifulSoup(content, 'html.parser').find_all('a')[1].get('href')
    except IndexError:
        raise exc.MatchError

    if value != '#':
        return value
    else:
        raise exc.MatchError
