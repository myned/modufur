import aiohttp
import ast
import re

from bs4 import BeautifulSoup
from lxml import html
from hurry.filesize import size, alternative

from misc import exceptions as exc
from utils import utils as u


# async def get_harry(url):
#     content = await u.fetch('https://iqdb.harry.lu', params={'url': url})
#     soup = BeautifulSoup(content, 'html.parser')
#
#     if soup.find('div', id='show1').string is 'Not the right one? ':
#         parent = soup.find('th', string='Probable match:').parent.parent
#
#         post = await u.fetch(
#             'https://e621.net/post/show.json',
#             params={'id': re.search('show/([0-9]+)', parent.tr.td.a.get('href')).group(1)},
#             json=True)
#         if (post['status'] == 'deleted'):
#             post = await u.fetch(
#                 'https://e621.net/post/show.json',
#                 params={'id': re.search('#(\\d+)', post['delreason']).group(1)},
#                 json=True)
#
#         result = {
#             'source': f'https://e621.net/post/show/{post["id"]}',
#             'artist': ', '.join(post['artist']),
#             'thumbnail': parent.td.a.img.get('src'),
#             'similarity': re.search('\\d+', parent.tr[4].td.string).group(0),
#             'database': 'Harry.lu'
#             }
#
#         return result
#     else:
#         return False


async def get_kheina(url):
    content = await u.fetch('https://kheina.com', params={'url': url})
    soup = BeautifulSoup(content, 'html.parser')

    results = ast.literal_eval(soup.find('data', id='results').string)[-1]
    iqdbdata = ast.literal_eval(soup.find('data', id='iqdbdata').string)[0]

    result = {
        'source': results[3],
        'artist': results[4],
        'thumbnail': f'https://f002.backblazeb2.com/file/kheinacom/{results[1]}.jpg',
        'similarity': str(int(float(iqdbdata['similarity']))),
        'database': 'Kheina'
        }

    return result


async def get_saucenao(url):
    content = await u.fetch(
        'https://saucenao.com/search.php',
        params={'url': url, 'api_key': u.config['saucenao_api'], 'output_type': 2},
        json=True)
    results = content['results'][0]
    for i in range(len(content['results'])):
        if 'e621' in content['results'][i]['header']['index_name']:
            results = content['results'][i]

    if 'author_name' in results['data']:
        artist = 'author_name'
    elif 'member_name' in results['data']:
        artist = 'member_name'
    else:
        artist = 'creator'

    result = {
        'source': results['data']['ext_urls'][0],
        'artist': results['data'][artist],
        'thumbnail': results['header']['thumbnail'],
        'similarity': str(int(float(results['header']['similarity']))),
        'database': 'SauceNAO'
        }

    return result


async def get_post(url):
    try:
        content = await u.fetch(url, response=True)
        filesize = int(content.headers['Content-Length'])
        if filesize > 8192 * 1024:
            raise exc.SizeError(size(filesize, system=alternative))

        result = await get_kheina(url)
        if int(result['similarity']) < 55:
            result = await get_saucenao(url)
        if int(result['similarity']) < 55:
            raise exc.MatchError(re.search('\\/([^\\/]+)$', url).group(1))

        return result

    except aiohttp.InvalidURL:
        raise exc.MissingArgument


async def get_image(url):
    content = await u.fetch(url)

    value = html.fromstring(content).xpath(
        'string(/html/body/div[@id="content"]/div[@id="post-view"]/div[@class="content"]/div[2]/img/@src)')

    return value
