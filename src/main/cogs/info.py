import asyncio
import traceback as tb

import discord as d
from discord.ext import commands

from misc import exceptions as exc
from utils import utils as u


class Info:

    def __init__(self, bot):
        self.bot = bot

    # @commands.command(name='helptest', aliases=['h'], hidden=True)
    # async def list_commands(self, ctx):
    #     embed = d.Embed(title='All possible commands:', color=ctx.me.color)
    #     embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.avatar_url)
    #     embed.add_field(
    #         name='Booru', value='\n{}bl umbrella command for managing blacklists'.format(u.config['prefix']))
    #
    #     await ctx.send(embed=embed)

    @commands.command(hidden=True)
    async def hi(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)

        hello = 'Hewwo, {}.'.format(ctx.author.mention)
        if ctx.author.id == checks.owner_id:
            hello += '.. ***Master.*** uwu'
        elif ctx.author.guild_permissions.administrator:
            hello = '{} **Admin** {}'.format(hello[:7], hello[7:])
        elif ctx.author.guild_permissions.ban_members:
            hello = '{} **Mod** {}'.format(hello[:7], hello[7:])
        await dest.send(hello)

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
