import asyncio
import discord
import traceback
from discord.ext import commands
from cogs import booru
from misc import checks
from misc import exceptions as exc
from utils import formatter

class Utils:

    def __init__(self, bot):
        self.bot = bot

    def last():
        pass

    @commands.command(name='last', aliases=['l', ','], brief='Reinvokes last command', description='Reinvokes previous command executed', hidden=True)
    async def last_command(self, ctx):
        try:
            # await ctx.invoke(command, args)
            await ctx.send('`' + booru.last_command[ctx.message.author.id] + '`')
        except Exception:
            await ctx.send(exceptions.base)
            traceback.print_exc(limit=1)

    # [prefix]ping -> Pong!
    @commands.command(aliases=['p'], brief='Pong!', description='Returns latency from bot to Discord servers, not to user')
    @checks.del_ctx()
    async def ping(self, ctx):
        try:
            await ctx.send(ctx.message.author.mention + '  🏓  `' + str(int(self.bot.latency * 1000)) + 'ms`', delete_after=5)
        except Exception:
            await ctx.send(exceptions.base)
            traceback.print_exc(limit=1)

    @commands.command(aliases=['pre'], brief='List bot prefixes', description='Shows all used prefixes')
    @checks.del_ctx()
    async def prefix(self, ctx):
        try:
            await ctx.send('**Prefix:** `,` or ' + ctx.me.mention)
        except Exception:
            await ctx.send(exceptions.base)
            traceback.print_exc(limit=1)

    @commands.group(name=',send', aliases=[',s'], hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def send(self, ctx):
        pass

    @send.command(name='guild', aliases=['g', 'server', 's'])
    async def send_guild(self, ctx, guild, channel, *message):
        await discord.utils.get(self.bot.get_all_channels(), guild__name=guild, name=channel).send(formatter.tostring(message))
    @send.command(name='user', aliases=['u', 'member', 'm'])
    async def send_user(self, ctx, user, *message):
        await discord.utils.get(self.bot.get_all_members(), id=int(user)).send(formatter.tostring(message))
