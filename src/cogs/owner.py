import asyncio
import code
import io
import os
import re
import sys
import traceback as tb
from contextlib import redirect_stdout, suppress

import discord as d
import pyrasite as pyr
from discord.ext import commands as cmds

from misc import exceptions as exc
from misc import checks
from utils import utils as u


class Bot:

    def __init__(self, bot):
        self.bot = bot

    # Close connection to Discord - immediate offline
    @cmds.command(name=',die', aliases=[',d'], brief='Kills the bot', description='BOT OWNER ONLY\nCloses the connection to Discord', hidden=True)
    @cmds.is_owner()
    async def die(self, ctx):
        await ctx.message.add_reaction('\N{CRESCENT MOON}')

        await self.bot.get_channel(u.config['info_channel']).send('**Shutting down** \N{CRESCENT MOON} . . .')

        chantype = 'guild' if isinstance(ctx.channel, d.TextChannel) else 'private'
        u.temp['startup'] = (chantype, ctx.channel.id if chantype == 'guild' else ctx.author.id, ctx.message.id)
        u.dump(u.temp, 'temp/temp.pkl')

        # loop = self.bot.loop.all_tasks()
        # for task in loop:
        #     task.cancel()
        await self.bot.logout()
        u.close(self.bot.loop)
        print('\n< < < < < < < < < < < <\nD I S C O N N E C T E D\n< < < < < < < < < < < <\n')
        # u.notify('D I S C O N N E C T E D')

    @cmds.command(name=',restart', aliases=[',res', ',r'], hidden=True)
    @cmds.is_owner()
    async def restart(self, ctx):
        await ctx.message.add_reaction('\N{SLEEPING SYMBOL}')

        print('\n^ ^ ^ ^ ^ ^ ^ ^ ^ ^\nR E S T A R T I N G\n^ ^ ^ ^ ^ ^ ^ ^ ^ ^\n')
        await self.bot.get_channel(u.config['info_channel']).send('**Restarting** \N{SLEEPING SYMBOL} . . .')
        # u.notify('R E S T A R T I N G')

        chantype = 'guild' if isinstance(ctx.channel, d.TextChannel) else 'private'
        u.temp['startup'] = (chantype, ctx.channel.id if chantype == 'guild' else ctx.author.id, ctx.message.id)
        u.dump(u.temp, 'temp/temp.pkl')

        # loop = self.bot.loop.all_tasks()
        # for task in loop:
        #     task.cancel()
        await self.bot.logout()
        u.close(self.bot.loop)
        os.execl(sys.executable, 'python3', 'run.py')

    # Invite bot to bot owner's server
    @cmds.command(name=',invite', aliases=[',inv', ',link'], brief='Invite the bot', description='BOT OWNER ONLY\nInvite the bot to a server (Requires admin)', hidden=True)
    @cmds.is_owner()
    async def invite(self, ctx):
        await ctx.message.add_reaction('\N{ENVELOPE}')

        await ctx.send('https://discordapp.com/oauth2/authorize?&client_id={}&scope=bot&permissions={}'.format(u.config['client_id'], u.config['permissions']), delete_after=5)

    @cmds.command(name=',guilds', aliases=[',glds', ',servers', ',servs'])
    @cmds.is_owner()
    async def guilds(self, ctx):
        paginator = cmds.Paginator()

        for guild in self.bot.guilds:
            paginator.add_line(guild.name)

        for page in paginator.pages:
            await ctx.send(f'**Guilds:**\n{page}')

    @cmds.command(name=',status', aliases=[',presence', ',game'], hidden=True)
    @cmds.is_owner()
    async def change_status(self, ctx, *, game=None):
        if game:
            await self.bot.change_presence(game=d.Game(name=game))
            u.config['playing'] = game
            u.dump(u.config, 'config.json', json=True)
            await ctx.send(f'**Game changed to** `{game}`')
        else:
            await self.bot.change_presence(game=None)
            u.config['playing'] = ''
            u.dump(u.config, 'config.json', json=True)
            await ctx.send('**Game changed to** ` `')

    @cmds.command(name=',username', aliases=[',user'], hidden=True)
    @cmds.is_owner()
    async def change_username(self, ctx, *, username=None):
        if username:
            await self.bot.user.edit(username=username)
            await ctx.send(f'**Username changed to** `{username}`')
        else:
            await ctx.send('**Invalid string**', delete_after=7)
            await ctx.message.add_reaction('\N{CROSS MARK}')


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

    @cmds.command(name=',console', aliases=[',con', ',c'], hidden=True)
    @cmds.is_owner()
    async def console(self, ctx):
        def execute(msg):
            if msg.content.lower().startswith('exec ') and msg.author is ctx.author and msg.channel is ctx.channel:
                msg.content = msg.content[5:]
                return True
            return False

        def evaluate(msg):
            if msg.content.lower().startswith('eval ') and msg.author is ctx.author and msg.channel is ctx.channel:
                msg.content = msg.content[5:]
                return True
            return False

        def exit(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and user is ctx.author and reaction.message.id == ctx.message.id:
                raise exc.Abort
            return False

        try:
            console = await self.generate(ctx)
            exception = await self.generate_err(ctx)

            await ctx.message.add_reaction('\N{OCTAGONAL SIGN}')

            while not self.bot.is_closed():
                try:
                    done, pending = await asyncio.wait([self.bot.wait_for('message', check=execute), self.bot.wait_for('message', check=evaluate), self.bot.wait_for('reaction_add', check=exit)], return_when=asyncio.FIRST_COMPLETED)

                    message = done.pop().result()
                    print(message.content)

                except exc.Execute:
                    try:
                        sys.stdout = io.StringIO()
                        sys.stderr = io.StringIO()
                        exec(message.content)

                    except Exception:
                        await self.refresh_err(exception, tb.format_exc(limit=1))

                    finally:
                        await self.refresh(console, message.content, sys.stdout.getvalue() if sys.stdout.getvalue() != console.content else None)
                        sys.stdout = sys.__stdout__
                        sys.stderr = sys.__stderr__
                        with suppress(d.NotFound):
                            await message.delete()

                except exc.Evaluate:
                    try:
                        sys.stdout = io.StringIO()
                        sys.stderr = io.StringIO()
                        eval(message.content)

                    except Exception:
                        await self.refresh_err(exception, tb.format_exc(limit=1))

                    finally:
                        await self.refresh(console, message.content, sys.stdout.getvalue() if sys.stdout.getvalue() != console.content else None)
                        sys.stdout = sys.__stdout__
                        sys.stderr = sys.__stderr__
                        with suppress(d.NotFound):
                            await message.delete()

        except exc.Abort:
            pass

        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            print('RESET : sys.std output/error')

    @cmds.command(name=',execute', aliases=[',exec'], hidden=True)
    @cmds.is_owner()
    async def execute(self, ctx, *, exe):
        try:
            with io.StringIO() as buff, redirect_stdout(buff):
                exec(exe)
                await self.generate(ctx, exe, f'\n{buff.getvalue()}')

        except Exception:
            await self.generate(ctx, exe, f'\n{tb.format_exc()}')

    @cmds.command(name=',evaluate', aliases=[',eval'], hidden=True)
    @cmds.is_owner()
    async def evaluate(self, ctx, *, evl):
        try:
            with io.StringIO() as buff, redirect_stdout(buff):
                eval(evl)
                await self.generate(ctx, evl, f'\n{buff.getvalue()}')

        except Exception:
            await self.generate(ctx, evl, f'\n{tb.format_exc()}')

    @cmds.group(aliases=[',db'], hidden=True)
    @cmds.is_owner()
    async def debug(self, ctx):
        console = await self.generate(ctx)

    @debug.command(name='inject', aliases=['inj'])
    async def _inject(self, ctx, *, input_):
        pass

    @debug.command(name='inspect', aliases=['ins'])
    async def _inspect(self, ctx, *, input_):
        pass

    # @cmds.command(name='endpoint', aliases=['end'])
    # async def get_endpoint(self, ctx, *args):
    #     await ctx.send(f'```\n{await u.fetch(f"https://{args[0]}/{args[1]}/{args[2]}", params={args[3]: args[4], "limit": 1}, json=True)}```')
