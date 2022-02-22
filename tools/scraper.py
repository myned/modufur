import aiohttp
import tldextract
import lightbulb
import pysaucenao

import config as c


plugin = lightbulb.Plugin("scraper")
sauce = pysaucenao.SauceNao(api_key=c.config["saucenao"], priority=(29, 40, 41))  # e621 > Fur Affinity > Twitter


async def reverse(urls):
    return [await _saucenao(url) or await _kheina(url) for url in urls]


async def _saucenao(url):
    try:
        results = await sauce.from_url(url)
    except pysaucenao.FileSizeLimitException:
        raise pysaucenao.FileSizeLimitException(url)
    except pysaucenao.ImageSizeException:
        raise pysaucenao.ImageSizeException(url)
    except pysaucenao.InvalidImageException:
        raise pysaucenao.InvalidImageException(url)

    return (
        {
            "url": results[0].url,
            "artist": ", ".join(results[0].authors) or "Unknown",
            "thumbnail": results[0].thumbnail,
            "similarity": round(results[0].similarity),
            "source": tldextract.extract(results[0].index).domain,
        }
        if results
        else None
    )


async def _kheina(url):
    content = await _post("https://api.kheina.com/v1/search", {"url": url})

    if content["results"][0]["similarity"] < 50:
        return None

    return {
        "url": content["results"][0]["sources"][0]["source"],
        "artist": content["results"][0]["sources"][0]["artist"] or "Unknown",
        "thumbnail": f'https://cdn.kheina.com/file/kheinacom/{content["results"][0]["sources"][0]["sha1"]}.jpg',
        "similarity": round(content["results"][0]["similarity"]),
        "source": tldextract.extract(content["results"][0]["sources"][0]["source"]).domain,
    }


async def _post(url, data):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as response:
            return await response.json() if response.status == 200 else None


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
