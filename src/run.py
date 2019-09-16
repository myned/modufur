import asyncio
import logging as log
import sys
import traceback as tb
from contextlib import suppress

import discord as d
from discord import errors as err
from discord.ext import commands as cmds
from discord.ext.commands import errors as errext

from misc import exceptions as exc
from misc import checks
from utils import utils as u

log.basicConfig(level=log.WARNING)


def get_prefix(bot, message):
    with suppress(AttributeError):
        return u.settings['prefixes'].get(message.guild.id, u.config['prefix'])
    return u.config['prefix']


bot = cmds.Bot(
    command_prefix=get_prefix,
    self_bot=u.config['selfbot'],
    description='Modufur - A booru bot with a side of management and automated tasking'
                '\nMade by @Myned#3985',
    help_attrs={'aliases': ['h']}, pm_help=None)


@bot.event
async def on_ready():
    if not checks.ready:
        from cogs import booru, info, management, owner, tools

        for cog in (
                tools.Utils(bot),
                owner.Bot(bot),
                owner.Tools(bot),
                management.Administration(bot),
                info.Info(bot),
                booru.MsG(bot)):
            bot.add_cog(cog)
            u.cogs[type(cog).__name__] = cog
            print(f'COG : {type(cog).__name__}')

        if u.config['playing'] is not '':
            await bot.change_presence(activity=d.Game(u.config['playing']))

        print('\n> > > > > > > > >'
              f'\nC O N N E C T E D : {bot.user.name}'
              '\n> > > > > > > > >\n')

        try:
            if u.temp['startup']:
                with suppress(err.NotFound):
                    if u.temp['startup'][0] == 'guild':
                        ctx = bot.get_channel(u.temp['startup'][1])
                    else:
                        ctx = bot.get_user(u.temp['startup'][1])
                    message = await ctx.get_message(u.temp['startup'][2])

                    await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                u.temp['startup'] = ()
                u.dump(u.temp, 'temp/temp.pkl')

            checks.ready = True
        except KeyError:
            u.dump({'startup': ()}, 'temp/temp.pkl')
        except AttributeError:
            pass
    else:
        print('\n- - - -\nI N F O : reconnected, reinitializing tasks\n- - - -\n')
        reconnect = await bot.get_user(u.config['owner_id']).send('**RECONNECTING**')
        await reconnect.add_reaction('\N{SLEEPING SYMBOL}')

        if u.tasks['auto_del']:
            for channel in u.tasks['auto_del']:
                temp = bot.get_channel(channel)
                bot.loop.create_task(u.cogs['Administration'].queue_for_deletion(temp))
                print(f'RESTARTED : auto-deleting in #{temp.name}')
            u.cogs['Administration'].deleting = True
            bot.loop.create_task(u.cogs['Administration'].delete())

        if u.config['playing'] is not '':
            await bot.change_presence(activity=d.Game(u.config['playing']))

        await reconnect.add_reaction('\N{WHITE HEAVY CHECK MARK}')
        print('\nS U C C E S S\n')


@bot.event
async def on_message(message):
    if not u.config['selfbot']:
        if message.author is not bot.user and not message.author.bot and message.author.id not in u.block['user_ids']:
            await bot.process_commands(message)
    else:
        if not message.author.bot:
            await bot.process_commands(message)


@bot.event
async def on_error(error, *args, **kwargs):
    print(f'\n! ! ! ! !\nE R R O R : {sys.exc_info()[1].text}\n! ! ! ! !\n', file=sys.stderr)
    tb.print_exc()
    await bot.get_user(u.config['owner_id']).send(f'**ERROR** \N{WARNING SIGN}\n```\n{error}```')

    if u.temp['startup']:
        u.temp.clear()
        u.dump(u.temp, 'temp/temp.pkl')

    await bot.logout()


@bot.event
async def on_command_error(ctx, error):
    with suppress(err.NotFound):
        if isinstance(error, err.NotFound):
            print('NOT FOUND')
        elif isinstance(error, errext.CommandInvokeError):
            print(f'ERROR : {error}')
        elif isinstance(error, err.Forbidden):
            pass
        elif isinstance(error, errext.CommandOnCooldown):
            await u.add_reaction(ctx.message, '\N{HOURGLASS}')
            await asyncio.sleep(error.retry_after)
            await u.add_reaction(ctx.message, '\N{WHITE HEAVY CHECK MARK}')
        elif isinstance(error, errext.MissingRequiredArgument):
            await ctx.send('**Missing required argument**')
            await u.add_reaction(ctx.message, '\N{CROSS MARK}')
        elif isinstance(error, errext.BadArgument):
            await ctx.send(f'**Invalid argument.** {error}')
            await u.add_reaction(ctx.message, '\N{CROSS MARK}')
        elif isinstance(error, errext.CheckFailure):
            await ctx.send('**Insufficient permissions**')
            await u.add_reaction(ctx.message, '\N{NO ENTRY}')
        elif isinstance(error, errext.CommandNotFound):
            print(f'INVALID COMMAND : {error}', file=sys.stderr)
            await u.add_reaction(ctx.message, '\N{BLACK QUESTION MARK ORNAMENT}')
        else:
            print('\n! ! ! ! ! ! !  ! ! ! ! !'
                  f'\nC O M M A N D  E R R O R : {error}'
                  '\n! ! ! ! ! ! !  ! ! ! ! !\n', file=sys.stderr)
            tb.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
            await bot.get_user(u.config['owner_id']).send(
                '**COMMAND ERROR** \N{WARNING SIGN}'
                f'`{ctx.message.content}`'
                f'from {ctx.author.mention}'
                f'in {ctx.channel.mention if isinstance(ctx.channel, d.channel.TextChannel) else "DMs"}'
                '\n```\n'
                f'{error}```')
            await exc.send_error(ctx, error)
            await u.add_reaction(ctx.message, '\N{WARNING SIGN}')


@bot.event
async def on_command_completion(ctx):
    with suppress(err.NotFound):
        with suppress(AttributeError):
            if ctx.guild.id in u.settings['del_ctx'] and ctx.me.permissions_in(ctx.channel).manage_messages:
                await ctx.message.delete()

    u.last_commands[ctx.author.id] = ctx


@bot.event
async def on_guild_join(guild):
    if str(guild.id) in u.block['guild_ids']:
        print(f'LEAVING : {guild.name}')
        await guild.leave()
    else:
        print(f'JOINING : {guild.name}')


@bot.event
async def on_guild_remove(guild):
    print(f'LEFT : {guild.name}')

    for task, idents in u.tasks.items():
        for channel in guild.channels:
            if channel.id in idents:
                idents.remove(channel.id)
                print(f'STOPPED : {task} in #{channel.id}')
    u.dump(u.tasks, 'cogs/tasks.pkl')


@bot.command(name=',test', hidden=True)
@cmds.is_owner()
async def test(ctx):
    pass


bot.run(u.config['token'], bot=not u.config['selfbot'])
