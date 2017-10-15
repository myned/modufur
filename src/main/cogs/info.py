import asyncio
import traceback as tb

import discord
from discord.ext import commands

from misc import exceptions as exc


class Info:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    async def hi(ctx):
        user = ctx.author

        hello = 'Hewwo, {}.'.format(user.mention)
        if user.id == checks.owner_id:
            hello += '.. ***Master.*** uwu'
        elif user.guild_permissions.administrator:
            hello = '{} **Admin** {}'.format(hello[:7], hello[7:])
        elif user.guild_permissions.ban_members:
            hello = '{} **Mod** {}'.format(hello[:7], hello[7:])
        await ctx.send(hello)

    @commands.group(name='info', aliases=['i'])
    async def info(self, ctx):
        if invoked_subcommand is None:
            await ctx.send('<embed>BOT INFO</embed>')

    @info.command(aliases=['g', 'server', 's'], brief='Provides info about a guild', hidden=True)
    async def guild(self, ctx):
        pass

    @info.command(aliases=['u', 'member', 'm'], brief='Provides info about a user', hidden=True)
    async def user(self, ctx):
        pass
