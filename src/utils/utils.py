import json as jsn
import os
import pickle as pkl
from contextlib import suppress
from fractions import gcd
import math

import aiohttp
import discord as d
from discord import errors as err

from misc import exceptions as exc


print('\nPID : {}\n'.format(os.getpid()))


try:
    with open('config.json') as infile:
        config = jsn.load(infile)
        print('LOADED : config.json')

except FileNotFoundError:
    with open('config.json', 'w') as outfile:
        jsn.dump({'client_id': 0, 'owner_id': 0, 'permissions': 126016,
                  'playing': 'a game', 'prefix': [',', 'm,'], 'selfbot': False, 'token': 'str', 'saucenao_api': 'str'}, outfile, indent=4, sort_keys=True)
        print('FILE NOT FOUND : config.json created with abstract values. Restart run.py with correct values')


def setdefault(filename, default=None, json=False):
    if json:
        try:
            with open(filename, 'r') as infile:
                print(f'LOADED : {filename}')
                return jsn.load(infile)

        except FileNotFoundError:
            with open(filename, 'w+') as iofile:
                print(f'FILE NOT FOUND : {filename} created and loaded with default values')
                jsn.dump(default, iofile)
                iofile.seek(0)
                return jsn.load(iofile)
    else:
        try:
            with open(filename, 'rb') as infile:
                print(f'LOADED : {filename}')
                return pkl.load(infile)

        except FileNotFoundError:
            with open(filename, 'wb+') as iofile:
                print(f'FILE NOT FOUND : {filename} created and loaded with default values')
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


settings = setdefault('misc/settings.pkl', default={'del_ctx': [], 'del_resp': [], 'prefixes': {}})
tasks = setdefault('cogs/tasks.pkl', default={'auto_del': [], 'auto_hrt': [], 'auto_rev': []})
temp = setdefault('temp/temp.pkl', default={'startup': ()})
block = setdefault('cogs/block.json', default={'guild_ids': [], 'user_ids': []}, json=True)

cogs = {}
color = d.Color(0x1A1A1A)
last_commands = {}

asession = aiohttp.ClientSession()


async def fetch(url, *, params={}, json=False, response=False, text=False):
    async with asession.get(url, params=params, headers={
            'User-Agent': 'Myned/Modufur (https://github.com/Myned/Modufur)'}, ssl=False) as r:
        if json:
            return await r.json()
        elif response:
            return r
        elif text:
            return await r.text()
        else:
            return await r.read()


def generate_embed(ctx, *, title=d.Embed.Empty, kind='rich', description=d.Embed.Empty, url=d.Embed.Empty, timestamp=d.Embed.Empty, colour=color, footer={}, image=d.Embed.Empty, thumbnail=d.Embed.Empty, author={}, fields=[]):
    embed = d.Embed(title=title, type=kind, description=description, url=url, timestamp=timestamp, colour=colour if isinstance(ctx.channel, d.TextChannel) else color)

    if footer:
        embed.set_footer(text=footer.get('text', d.Embed.Empty), icon_url=footer.get('icon_url', d.Embed.Empty))
    if image:
        embed.set_image(url=image)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if author:
        embed.set_author(name=author.get('name', d.Embed.Empty), url=author.get('url', d.Embed.Empty), icon_url=author.get('icon_url', d.Embed.Empty))
    for field in fields:
        embed.add_field(name=field.get('name', d.Embed.Empty), value=field.get('value', d.Embed.Empty), inline=field.get('inline', True))

    return embed


def kwargs(args):
    params = list(args)
    lst = 'blacklist'

    for switch in ('-a', '--aliases'):
        if switch in params:
            lst = 'aliases'
            params.remove(switch)

    return params, lst

def get_kwargs(ctx, args, *, limit=False):
    remaining = list(args[:])
    rm = False
    lim = 1

    for flag in ('-r', '-rm', '--remove'):
        if flag in remaining:
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

    return {'remaining': remaining, 'remove': rm, 'limit': lim}


def get_aspectratio(a, b):
    divisor = gcd(a, b)
    return f'{int(a / divisor)}:{int(b / divisor)}'


def ci(pos, n):
    z = 1.96
    phat = float(pos) / n

    return (phat + z*z/(2*n) - z * math.sqrt((phat*(1-phat)+z*z/(4*n))/n))/(1+z*z/n)


async def add_reaction(message, reaction, errors=(err.NotFound, err.Forbidden)):
    sent = False

    with suppress(errors):
        await message.add_reaction(reaction)
        sent = True

    return sent
