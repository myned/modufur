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
import discord
import traceback
from discord import utils
from discord.ext import commands
from cogs import booru, info, tools
from misc import checks
from misc import exceptions as exc

bot = commands.Bot(command_prefix=commands.when_mentioned_or(config['prefix']), description='Experimental booru bot')

# Send and print ready message to #testing and console after logon
@bot.event
async def on_ready():
    if isinstance(bot.get_channel(config['startup_channel']), discord.TextChannel):
        await bot.get_channel(config['startup_channel']).send('H3l1(0) hOw aR3? **H4vE dAy.** 🌈')
    print('Connected.')
    print('Username: ' + bot.user.name)
    print('-------')

# Close connection to Discord - immediate offline
@bot.command(name=',die', aliases=[',d', ',close', ',kill'], brief='Kills the bot', description='BOT OWNER ONLY\nCloses the connection to Discord', hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def die(ctx):
    try:
        if isinstance(bot.get_channel(config['startup_channel']), discord.TextChannel):
            await bot.get_channel(config['shutdown_channel']).send('Am g0 by3e333333eee. **H4v3 n1GhT.** 💤')
        await bot.close()
        print('-------')
        print('Closed.')
    except Exception:
        await ctx.send(exc.base)
        traceback.print_exc(limit=1)

# Invite bot to bot owner's server
@bot.command(name=',invite', aliases=[',inv', ',link'], brief='Invite the bot', description='BOT OWNER ONLY\nInvite the bot to a server (Requires admin)', hidden=True)
@commands.is_owner()
@checks.del_ctx()
async def invite(ctx):
    try:
        await ctx.send('🔗 https://discordapp.com/oauth2/authorize?&client_id=' + str(config['client_id']) + '&scope=bot&permissions=' + str(config['permissions']))
    except Exception:
        await ctx.send(exc.base)
        traceback.print_exc(limit=1)

@bot.command(brief='[IN TESTING]', description='[IN TESTING]', hidden=True)
async def hi(ctx):
    try:
        hello = 'Hewwo, ' + ctx.message.author.mention + '.'
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
@commands.is_owner()
@checks.del_ctx()
async def test(ctx):
    embed = discord.Embed(title='Title', type='rich', description='Description.', url='https://static1.e621.net/data/4b/3e/4b3ec0c2e8580f418e4ce019dfd5ac32.png', color=discord.Color.from_rgb(255, 255, 255))
    embed = embed.set_image('https://static1.e621.net/data/27/0f/270fd28caa5e6d8bf542a76515848e02.png')
    embed = embed.set_footer('Footer')
    embed = embed.set_author('Author')
    embed = embed.set_thumbnail('https://cdn.discordapp.com/attachments/353251794161500163/357707620561453077/9d803ea3-b7fa-401f-89cf-f32cf21fe772.png')
    ctx.send('Embed test', embed=embed)

bot.add_cog(tools.Utils(bot))
bot.add_cog(info.Info(bot))
bot.add_cog(booru.MsG(bot))

bot.run(config['token'])
