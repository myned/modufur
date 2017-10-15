import asyncio
import json
import os
import pickle as pkl
import subprocess

import aiohttp
from pync import Notifier

print('\nPID : {}\n'.format(os.getpid()))


# def notify(message):
#     subprocess.run(['terminal-notifier', '-message', message, '-title',
#                     'Modumind', '-activate', 'com.apple.Terminal', '-appIcon', 'icon.png', '-sound', 'Ping'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


try:
    with open('config.json') as infile:
        config = json.load(infile)
        print('config.json loaded.')
except FileNotFoundError:
    with open('config.json', 'w') as outfile:
        json.dump({'client_id': 0, 'listed_ids': [0], 'owner_id': 0, 'permissions': 126016, 'prefix': ',',
                   'shutdown_channel': 0, 'startup_channel': 0, 'token': 'str'}, outfile, indent=4, sort_keys=True)
        raise FileNotFoundError(
            'Config file not found: config.json created with abstract values. Restart run.py with correct values.')


def setdefault(filename, default=None):
    try:
        with open(filename, 'rb') as infile:
            print('{} loaded.'.format(filename))
            return pkl.load(infile)
    except FileNotFoundError:
        with open(filename, 'wb+') as iofile:
            print('File not found: {} created and loaded with default values.'.format(filename))
            pkl.dump(default, iofile)
            iofile.seek(0)
            return pkl.load(iofile)


def load(filename):
    with open(filename, 'rb') as infile:
        return pkl.load(infile)


def dump(obj, filename):
    with open(filename, 'wb') as outfile:
        pkl.dump(obj, outfile)


tasks = setdefault('cogs/tasks.pkl', {})


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


async def fetch(url, *, params={}, json=False):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers={'user-agent': 'Modumind/0.0.1 (Myned)'}) as r:
            if json is True:
                return await r.json()
            return r
