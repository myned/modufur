import asyncio
import datetime as dt
import json
# import logging as log
import subprocess
import sys
import traceback as tb
from contextlib import suppress

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


bot = commands.Bot(command_prefix=get_prefix, description='Experimental miscellaneous bot')

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

  if u.config['playing'] is not 'None':
    await bot.change_presence(game=d.Game(name=u.config['playing']))
  else:
    await bot.change_presence(game=None)

  print('\n\\ \\ \\ \\ \\ \\ \\ \\ \\\nC O N N E C T E D : {}\n/ / / / / / / / /\n'.format(bot.user.name))
  await bot.get_channel(u.config['info_channel']).send('**Started** \N{BLACK SUN WITH RAYS} .')
  # u.notify('C O N N E C T E D')
  if u.temp:
    channel = bot.get_channel(u.temp['restart_ch'])
    message = await channel.get_message(u.temp['restart_msg'])
    await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
    u.temp.clear()


@bot.event
async def on_error(error, *args, **kwargs):
  print('\n! ! ! ! !\nE R R O R : {}\n! ! ! ! !\n'.format(error), file=sys.stderr)
  tb.print_exc()
  await bot.get_user(u.config['owner_id']).send('**ERROR** ⚠ `{}`'.format(error))
  await bot.get_channel(u.config['info_channel']).send('**ERROR** ⚠ `{}`'.format(error))
  # u.notify('E R R O R')
  await bot.logout()
  u.close(bot.loop)


@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, errext.CheckFailure):
    await ctx.send('\N{NO ENTRY} **Insufficient permissions.**', delete_after=10)
    await ctx.message.add_reaction('\N{NO ENTRY}')
  elif isinstance(error, errext.CommandNotFound):
    print('INVALID COMMAND : {}'.format(error), file=sys.stderr)
    await ctx.message.add_reaction('\N{CROSS MARK}')
  else:
    print('\n! ! ! ! ! ! !  ! ! ! ! !\nC O M M A N D  E R R O R : {}\n! ! ! ! ! ! !  ! ! ! ! !\n'.format(
        error), file=sys.stderr)
    tb.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    await bot.get_user(u.config['owner_id']).send('**COMMAND ERROR** ⚠ `{}`'.format(error))
    await bot.get_channel(u.config['info_channel']).send('**COMMAND ERROR** ⚠ `{}`'.format(error))
    await exc.send_error(ctx, error)
    await ctx.message.add_reaction('⚠')
    # u.notify('C O M M A N D  E R R O R')


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
async def test(ctx):
  def check(react, user):
    return reaction.emoji == '\N{THUMBS UP SIGN}'
  # channel = bot.get_channel(int(cid))
  # voice = await channel.connect()
  # voice.play(d.AudioSource, after=lambda: after(voice))
  test = await ctx.send('thumbs up!')
  while True:
    done, pending = await asyncio.wait([bot.wait_for('reaction_add', check=check), bot.wait_for('reaction_remove', check=check)], return_when=asyncio.FIRST_COMPLETED)
    await ctx.send('well doneeee')
  # bot.add_listener(on_reaction_add)
  # bot.add_listener(on_reaction_remove)

bot.run(u.config['token'])
