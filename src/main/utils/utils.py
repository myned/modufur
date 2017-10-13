import asyncio
import json
import pickle as pkl

import aiohttp as aio


def setdefault(filename, default=None):
    try:
        with open(filename, 'rb') as infile:
            print('\"{}\" loaded.'.format(filename))
            return pkl.load(infile)
    except FileNotFoundError:
        with open(filename, 'wb+') as iofile:
            print('File not found: \"{}\" created and loaded with default values.'.format(filename))
            pkl.dump(default, iofile)
            iofile.seek(0)
            return pkl.load(iofile)


def load(filename):
    with open(filename, 'rb') as infile:
        return pkl.load(infile)


def dump(obj, filename):
    with open(filename, 'wb') as outfile:
        pkl.dump(obj, outfile)


background = setdefault('./cogs/background.pkl', {})

with open('config.json') as infile:
    config = json.load(infile)


async def clear(obj, interval=10 * 60, replace=None):
    if replace is None:
        if type(obj) is list:
            replace = []
        elif type(obj) is dict:
            replace = {}
        elif type(obj) is int:
            replace = 0
        elif type(obj) is str:
            replace = ''

    while True:
        obj = replace
        asyncio.sleep(interval)


session = None

HEADERS = {'user-agent': 'Modumind/0.0.1 (Myned)'}


async def fetch(url, *, params={}, json=False):
    global session, HEADERS
    async with session.get(url, params=params, headers=HEADERS) as r:
        if json is True:
            return await r.json()
        return r
