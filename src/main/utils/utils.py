import asyncio
import json as jsn
import os
import pickle as pkl
import subprocess
from contextlib import suppress

import aiohttp
import discord as d
from pync import Notifier

print('\nPID : {}\n'.format(os.getpid()))


# def notify(message):
#     subprocess.run(['terminal-notifier', '-message', message, '-title',
#                     'Modumind', '-activate', 'com.apple.Terminal', '-appIcon', 'icon.png', '-sound', 'Ping'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


try:
    with open('config.json') as infile:
        config = jsn.load(infile)
        print('config.json loaded.')
except FileNotFoundError:
    with open('config.json', 'w') as outfile:
        jsn.dump({'client_id': 0, 'info_channel': 0, 'owner_id': 0, 'permissions': 126016,
                  'playing': 'a game', 'prefix': ',', 'token': 'str'}, outfile, indent=4, sort_keys=True)
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


def load(filename, *, json=False):
    if not json:
        with open(filename, 'rb') as infile:
            return pkl.load(infile)
    else:
        with open(filename) as infile:
            return jsn.load(infile)


def dump(obj, filename, *, json=False):
    if not json:
        with open(filename, 'wb') as outfile:
            pkl.dump(obj, outfile)
    else:
        with open(filename, 'w') as outfile:
            jsn.dump(obj, outfile, indent=4, sort_keys=True)


settings = setdefault('settings.pkl', {'del_ctx': []})
tasks = setdefault('cogs/tasks.pkl', {'auto_del': [], 'auto_qual': [], 'auto_rev': []})
temp = setdefault('temp/temp.pkl', {})

RATE_LIMIT = 2.2
session = aiohttp.ClientSession()


# async def clear(obj, interval=10 * 60, replace=None):
#     if replace is None:
#         if type(obj) is list:
#             replace = []
#         elif type(obj) is dict:
#             replace = {}
#         elif type(obj) is int:
#             replace = 0
#         elif type(obj) is str:
#             replace = ''
#
#     while True:
#         obj = replace
#         asyncio.sleep(interval)


def close(loop):
    global session

    if session:
        session.close()

    loop.stop()
    pending = asyncio.Task.all_tasks()
    for task in pending:
        task.cancel()
        # with suppress(asyncio.CancelledError):
        #     loop.run_until_complete(task)
    # loop.close()

    print('Finished cancelling tasks.')


async def fetch(url, *, params={}, json=False):
    global session

    async with session.get(url, params=params, headers={'user-agent': 'Modumind/0.0.1 (Myned)'}) as r:
        if json:
            return await r.json()
        return await r.read()


# def geneate_embed(**kwargs):
#     embed = d.Embed(title=kwargs['title'], )

def get_args(ctx, args, *, rem=False, rm=False, lim=False):
    destination = ctx
    remaining = list(args[:])
    remove = False
    limit = 1

    if '-d' in remaining or '-dm' in remaining:
        destination = ctx.author

        try:
            remaining.remove('-d')
        except ValueError:
            remaining.remove('-dm')

    if rm:
        if ('-r' in remaining or '-rm' in remaining or '-remove' in remaining) and ctx.author.permissions_in(ctx.channel).manage_messages:
            remove = True
            print('remove')

            try:
                remaining.remove('-r')
            except ValueError:
                try:
                    remaining.remove('-rm')
                except ValueError:
                    remaining.remove('-remove')

    if lim:
        for arg in remaining:
            if len(arg) == 1:
                with suppress(ValueError):
                    if int(arg) <= 3 and int(arg) >= 1:
                        limit = int(arg)
                        remaining.remove(arg)
                        break
                    else:
                        raise exc.BoundsError(arg)

    if rem:
        if rm and lim:
            return destination, remaining, remove, limit
        if rm:
            return destination, remaining, remove
        if lim:
            return destination, remaining, limit
        return destination, remaining
    return destination
