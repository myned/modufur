import aiohttp
import ast
import re

from bs4 import BeautifulSoup
import lxml
from hurry.filesize import size, alternative
import tldextract as tld

from misc import exceptions as exc
from utils import utils as u


# async def get_harry(url):
#     content = await u.fetch(f'https://iqdb.harry.lu?url={url}')
#     soup = BeautifulSoup(content, 'html5lib')
#
#     if soup.find('div', id='show1').string is 'Not the right one? ':
#         parent = soup.find('th', string='Probable match:').parent.parent
#
#         post = await u.fetch(
#             f'https://e621.net/posts.json?id={re.search("show/([0-9]+)", parent.tr.td.a.get('href')).group(1)}',
#             json=True)
#         if (post['status'] == 'deleted'):
#             post = await u.fetch(
#                 f'https://e621.net/posts.json?id={re.search("#(\\d+)", post["delreason"]).group(1)}',
#                 json=True)
#
#         result = {
#             'source': f'https://e621.net/posts/{post["id"]}',
#             'artist': ', '.join(post['tags']['artist']),
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
        content = await u.fetch(f'https://api.kheina.com/v1/search', post={'url': url}, json=True)

        similarity = int(content['results'][0]['similarity'])
        if similarity < 55:
            return None

        if tld.extract(content['results'][0]['sources'][0]['source']).domain == 'furaffinity':
            submission = re.search('\\d+$', content['results'][0]['sources'][0]['source']).group(0)
            try:
                export = await u.fetch(f'https://faexport.spangle.org.uk/submission/{submission}.json', json=True)
                thumbnail = export['full']
            except AssertionError:
                thumbnail = ''
        else:
            thumbnail = ''

        result = {
            'source': content['results'][0]['sources'][0]['source'],
            'artist': content['results'][0]['sources'][0]['artist'] if content['results'][0]['sources'][0]['artist'] else 'unknown',
            'thumbnail': thumbnail,
            'similarity': str(similarity),
            'database': tld.extract(content['results'][0]['sources'][0]['source']).domain
        }

        return result

    except Exception:
        return None


async def query_saucenao(url):
    try:
        content = await u.fetch(
            f'https://saucenao.com/search.php?url={url}&api_key={u.config["saucenao_api"]}&output_type={2}',
            json=True)

        if content['header'].get('message', '') in (
                'Access to specified file was denied... ;_;',
                'Problem with remote server...',
                'image dimensions too small...'):
            raise exc.ImageError

        match = content['results'][0]

        similarity = int(float(match['header']['similarity']))
        if similarity < 55:
            return None

        source = match['data']['ext_urls'][0]
        for e in match['data']['ext_urls']:
            if 'furaffinity' in e:
                source = e
                break
        for e in match['data']['ext_urls']:
            if 'e621' in e:
                source = e
                break

        artist = 'unknown'
        for e in (
                'author_name',
                'member_name',
                'creator'):
            if e in match['data'] and match['data'][e]:
                artist = match['data'][e]
                break

        result = {
            'source': source,
            'artist': artist,
            'thumbnail': match['header']['thumbnail'],
            'similarity': str(similarity),
            'database': tld.extract(source).domain
        }

        return result

    except Exception:
        return None


async def get_post(url):
    try:
        content = await u.fetch(url, response=True)
        filesize = int(content.headers['Content-Length'])
        if filesize > 8192 * 1024:
            raise exc.SizeError(size(filesize, system=alternative))

        # Prioritize SauceNAO if e621/furaffinity, Kheina>SauceNAO if not
        result = await query_saucenao(url)
        if result:
            if not any(s in result['source'] for s in ('e621', 'furaffinity')):
                kheina = await query_kheina(url)
                if kheina:
                    result = kheina
        else:
            result = await query_kheina(url)

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
