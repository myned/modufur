import json

try:
    with open('config.json') as infile:
        config = json.load(infile)
        print('\"config.json\" loaded.')
except FileNotFoundError:
    with open('config.json', 'w') as outfile:
        json.dump({'client_id': 0, 'listed_ids': [0], 'owner_id': 0, 'permissions': 388160, 'prefix': ',', 'shutdown_channel': 0, 'startup_channel': 0, 'token': 'str'}, outfile, indent=4, sort_keys=True)
        raise FileNotFoundError('Config file not found: \"config.json\" created with abstract values. Restart \"run.py\" with correct values.')

import asyncio
import datetime as dt
import discord as d
import os
import subprocess
import sys
import traceback
from discord import utils
from discord.ext import commands
from cogs import booru, info, owner, management, tools
from misc import checks
from misc import exceptions as exc
from utils import utils as u

import logging
logging.basicConfig(level=logging.INFO)

print('PID {}'.format(os.getpid()))

bot = commands.Bot(command_prefix=config['prefix'], description='Experimental booru bot')

# Send and print ready message to #testing and console after logon
@bot.event
async def on_ready():
    global bot

    bot.add_cog(tools.Utils(bot))
    bot.add_cog(owner.Tools(bot))
    bot.add_cog(management.Administration(bot))
    bot.add_cog(info.Info(bot))
    bot.add_cog(booru.MsG(bot))

    # bot.loop.create_task(u.clear(booru.temp_urls, 30*60))

    if isinstance(bot.get_channel(config['startup_channel']), d.TextChannel):
        await bot.get_channel(config['startup_channel']).send('**Started.** ☀️')
    print('CONNECTED')
    print(bot.user.name)
    print('-------')

# Close connection to Discord - immediate offline
@bot.command(name=',die', aliases=[',d'], brief='Kills the bot', description='BOT OWNER ONLY\nCloses the connection to Discord', hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def die(ctx):
    try:
        if isinstance(bot.get_channel(config['startup_channel']), d.TextChannel):
            await bot.get_channel(config['shutdown_channel']).send('**Shutting down...** 🌙')
        await bot.close()
        print('-------')
        print('CLOSED')
    except Exception:
        await ctx.send(exc.base + '\n```' + traceback.format_exc(limit=1) + '```')
        traceback.print_exc(limit=1)

@bot.command(name=',restart', aliases=[',res', ',r'], hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def restart(ctx):
    try:
        print('RESTARTING')
        print('-------')
        if isinstance(bot.get_channel(config['startup_channel']), d.TextChannel):
            await bot.get_channel(config['shutdown_channel']).send('**Restarting...** 💤')
        os.execl(sys.executable, 'python3', 'run.py')
    except Exception:
        await ctx.send('{}\n```{}```'.format(exc.base, traceback.format_exc(limit=1)))
        traceback.print_exc(limit=1)

# Invite bot to bot owner's server
@bot.command(name=',invite', aliases=[',inv', ',link'], brief='Invite the bot', description='BOT OWNER ONLY\nInvite the bot to a server (Requires admin)', hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def invite(ctx):
    try:
        await ctx.send('🔗 https://discordapp.com/oauth2/authorize?&client_id={}&scope=bot&permissions={}'.format(config['client_id'], config['permissions']), delete_after=10)
    except Exception:
        await ctx.send('{}\n```{}```'.format(exc.base, traceback.format_exc(limit=1)))
        traceback.print_exc(limit=1)

@bot.command(brief='[IN TESTING]', description='[IN TESTING]', hidden=True)
async def hi(ctx):
    user = ctx.message.author
    try:
        hello = 'Hewwo, {}.'.format(user.mention)
        if user.id == checks.owner_id:
            hello += '.. ***Master.*** uwu'
        elif user.guild_permissions.administrator:
            hello = '{} **Admin** {}'.format(hello[:7], hello[7:])
        elif user.guild_permissions.ban_members:
            hello = '{} **Mod** {}'.format(hello[:7], hello[7:])
        await ctx.send(hello)
    except Exception:
        await ctx.send('{}\n```{}```'.format(exc.base, traceback.format_exc(limit=1)))
        traceback.print_exc(limit=1)

@bot.command(name=',test', hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def test(ctx):
    embed = d.Embed(title='/post/xxxxxx', url='https://static1.e621.net/data/4b/3e/4b3ec0c2e8580f418e4ce019dfd5ac32.png', timestamp=dt.datetime.utcnow(), color=ctx.me.color)
    embed.set_image(url='https://static1.e621.net/data/27/0f/270fd28caa5e6d8bf542a76515848e02.png')
    embed.set_footer(text='e621', icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
    embed.set_author(name='tags', url=ctx.message.author.avatar_url, icon_url=ctx.message.author.avatar_url)
    embed.add_field(name='Link', value='https://static1.e621.net/data/c2/55/c255792b5a307ee6efa51d6bb3edf878.jpg')
    await ctx.send(embed=embed)

bot.run(config['token'])
