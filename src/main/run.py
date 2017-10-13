import asyncio
import datetime as dt
import json
import logging
import os
import subprocess
import sys
import traceback as tb

import aiohttp as aio
import discord as d
from discord import utils
from discord.ext import commands

from cogs import booru, info, management, owner, tools
from misc import exceptions as exc
from misc import checks
from utils import utils as u

try:
    with open('config.json') as infile:
        config = json.load(infile)
        print('\"config.json\" loaded.')
except FileNotFoundError:
    with open('config.json', 'w') as outfile:
        json.dump({'client_id': 0, 'listed_ids': [0], 'owner_id': 0, 'permissions': 126016, 'prefix': ',',
                   'shutdown_channel': 0, 'startup_channel': 0, 'token': 'str'}, outfile, indent=4, sort_keys=True)
        raise FileNotFoundError(
            'Config file not found: \"config.json\" created with abstract values. Restart \"run.py\" with correct values.')


logging.basicConfig(level=logging.INFO)

print('PID {}'.format(os.getpid()))

bot = commands.Bot(command_prefix=config['prefix'], description='Experimental booru bot')

# Send and print ready message to #testing and console after logon


@bot.event
async def on_ready():
    bot.add_cog(tools.Utils(bot))
    bot.add_cog(owner.Bot(bot, config))
    bot.add_cog(owner.Tools(bot))
    bot.add_cog(management.Administration(bot))
    bot.add_cog(info.Info(bot))
    bot.add_cog(booru.MsG(bot))

    u.session = aio.ClientSession(loop=bot.loop)

    # bot.loop.create_task(u.clear(booru.temp_urls, 30*60))

    if isinstance(bot.get_channel(config['startup_channel']), d.TextChannel):
        await bot.get_channel(config['startup_channel']).send('**Started.** ☀️')
    print('CONNECTED')
    print(bot.user.name)
    print('-------')


@bot.event
async def on_command_error(ctx, error):
    print(error)
    await ctx.send('{}\n```\n{}```'.format(exc.base, error))


async def on_reaction_add(r, u):
    print('Reacted')


async def on_reaction_remove(r, u):
    print('Removed')


@bot.command(name=',test', hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def test(ctx):
    test = await ctx.send('Test')
    await test.add_reaction('✅')
    bot.add_listener(on_reaction_add)
    bot.add_listener(on_reaction_remove)

bot.run(config['token'])
