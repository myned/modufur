import asyncio
import json
import traceback
from contextlib import suppress

import discord as d
from discord import errors as err
from discord.ext import commands
from discord.ext.commands import errors as errext

from utils import utils as u

owner_id = u.config['owner_id']


def is_owner():
    async def predicate(ctx):
        return ctx.message.author.id == owner_id
    return commands.check(predicate)


def is_admin():
    def predicate(ctx):
        return ctx.message.author.guild_permissions.administrator
    return commands.check(predicate)


def is_mod():
    def predicate(ctx):
        return ctx.message.author.guild_permissions.ban_members
    return commands.check(predicate)


def owner(ctx):
    return ctx.message.author.id == owner_id


def admin(ctx):
    return ctx.message.author.guild_permissions.administrator


def mod(ctx):
    return ctx.message.author.guild_permissions.ban_members


def is_nsfw():
    def predicate(ctx):
        if isinstance(ctx.message.channel, d.TextChannel):
            return ctx.message.channel.is_nsfw()
        return True
    return commands.check(predicate)


def del_ctx():
    async def predicate(ctx):
        if ctx.guild.id in u.settings['del_ctx'] and ctx.me.permissions_in(ctx.channel).manage_messages and isinstance(ctx.message.channel, d.TextChannel):
            with suppress(err.NotFound):
                await ctx.message.delete()
        return True
    return commands.check(predicate)
