import asyncio
import datetime as dt
import json
# import logging as log
import subprocess
import sys
import traceback as tb
from contextlib import suppress
from pprint import pprint

import discord as d
from discord import utils
from discord.ext import commands
from discord.ext.commands import errors as errext

from misc import exceptions as exc
from misc import checks
from utils import utils as u

# log.basicConfig(level=log.INFO)


def get_prefix(bot, message):
    if isinstance(message.guild, d.Guild) and message.guild.id in u.settings['prefixes']:
        return u.settings['prefixes'][message.guild.id]
    return u.config['prefix']


bot = commands.Bot(command_prefix=get_prefix, formatter=commands.HelpFormatter(
    show_check_failure=True), description='Experimental miscellaneous bot')

# Send and print ready message to #testing and console after logon


@bot.event
async def on_ready():
    from cogs import booru, info, management, owner, tools

    for cog in (tools.Utils(bot), owner.Bot(bot), owner.Tools(bot), management.Administration(bot), info.Info(bot), booru.MsG(bot)):
        bot.add_cog(cog)
        print(f'COG : {type(cog).__name__}')

    # bot.loop.create_task(u.clear(booru.temp_urls, 30*60))

    if u.config['playing'] is not 'None':
        await bot.change_presence(game=d.Game(name=u.config['playing']))
    else:
        await bot.change_presence(game=None)

    print('\n\\ \\ \\ \\ \\ \\ \\ \\ \\\nC O N N E C T E D : {}\n/ / / / / / / / /\n'.format(bot.user.name))
    await bot.get_channel(u.config['info_channel']).send('**Started** ☀️ .')
    # u.notify('C O N N E C T E D')
    if u.temp:
        channel = bot.get_channel(u.temp['startup_chan'])
        message = await channel.get_message(u.temp['startup_msg'])
        await message.add_reaction('✅')
        u.temp.clear()


@bot.event
async def on_message(message):
    if message.author is not bot.user:
        await bot.process_commands(message)


@bot.event
async def on_error(error, *args, **kwargs):
    print('\n! ! ! ! !\nE R R O R : {}\n! ! ! ! !\n'.format(error), file=sys.stderr)
    tb.print_exc()
    await bot.get_user(u.config['owner_id']).send('**ERROR** ⚠\n```\n{}```'.format(error))
    await bot.get_channel(u.config['info_channel']).send('**ERROR** ⚠\n```\n{}```'.format(error))
    if u.temp:
        channel = bot.get_channel(u.temp['startup_chan'])
        message = await channel.get_message(u.temp['startup_msg'])
        await message.add_reaction('⚠')
        u.temp.clear()
    # u.notify('E R R O R')
    await bot.logout()
    u.close(bot.loop)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, errext.CheckFailure):
        await ctx.send('⛔️ **Insufficient permissions**', delete_after=10)
        await ctx.message.add_reaction('⛔️')
    elif isinstance(error, errext.CommandNotFound):
        print('INVALID COMMAND : {}'.format(error), file=sys.stderr)
        await ctx.message.add_reaction('❓')
    else:
        print('\n! ! ! ! ! ! !  ! ! ! ! !\nC O M M A N D  E R R O R : {}\n! ! ! ! ! ! !  ! ! ! ! !\n'.format(
            error), file=sys.stderr)
        tb.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await bot.get_user(u.config['owner_id']).send('**COMMAND ERROR** ⚠\n```\n{}```'.format(error))
        await bot.get_channel(u.config['info_channel']).send('**COMMAND ERROR** ⚠\n```\n{}```'.format(error))
        await exc.send_error(ctx, error)
        await ctx.message.add_reaction('⚠')
        # u.notify('C O M M A N D  E R R O R')

# d.opus.load_opus('opus')


async def wait(voice):
    asyncio.sleep(5)
    await voice.disconnect()


def after(voice, error):
    coro = voice.disconnect()
    future = asyncio.run_coroutine_threadsafe(coro, voice.loop)
    future.result()


@bot.command(name=',test', hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def test(ctx, message):
    if '<:N_:368917475531816962>' in message:
        await ctx.send('<:N_:368917475531816962>')
    # logs = []
    # async for entry in ctx.guild.audit_logs(limit=None, action=d.AuditLogAction.message_delete):
    #     logs.append(
    #         f'@{entry.user.name} deleted {entry.extra.count} messages from @{entry.target.name} in #{entry.extra.channel.name}')
    # pprint(logs)
    # channel = bot.get_channel(int(cid))
    # voice = await channel.connect()
    # voice.play(d.AudioSource, after=lambda: after(voice))

bot.run(u.config['token'])
