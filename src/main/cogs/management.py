import asyncio
import discord
import traceback
import discord
from discord.ext import commands
from misc import checks
from misc import exceptions as exc

class Administration:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='prunealluser')
    @commands.is_owner()
    async def prune_all_user(self, ctx, uid):
    channels = ctx.message.guild.channels
    member = ctx.message.guild.get_member(uid)
    history = {}
    c = 0
    for channel in channels:
        history[channel.id] = await channel.history().flatten()
        print('Added: ' + channel.id)
    for channel, messages in history.items():
        for message in messages:
            if message.author is member:
                await message.delete()
                c += 1
    await ctx.send('✅ `' + c + '` **messages deleted from the server.**')
