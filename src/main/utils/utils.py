import asyncio
import json as jsn
import os
import pickle as pkl
import subprocess
from contextlib import suppress

import aiohttp
import discord as d

from misc import exceptions as exc

# from pync import Notifier


print('\nPID : {}\n'.format(os.getpid()))


# def notify(message):
#     subprocess.run(['terminal-notifier', '-message', message, '-title',
#                     'Modumind', '-activate', 'com.apple.Terminal', '-appIcon', 'icon.png', '-sound', 'Ping'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


try:
    with open('config.json') as infile:
        config = jsn.load(infile)
        print('LOADED : config.json')
except FileNotFoundError:
    with open('config.json', 'w') as outfile:
        jsn.dump({'client_id': 0, 'info_channel': 0, 'owner_id': 0, 'permissions': 126016,
                  'playing': 'a game', 'prefix': [',', 'm,'], 'token': 'str'}, outfile, indent=4, sort_keys=True)
        raise FileNotFoundError(
            'FILE NOT FOUND : config.json created with abstract values. Restart run.py with correct values')


def setdefault(filename, default=None):
    try:
        with open(filename, 'rb') as infile:
            print('LOADED : {}'.format(filename))
            return pkl.load(infile)
    except FileNotFoundError:
        with open(filename, 'wb+') as iofile:
            print('FILE NOT FOUND : {} created and loaded with default values'.format(filename))
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


settings = setdefault('settings.pkl', {'del_ctx': [], 'prefixes': {}})
tasks = setdefault('cogs/tasks.pkl', {'auto_del': [], 'auto_qual': [], 'auto_rev': []})
temp = setdefault('temp.pkl', {})

RATE_LIMIT = 2.2
color = d.Color(0x1A1A1A)
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
    async with session.get(url, params=params, headers={'User-Agent': 'Myned/Modumind/dev'}) as r:
        if json:
            return await r.json()
        return await r.read()


# def geneate_embed(**kwargs):
#     embed = d.Embed(title=kwargs['title'], )

def get_kwargs(ctx, args, *, limit=False):
    destination = ctx
    remaining = list(args[:])
    rm = False
    lim = 1

    for flag in ('-d', '-dm'):
        if flag in remaining:
            destination = ctx.author

            remaining.remove(flag)

    for flag in ('-r', '-rm', '-remove', '-re', '-repl', '-replace'):
        if flag in remaining and ctx.author.permissions_in(ctx.channel).manage_messages:
            rm = True

            remaining.remove(flag)

    if limit:
        for arg in remaining:
            if arg.isdigit():
                if 1 <= int(arg) <= limit:
                    lim = int(arg)
                    remaining.remove(arg)
                    break
                else:
                    raise exc.BoundsError(arg)

    return {'destination': destination, 'remaining': remaining, 'remove': rm, 'limit': lim}
