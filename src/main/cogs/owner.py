import asyncio
import code
import io
import os
import re
import sys
import traceback as tb

import discord as d
import pyrasite as pyr
from discord.ext import commands

from misc import exceptions as exc
from misc import checks
from utils import utils as u

nl = re.compile('\n')


class Bot:

    def __init__(self, bot):
        self.bot = bot

    # Close connection to Discord - immediate offline
    @commands.command(name=',die', aliases=[',d'], brief='Kills the bot', description='BOT OWNER ONLY\nCloses the connection to Discord', hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def die(self, ctx):
        if isinstance(self.bot.get_channel(u.config['startup_channel']), d.TextChannel):
            await self.bot.get_channel(u.config['shutdown_channel']).send('**Shutting down...** 🌙')
        # loop = self.bot.loop.all_tasks()
        # for task in loop:
        #     task.cancel()
        u.close()
        await self.bot.logout()
        await self.bot.close()
        print('\n/ / / / / / / / / / / /\nD I S C O N N E C T E D\n\\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\\n')
        # u.notify('D I S C O N N E C T E D')

    @commands.command(name=',restart', aliases=[',res', ',r'], hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def restart(self, ctx):
        print('\n| | | | | | | | | |\nR E S T A R T I N G\n| | | | | | | | | |\n')
        if isinstance(self.bot.get_channel(u.config['startup_channel']), d.TextChannel):
            await self.bot.get_channel(u.config['shutdown_channel']).send('**Restarting...** 💤')
        # u.notify('R E S T A R T I N G')
        # loop = self.bot.loop.all_tasks()
        # for task in loop:
        #     task.cancel()
        u.close()
        await self.bot.logout()
        await self.bot.close()
        os.execl(sys.executable, 'python3', 'run.py')

    # Invite bot to bot owner's server
    @commands.command(name=',invite', aliases=[',inv', ',link'], brief='Invite the bot', description='BOT OWNER ONLY\nInvite the bot to a server (Requires admin)', hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def invite(self, ctx):
        await ctx.send('🔗 https://discordapp.com/oauth2/authorize?&client_id={}&scope=bot&permissions={}'.format(u.config['client_id'], u.config['permissions']), delete_after=10)

    @commands.command(aliases=['presence', 'game'], hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def status(self, ctx, game):
        try:
            if game is not None:
                await self.bot.change_presence(game=d.Game(name=game))
            else:
                raise exc.NotFound
        except exc.NotFound:
            await ctx.send('❌ **No game given.**', delete_after=10)


class Tools:

    def __init__(self, bot):
        self.bot = bot

    def format(self, i='', o=''):
        if len(o) > 1:
            return '>>> {}\n{}'.format(i, o)
        else:
            return '>>> {}'.format(i)

    async def generate(self, d, i='', o=''):
        return await d.send('```python\n{}```'.format(self.format(i, o)))

    async def refresh(self, m, i='', o=''):
        global nl
        output = m.content[10:-3]
        if len(nl.findall(output)) <= 20:
            await m.edit(content='```python\n{}\n{}\n>>>```'.format(output, self.format(i, o)))
        else:
            await m.edit(content='```python\n{}```'.format(self.format(i, o)))

    async def generate_err(self, d, o=''):
        return await d.send('```\n{}```'.format(o))

    async def refresh_err(self, m, o=''):
        await m.edit(content='```\n{}```'.format(o))

    @commands.command(name=',console', aliases=[',con', ',c'], hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def console(self, ctx):
        def execute(msg):
            if msg.content == 'exit' and msg.author is ctx.author:
                raise exc.Abort
            elif msg.author is ctx.author and msg.channel is ctx.channel:
                return True
            else:
                return False

        try:
            console = await self.generate(ctx)
            exception = await self.generate_err(ctx)
            while not self.bot.is_closed():
                try:
                    exe = await self.bot.wait_for('message', check=execute)
                except exc.Abort:
                    raise exc.Abort
                finally:
                    await exe.delete()
                try:
                    sys.stdout = io.StringIO()
                    sys.stderr = io.StringIO()
                    exec(exe.content)
                except Exception:
                    await self.refresh_err(exception, tb.format_exc(limit=1))
                finally:
                    await self.refresh(console, exe.content, sys.stdout.getvalue())
                    sys.stdout = sys.__stdout__
                    sys.stderr = sys.__stderr__
        except exc.Abort:
            await ctx.send('↩️ **Exited console.**')
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            print('Reset sys output.')

    @commands.command(name='arbitrary', aliases=[',arbit', ',ar'])
    @commands.is_owner()
    @checks.del_ctx()
    async def arbitrary(self, ctx, *, exe):
        try:
            sys.stdout = io.StringIO()
            exec(exe)
            await self.generate(ctx, exe, sys.stdout.getvalue())
        except Exception:
            await ctx.send('```\n{}```'.format(tb.format_exc(limit=1)))
            tb.print_exc(limit=1)
        finally:
            sys.stdout = sys.__stdout__
            print('Reset stdout.')

    @commands.group(aliases=[',db'], hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def debug(self, ctx):
        console = await self.generate(ctx)

    @debug.command(name='inject', aliases=['inj'])
    async def _inject(self, ctx, *, input_):
        pass

    @debug.command(name='inspect', aliases=['ins'])
    async def _inspect(self, ctx, *, input_):
        pass
