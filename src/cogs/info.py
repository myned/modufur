import asyncio
import traceback as tb

import discord as d
from discord.ext import commands as cmds

from misc import exceptions as exc
from utils import utils as u


class Info:

    def __init__(self, bot):
        self.bot = bot

    # @cmds.command(name='helptest', aliases=['h'], hidden=True)
    # async def list_commands(self, ctx):
    #     embed = d.Embed(title='All possible commands:', color=ctx.me.color)
    #     embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.avatar_url)
    #     embed.add_field(
    #         name='Booru', value='\n{}bl umbrella command for managing blacklists'.format(u.config['prefix']))
    #
    #     await ctx.send(embed=embed)

    @cmds.group(name='info', aliases=['i'], hidden=True)
    async def info(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('<embed>BOT INFO</embed>')

    @info.command(aliases=['g'], brief='Provides info about a guild')
    async def guild(self, ctx, guild_id: int):
        guild = d.utils.get(self.bot.guilds, id=guild_id)

        if guild:
            await ctx.send(guild.name)
        else:
            await ctx.send(f'**Not in any guilds by the id of: ** `{guild_id}`')

    @info.command(aliases=['u'], brief='Provides info about a user')
    async def user(self, ctx, user: d.User):
        pass
