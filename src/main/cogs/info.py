import asyncio
import discord
import traceback
from discord.ext import commands
from misc import exceptions as exc


class Info:

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='info', aliases=['i'])
    async def info(self, ctx):
        if invoked_subcommand is None:
            await ctx.send('<embed>BOT INFO</embed>')

    @info.command(aliases=['g', 'server', 's'], brief='Provides info about a guild', hidden=True)
    async def guild(self, ctx):
        try:
            guild = ''
        except Exception:
            await ctx.send(exc.base)
            traceback.print_exc(limit=1)

    @info.command(aliases=['u', 'member', 'm'], brief='Provides info about a user', hidden=True)
    async def user(self, ctx):
        try:
            user = ''
        except Exception:
            await ctx.send(exc.base)
            traceback.print_exc(limit=1)
