import asyncio
import datetime as dt
import json
import logging
import subprocess
import sys
import traceback as tb

import discord as d
from discord import utils
from discord.ext import commands
from discord.ext.commands import errors as errext

from misc import exceptions as exc
from misc import checks
from utils import utils as u

logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix=u.config['prefix'], description='Experimental booru bot')


# Send and print ready message to #testing and console after logon
@bot.event
async def on_ready():
    from cogs import booru, info, management, owner, tools

    bot.add_cog(tools.Utils(bot))
    bot.add_cog(owner.Bot(bot))
    bot.add_cog(owner.Tools(bot))
    bot.add_cog(management.Administration(bot))
    bot.add_cog(info.Info(bot))
    bot.add_cog(booru.MsG(bot))

    # bot.loop.create_task(u.clear(booru.temp_urls, 30*60))

    if isinstance(bot.get_channel(u.config['startup_channel']), d.TextChannel):
        await bot.get_channel(u.config['startup_channel']).send('**Started.** ☀️')
    print('\n\\ \\ \\ \\ \\ \\ \\ \\ \\\nC O N N E C T E D : {}\n/ / / / / / / / /\n'.format(bot.user.name))
    # u.notify('C O N N E C T E D')


@bot.event
async def on_error(error, *args, **kwargs):
    if isinstance(bot.get_channel(u.config['shutdown_channel']), d.TextChannel):
        await bot.get_channel(u.config['shutdown_channel']).send('**ERROR** ⚠️ {}'.format(error))
    u.close()
    await bot.logout()
    await bot.close()
    print('\n! ! ! ! !\nE R R O R : {}\n! ! ! ! !\n'.format(error), file=sys.stderr)
    tb.print_exc()
    # u.notify('E R R O R')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, errext.CheckFailure):
        await ctx.send('❌ **Insufficient permissions.**', delete_after=10)
    elif not isinstance(error, errext.CommandNotFound):
        print('\n! ! ! ! ! ! !  ! ! ! ! !\nC O M M A N D  E R R O R : {}\n! ! ! ! ! ! !  ! ! ! ! !\n'.format(
            error), file=sys.stderr)
        tb.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await exc.send_error(ctx, error)
        # u.notify('C O M M A N D  E R R O R')
    else:
        print('INVALID COMMAND : {}'.format(error), file=sys.stderr)


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
