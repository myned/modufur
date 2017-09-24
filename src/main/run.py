import asyncio
import discord
import json
import traceback
from discord import utils
from discord.ext import commands
from cogs import booru, info, tools
from misc import checks
from misc import exceptions as exc

try:
    with open('config.json') as infile:
        config = json.load(infile)
        print('\"config.json\" loaded.')
except FileNotFoundError:
    with open('config.json', 'w') as outfile:
        json.dump({'client_id': 'int', 'owner_id': 'int', 'permissions': 'int', 'shutdown_channel': 'int', 'startup_channel': 'int',
        'token': 'str'}, outfile, indent=4, sort_keys=True)
        raise FileNotFoundError('Config file not found: \"config.json\" created with abstract values. Restart \"run.py\" with correct values.')

bot = commands.Bot(command_prefix=commands.when_mentioned_or(','), description='Experimental booru bot')

# Send and print ready message to #testing and console after logon
@bot.event
async def on_ready():
    await bot.get_channel(config['startup_channel']).send('Hello how are? **Have day.** 🌈\n<embed>[STARTUP-INFO]</embed>')
    print('Connected.')
    print('Username: ' + bot.user.name)
    print('-------')

# Close connection to Discord - immediate offline
@bot.command(name=',die', aliases=[',d', ',close', ',kill'], brief='Kills the bot', description='BOT OWNER ONLY\nCloses the connections to Discord', hidden=True)
@checks.del_ctx()
@commands.is_owner()
async def die(ctx):
    try:
        await ctx.send('Am go bye. **Have night.** 💤')
        # await bot.get_channel(config['shutdown_channel']).send('<embed>[SHUTDOWN-INFO]</embed>')
        await bot.close()
        print('-------')
        print('Closed.')
    except Exception:
        await ctx.send(exc.base)
        traceback.print_exc(limit=1)

# Invite bot to bot owner's server
@bot.command(name=',invite', aliases=[',inv', ',link'], brief='Invite the bot', description='BOT OWNER ONLY\nInvite the bot to a server (Requires admin)', hidden=True)
@checks.del_ctx()
@commands.is_owner()
async def invite(ctx):
    try:
        await ctx.send('🔗 ' + utils.oauth_url(config['client_id'], permissions=config['permissions'], guild=ctx.message.guild))
    except Exception:
        await ctx.send(exc.base)
        traceback.print_exc(limit=1)

@bot.command(brief='[IN TESTING]', description='[IN TESTING]', hidden=True)
async def hi(ctx):
    try:
        hello = 'Hello, ' + ctx.message.author.mention + '.'
        if ctx.message.author.id == checks.owner_id:
            hello += '.. ***Master.*** uwu'
        elif ctx.message.author.guild_permissions.administrator:
            hello = hello[:7] + '**Admin** ' + hello[7:]
        elif ctx.message.author.guild_permissions.ban_members:
            hello = hello[:7] + '**Mod** ' + hello[7:]
        await ctx.send(hello)
    except Exception:
        await ctx.send(exc.base)
        traceback.print_exc(limit=1)

@bot.command(hidden=True)
@checks.del_ctx()
async def test(ctx):
    pass

bot.add_cog(info.Info(bot))
bot.add_cog(tools.Utils(bot))
bot.add_cog(booru.MsG(bot))

bot.run(config['token'])
