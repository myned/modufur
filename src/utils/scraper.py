import aiohttp
import ast
import re

from bs4 import BeautifulSoup
import lxml
from hurry.filesize import size, alternative

from misc import exceptions as exc
from utils import utils as u


# async def get_harry(url):
#     content = await u.fetch('https://iqdb.harry.lu', params={'url': url})
#     soup = BeautifulSoup(content, 'html5lib')
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


async def query_kheina(url):
    try:
        content = await u.fetch('https://kheina.com', params={'url': url}, text=True)

        for e in ('&quot;', '&apos;'):
        content = content.replace(e, '')
    content = re.sub('<a href="/cdn-cgi/l/email-protection".+</a>', '', content)

    soup = BeautifulSoup(content, 'html5lib')

    if soup.find('data', id='error'):
        return False

    results = soup.find('data', id='results').string
    results = ast.literal_eval(results)
    iqdbdata = soup.find('data', id='iqdbdata').string
    iqdbdata = ast.literal_eval(iqdbdata)

    similarity = int(float(iqdbdata[0]['similarity']))
    if similarity < 55:
        return False

    for e in results:
        if iqdbdata[0]['iqdbid'] in e:
            match = e
            break

    result = {
        'source': match[3].replace('\\', ''),
        'artist': match[4],
        'thumbnail': f'https://f002.backblazeb2.com/file/kheinacom/{match[1]}.jpg',
        'similarity': str(similarity),
        'database': 'Kheina'
    }

        return result

    except Exception:
        return False


async def query_saucenao(url):
    try:
        content = await u.fetch(
            'https://saucenao.com/search.php',
            params={'url': url, 'api_key': u.config['saucenao_api'], 'output_type': 2},
        json=True)

    if content['header'].get('message', '') in (
            'Access to specified file was denied... ;_;',
            'Problem with remote server...',
            'image dimensions too small...'):
        raise exc.ImageError

    match = content['results'][0]

    similarity = int(float(match['header']['similarity']))
    if similarity < 55:
        return False

    source = match['data']['ext_urls'][0]
    for e in match['data']['ext_urls']:
        if 'e621' in e:
            source = e
            break

    artist = 'Unknown'
    for e in (
        'author_name',
        'member_name',
        'creator'
    ):
        if e in match['data']:
            artist = match['data'][e]
            break

    result = {
        'source': source,
        'artist': artist,
        'thumbnail': match['header']['thumbnail'],
        'similarity': str(similarity),
        'database': 'SauceNAO'
    }

        return result

    except Exception:
        return False


async def get_post(url):
    try:
        content = await u.fetch(url, response=True)
        filesize = int(content.headers['Content-Length'])
        if filesize > 8192 * 1024:
            raise exc.SizeError(size(filesize, system=alternative))

        result = await query_kheina(url)
        if not result:
            result = await query_saucenao(url)
        if not result:
            raise exc.MatchError(re.search('\\/([^\\/]+)$', url).group(1))

        return result

    except aiohttp.InvalidURL:
        raise exc.MissingArgument


async def get_image(url):
    content = await u.fetch(url)

    value = lxml.html.fromstring(content).xpath(
        'string(/html/body/div[@id="content"]/div[@id="post-view"]/div[@class="content"]/div[2]/img/@src)')

    return value
