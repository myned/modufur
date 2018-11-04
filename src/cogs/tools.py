import asyncio
from datetime import datetime as dt
import mimetypes
import os
import tempfile
import traceback as tb
import webbrowser

import discord as d
from discord.ext import commands as cmds

#from run import config
from cogs import booru
from misc import exceptions as exc
from misc import checks
from utils import utils as u
from utils import formatter

youtube = None

tempfile.tempdir = os.getcwd()


class Utils:

    def __init__(self, bot):
        self.bot = bot

    @cmds.command(name='lastcommand', aliases=['last', 'l', ','], brief='Reinvokes last successful command', description='Executes last successfully executed command')
    async def last_command(self, ctx, arg='None'):
        try:
            context = u.last_commands[ctx.author.id]

            if arg == 'show' or arg == 'sh' or arg == 's':
                await ctx.send(f'`{context.prefix}{context.invoked_with} {" ".join(context.args[2:])}`', delete_after=7)
            else:
                await ctx.invoke(context.command, *context.args[2:], **context.kwargs)

        except KeyError:
            await ctx.send('**No last command**', delete_after=7)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    # Displays latency
    @cmds.command(aliases=['p'], brief='Pong!', description='Returns latency from bot to Discord servers, not to user')
    async def ping(self, ctx):
        await ctx.message.add_reaction('\N{TABLE TENNIS PADDLE AND BALL}')
        await ctx.send(ctx.author.mention + '  \N{TABLE TENNIS PADDLE AND BALL}  `' + str(round(self.bot.latency * 1000)) + 'ms`', delete_after=5)

    @cmds.command(aliases=['pre', 'prefixes'], brief='List bot prefixes', description='Shows all used prefixes')
    async def prefix(self, ctx):
        await ctx.send('**Prefix:** `{}`'.format('` or `'.join(u.settings['prefixes'][ctx.guild.id] if ctx.guild.id in u.settings['prefixes'] else u.config['prefix'])))

    @cmds.group(name=',send', aliases=[',s'], hidden=True)
    @cmds.is_owner()
    async def send(self, ctx):
        pass

    @send.command(name='guild', aliases=['g', 'server', 's'])
    async def send_guild(self, ctx, guild, channel, *, message):
        try:
            tempchannel = d.utils.find(lambda m: m.name == channel, d.utils.find(
                lambda m: m.name == guild, self.bot.guilds).channels)

            try:
                await tempchannel.send(message)

            except AttributeError:
                await ctx.send('**Invalid channel**', delete_after=7)
                await ctx.message.add_reaction('\N{CROSS MARK}')

        except AttributeError:
            await ctx.send('**Invalid guild**', delete_after=7)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @send.command(name='user', aliases=['u', 'member', 'm'])
    async def send_user(self, ctx, user, *, message):
        await d.utils.get(self.bot.get_all_members(), id=int(user)).send(message)
