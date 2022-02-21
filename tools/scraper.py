import aiohttp
import tldextract
import lightbulb
import pysaucenao

import config as c


plugin = lightbulb.Plugin('scraper')
sauce = pysaucenao.SauceNao(api_key=c.config['saucenao'], priority=(29, 40, 41)) # e621 > Fur Affinity > Twitter


async def reverse(urls):
    matches = []

    for url in urls:
        saucenao = await _saucenao(url)
        kheina = None

        if saucenao:
            matches.append(saucenao)
        else:
            pass

        if not saucenao and not kheina:
            matches.append(None)

    return matches

async def _saucenao(url):
    try:
        results = await sauce.from_url(url)
    except pysaucenao.FileSizeLimitException:
        raise pysaucenao.FileSizeLimitException(url)
    except pysaucenao.ImageSizeException:
        raise pysaucenao.ImageSizeException(url)
    except pysaucenao.InvalidImageException:
        raise pysaucenao.InvalidImageException(url)

    if results:
        return {
            'source': results[0].url,
            'artist': results[0].author_name or 'unknown',
            'thumbnail': results[0].thumbnail,
            'similarity': int(results[0].similarity),
            'index': tldextract.extract(results[0].index).domain}
    return

async def _kheina(url):
    pass

async def _fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={'User-Agent': 'Myned/Modufur (https://github.com/Myned/Modufur)'}) as response:
            return await response.json() if response.status == 200 else None


def load(bot):
    bot.add_plugin(plugin)
def unload(bot):
    bot.remove_plugin(plugin)
