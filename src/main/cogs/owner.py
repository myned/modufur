import asyncio
import code
import io
import os
import re
import sys
import traceback as tb
from contextlib import suppress

import discord as d
import pyrasite as pyr
from discord.ext import commands

from misc import exceptions as exc
from misc import checks
from utils import utils as u


class Bot:

    def __init__(self, bot):
        self.bot = bot

    # Close connection to Discord - immediate offline
    @commands.command(name=',die', aliases=[',d'], brief='Kills the bot', description='BOT OWNER ONLY\nCloses the connection to Discord', hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def die(self, ctx):
        await ctx.message.add_reaction('🌙')

        await self.bot.get_channel(u.config['info_channel']).send('**Shutting down** 🌙 . . .')

        u.temp['startup_chan'] = ctx.channel.id
        u.temp['startup_msg'] = ctx.message.id
        u.dump(u.temp, 'temp.pkl')

        # loop = self.bot.loop.all_tasks()
        # for task in loop:
        #     task.cancel()
        await self.bot.logout()
        u.close(self.bot.loop)
        print('\n/ / / / / / / / / / / /\nD I S C O N N E C T E D\n\\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\ \\\n')
        # u.notify('D I S C O N N E C T E D')

    @commands.command(name=',restart', aliases=[',res', ',r'], hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def restart(self, ctx):
        await ctx.message.add_reaction('💤')

        print('\n| | | | | | | | | |\nR E S T A R T I N G\n| | | | | | | | | |\n')
        await self.bot.get_channel(u.config['info_channel']).send('**Restarting** 💤 . . .')
        # u.notify('R E S T A R T I N G')

        u.temp['startup_chan'] = ctx.channel.id
        u.temp['startup_msg'] = ctx.message.id
        u.dump(u.temp, 'temp.pkl')

        # loop = self.bot.loop.all_tasks()
        # for task in loop:
        #     task.cancel()
        await self.bot.logout()
        u.close(self.bot.loop)
        os.execl(sys.executable, 'python3', 'run.py')

    # Invite bot to bot owner's server
    @commands.command(name=',invite', aliases=[',inv', ',link'], brief='Invite the bot', description='BOT OWNER ONLY\nInvite the bot to a server (Requires admin)', hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def invite(self, ctx):
        await ctx.message.add_reaction('✉️')

        await ctx.send('https://discordapp.com/oauth2/authorize?&client_id={}&scope=bot&permissions={}'.format(u.config['client_id'], u.config['permissions']), delete_after=10)

    @commands.command(name=',status', aliases=[',presence', ',game'], hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def status(self, ctx, *, game=None):
        if game is not None:
            await self.bot.change_presence(game=d.Game(name=game))
            u.config['playing'] = game
            u.dump(u.config, 'config.json', json=True)
        else:
            await self.bot.change_presence(game=None)
            u.config['playing'] = 'None'
            u.dump(u.config, 'config.json', json=True)

        await ctx.message.add_reaction('✅')


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
        output = m.content[9:-3]
        if len(re.findall('\n', output)) <= 20:
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
            if msg.content.startswith('exe') and msg.author is ctx.author and msg.channel is ctx.channel:
                results.cancel()
                return True
            return False

        def evaluate(msg):
            if msg.content.startswith('eval') and msg.author is ctx.author and msg.channel is ctx.channel:
                results.cancel()
                return True
            return False

        def exit(reaction, user):
            if reaction.emoji == '↩️' and user is ctx.author and reaction.message.id == ctx.message.id:
                results.cancel()
                raise exc.Abort
            return False

        try:
            console = await self.generate(ctx)
            exception = await self.generate_err(ctx)

            await ctx.message.add_reaction('↩️')

            while not self.bot.is_closed():
                try:
                    results = await asyncio.gather([self.bot.wait_for('message', check=execute), self.bot.wait_for('message', check=evaluate), self.bot.wait_for('reaction_add', check=exit)], return_exceptions=True)
                    print(results)
                except exc.Execute:
                    try:
                        sys.stdout = io.StringIO()
                        sys.stderr = io.StringIO()
                        exec(exe.content)

                    except Exception:
                        await self.refresh_err(exception, tb.format_exc(limit=1))

                    finally:
                        await self.refresh(console, exe.content, sys.stdout.getvalue() if sys.stdout.getvalue() != console.content else None)
                        sys.stdout = sys.__stdout__
                        sys.stderr = sys.__stderr__

                except exc.Evaluate:
                    try:
                        sys.stdout = io.StringIO()
                        sys.stderr = io.StringIO()
                        eval(exe.content)

                    except Exception:
                        await self.refresh_err(exception, tb.format_exc(limit=1))

                    finally:
                        await self.refresh(console, exe.content, sys.stdout.getvalue() if sys.stdout.getvalue() != console.content else None)
                        sys.stdout = sys.__stdout__
                        sys.stderr = sys.__stderr__

                finally:
                    with suppress(d.NotFound):
                        await exe.delete()

        except exc.Abort:
            pass

        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            print('Reset sys output.')

            await ctx.message.add_reaction('✅')

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
        finally:
            sys.stdout = sys.__stdout__
            print('Reset stdout.')
            await ctx.message.add_reaction('✅')

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

    # @commands.command(name='endpoint', aliases=['end'])
    # async def get_endpoint(self, ctx, *args):
    #     await ctx.send(f'```\n{await u.fetch(f"https://{args[0]}/{args[1]}/{args[2]}", params={args[3]: args[4], "limit": 1}, json=True)}```')
