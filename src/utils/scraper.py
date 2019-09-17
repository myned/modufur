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

        content = await u.fetch('http://iqdb.harry.lu', params={'url': url})
        soup = BeautifulSoup(content, 'html.parser')
        source = soup.find_all('a', limit=2)[1].get('href')

        if source != '#':
            ident = re.search('show/([0-9]+)', source).group(1)
            post = await u.fetch('http://e621.net/post/show.json', params={'id': ident}, json=True)
            if (post['status'] == 'deleted'):
                ident = re.search('#(\\d+)', post['delreason']).group(1)
                post = await u.fetch('http://e621.net/post/show.json', params={'id': ident}, json=True)
            source = f'https://e621.net/post/show/{post["id"]}'
            similarity = re.search('\\d+', soup.find(string=re.compile('similarity'))).group(0) + '% Match'

            return post, source, similarity
        else:
            raise IndexError

    except IndexError:
        content = await u.fetch(
            'https://saucenao.com/search.php',
            params={
                'url': url,
                'api_key': u.config['saucenao_api'],
                'output_type': 2},
            json=True)
        result = content['results'][0]
        if 'author_name' in result['data']:
            artist = 'author_name'
        elif 'member_name' in result['data']:
            artist = 'member_name'
        else:
            artist = 'creator'
        post = {
            'file_url': result['header']['thumbnail'],
            'artist': [result['data'][artist]],
            'score': 'SauceNAO'}
        source = result['data']['ext_urls'][0]
        similarity = re.search('(\\d+)\\.', result['header']['similarity']).group(1) + '% Match'

        return post, source, similarity

        raise exc.MatchError(re.search('\\/([^\\/]+)$', url).group(1))

    except (AttributeError, ValueError, KeyError):
        raise exc.MissingArgument


async def get_image(url):
    content = await u.fetch(url)

    value = html.fromstring(content).xpath(
        'string(/html/body/div[@id="content"]/div[@id="post-view"]/div[@class="content"]/div[2]/img/@src)')

    return value
