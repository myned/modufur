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

logging.basicConfig(level=logging.INFO)

print('PID {}'.format(os.getpid()))

bot = commands.Bot(command_prefix=u.config['prefix'], description='Experimental booru bot')


# Send and print ready message to #testing and console after logon
@bot.event
async def on_ready():
    bot.add_cog(tools.Utils(bot))
    bot.add_cog(owner.Bot(bot))
    bot.add_cog(owner.Tools(bot))
    bot.add_cog(management.Administration(bot))
    bot.add_cog(info.Info(bot))
    bot.add_cog(booru.MsG(bot))

    u.session = aio.ClientSession(loop=bot.loop)

    # bot.loop.create_task(u.clear(booru.temp_urls, 30*60))

    if isinstance(bot.get_channel(u.config['startup_channel']), d.TextChannel):
        await bot.get_channel(u.config['startup_channel']).send('**Started.** ☀️')
    print('CONNECTED')
    print(bot.user.name)
    print('-------')


@bot.event
async def on_command_error(ctx, error):
    if not isinstance(error, commands.errors.CommandNotFound):
        print(error)
        await ctx.send('{}\n```\n{}```'.format(exc.base, error))


async def on_reaction_add(r, u):
    pass


async def on_reaction_remove(r, u):
    pass


async def reaction_add(r, u):
    bot.add_listener(on_reaction_add)
    print('Reacted')
    bot.remove_listener(on_reaction_remove)


async def reaction_remove(r, u):
    bot.add_listener(on_reaction_remove)
    print('Removed')
    bot.remove_listener(on_reaction_remove)


@bot.command(name=',test', hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def test(ctx):
    test = await ctx.send('Test')
    await test.add_reaction('✅')
    bot.add_listener(on_reaction_add)
    bot.add_listener(on_reaction_remove)

bot.run(u.config['token'])
