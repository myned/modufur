import asyncio
from datetime import datetime as dt
import json
import logging as log
import subprocess
import sys
import traceback as tb
from contextlib import suppress
from pprint import pprint
from hurry.filesize import size, alternative
from urllib.parse import urlparse

import discord as d
from discord import errors as err
from discord import utils
from discord.ext import commands as cmds
from discord.ext.commands import errors as errext

from misc import exceptions as exc
from misc import checks
from utils import utils as u

log.basicConfig(level=log.WARNING)


# class HelpFormatter(cmds.HelpFormatter):
#
#     async def format(self):
#         self._paginator = cmds.Paginator()
#
#         # we need a padding of ~80 or so
#
#         description = self.command.description if not self.is_cog() else inspect.getdoc(self.command)
#
#         if description:
#             # <description> portion
#             self._paginator.add_line(description, empty=True)
#
#         if isinstance(self.command, cmds.Command):
#             # <signature portion>
#             signature = self.get_command_signature()
#             self._paginator.add_line(signature, empty=True)
#
#             # <long doc> section
#             if self.command.help:
#                 self._paginator.add_line(self.command.help, empty=True)
#
#             # end it here if it's just a regular command
#             if not self.has_subcommands():
#                 self._paginator.close_page()
#                 return self._paginator.pages
#
#         max_width = self.max_name_size


def get_prefix(bot, message):
    with suppress(AttributeError):
        return u.settings['prefixes'].get(message.guild.id, u.config['prefix'])
    return u.config['prefix']

bot = cmds.Bot(command_prefix=get_prefix, self_bot=u.config['selfbot'], formatter=cmds.HelpFormatter(show_check_failure=True), description='Modufur - A booru bot with a side of management and automated tasking\nMade by @Myned#3985\n\nNSFW for Not Safe For Wumpus commands\n(G) for group commands\n@permission@ for required permissions\n!notice! for important information\np for prefix\n\n\{\} for mandatory argument\n[] for optional argument\n... for one or more arguments', help_attrs={'aliases': ['h']}, pm_help=None)

@bot.command(help='help', brief='brief', description='description', usage='usage', hidden=True)
async def test(ctx):
    await ctx.send('test')

# Send and print ready message to #testing and console after logon


@bot.event
async def on_ready():
    if not checks.ready:
        # d.opus.load_opus('opuslib')

        from cogs import booru, info, management, owner, tools

        for cog in (tools.Utils(bot), owner.Bot(bot), owner.Tools(bot), management.Administration(bot), info.Info(bot), booru.MsG(bot)):
            bot.add_cog(cog)
            u.cogs[type(cog).__name__] = cog
            print(f'COG : {type(cog).__name__}')

        # bot.loop.create_task(u.clear(booru.temp_urls, 30*60))

        if u.config['playing'] is not '':
            await bot.change_presence(activity=d.Game(name=u.config['playing']))

        print('\n> > > > > > > > >\nC O N N E C T E D : {}\n> > > > > > > > >\n'.format(bot.user.name))
        await bot.get_channel(u.config['info_channel']).send(f'**Started** \N{BLACK SUN WITH RAYS} `{"` or `".join(u.config["prefix"])}`')
        # u.notify('C O N N E C T E D')

        if u.temp['startup']:
            with suppress(err.NotFound):
                if u.temp['startup'][0] == 'guild':
                    dest = bot.get_channel(u.temp['startup'][1])
                else:
                    dest = bot.get_user(u.temp['startup'][1])
                message = await dest.get_message(u.temp['startup'][2])

                await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

            u.temp['startup'] = ()
            u.dump(u.temp, 'temp/temp.pkl')

        checks.ready = True
    else:
        print('\n- - - -\nI N F O : reconnected, reinitializing tasks\n- - - -\n')

        if u.tasks['auto_del']:
            for channel in u.tasks['auto_del']:
                temp = bot.get_channel(channel)
                bot.loop.create_task(u.cogs['Administration'].queue_for_deletion(temp))
                print('RESTARTED : auto-deleting in #{}'.format(temp.name))
            u.cogs['Administration'].deleting = True
            bot.loop.create_task(u.cogs['Administration'].delete())

        if u.config['playing'] is not '':
            await bot.change_presence(game=d.Game(name=u.config['playing']))

        print('\nS U C C E S S\n')


@bot.event
async def on_message(message):
    if not u.config['selfbot']:
        if message.author is not bot.user and not message.author.bot:
            await bot.process_commands(message)
    else:
        if not message.author.bot:
            await bot.process_commands(message)


@bot.event
async def on_error(error, *args, **kwargs):
    print('\n! ! ! ! !\nE R R O R : {}\n! ! ! ! !\n'.format(error), file=sys.stderr)
    tb.print_exc()
    await bot.get_user(u.config['owner_id']).send('**ERROR** \N{WARNING SIGN}\n```\n{}```'.format(error))
    await bot.get_channel(u.config['info_channel']).send('**ERROR** \N{WARNING SIGN}\n```\n{}```'.format(error))

    if u.temp['startup']:
        with suppress(err.NotFound):
            if u.temp['startup'][0] == 'guild':
                dest = bot.get_channel(u.temp['startup'][1])
            else:
                dest = bot.get_user(u.temp['startup'][1])
            message = await dest.get_message(u.temp['startup'][2])

            await message.add_reaction('\N{WARNING SIGN}')

        u.temp.clear()
        u.dump(u.temp, 'temp/temp.pkl')
    # u.notify('E R R O R')
    await bot.logout()


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, err.NotFound):
        print('NOT FOUND')
    elif isinstance(error, errext.MissingRequiredArgument):
        await ctx.send('**Missing required argument**', delete_after=7)
        await ctx.message.add_reaction('\N{CROSS MARK}')
    elif isinstance(error, errext.BadArgument):
        await ctx.send(f'**Invalid argument.** {error}', delete_after=7)
        await ctx.message.add_reaction('\N{CROSS MARK}')
    elif isinstance(error, errext.CheckFailure):
        await ctx.send('**Insufficient permissions**', delete_after=7)
        await ctx.message.add_reaction('\N{NO ENTRY}')
    elif isinstance(error, errext.CommandNotFound):
        print('INVALID COMMAND : {}'.format(error), file=sys.stderr)
        await ctx.message.add_reaction('\N{BLACK QUESTION MARK ORNAMENT}')
    else:
        print('\n! ! ! ! ! ! !  ! ! ! ! !\nC O M M A N D  E R R O R : {}\n! ! ! ! ! ! !  ! ! ! ! !\n'.format(
            error), file=sys.stderr)
        tb.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await bot.get_user(u.config['owner_id']).send('**COMMAND ERROR** \N{WARNING SIGN} `{}` from {} in {}\n```\n{}```'.format(ctx.message.content, ctx.author.mention, ctx.channel.mention if ctx.channel is d.channel.TextChannel else 'DMs', error))
        await bot.get_channel(u.config['info_channel']).send('**COMMAND ERROR** \N{WARNING SIGN} `{}` from {} in {}\n```\n{}```'.format(ctx.message.content, ctx.author.mention, ctx.channel.mention if ctx.channel is d.channel.TextChannel else 'DMs', error))
        await exc.send_error(ctx, error)
        await ctx.message.add_reaction('\N{WARNING SIGN}')
        # u.notify('C O M M A N D  E R R O R')

# @bot.event
# async def on_command(ctx):
#     if ctx.guild.id in u.settings['del_resp']:
#         pass

@bot.event
async def on_command_completion(ctx):
    with suppress(err.NotFound):
        with suppress(AttributeError):
            if ctx.guild.id in u.settings['del_ctx'] and ctx.me.permissions_in(ctx.channel).manage_messages and isinstance(ctx.message.channel, d.TextChannel):
                await ctx.message.delete()

        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    for command in ('lastcommand', ',restart', ',die'):
        if ctx.command.name == command:
            return

    u.last_commands[ctx.author.id] = ctx

@bot.event
async def on_guild_remove(guild):
    print(f'LEFT : {guild.name}')

    for task, idents in u.tasks.items():
        for channel in guild.channels:
            if channel.id in idents:
                idents.remove(channel.id)
                print(f'STOPPED : {task} in #{channel.id}')
    u.dump(u.tasks, 'cogs/tasks.pkl')


async def wait(voice):
    asyncio.sleep(5)
    await voice.disconnect()


def after(voice, error):
    coro = voice.disconnect()
    future = asyncio.run_coroutine_threadsafe(coro, voice.loop)
    future.result()

# suggested = u.setdefault('cogs/suggested.pkl', {'last_update': 'None', 'tags': {}, 'total': 0})
@bot.command(name=',test', hidden=True)
@cmds.is_owner()
async def test(ctx):
    post = await u.fetch('https://e621.net/post/show.json?id=1145042', json=True)

    tags = []
    if post['tags']:
        temptags = post['tags'].split(' ')
        cis = []
        for tag in suggested:
            pass
        for tag in temptags:
            tags.append(f'[{tag}](https://e621.net/post?tags={tag})')
        # tags = ' '.join(tags)
    else:
        tags = 'None'

    if post['description']:
        post_description = post['description'] if len(post['description']) < 200 else f'{post["description"][:200]}...'
    else:
        post_description = 'None'

    title = ', '.join(post['artist'])
    description = f'posted by: *[{post["author"]}](https://e621.net/post?tags=user:{post["author"]})*'
    url = f'https://e621.net/post?tags={",".join(post["artist"])}'
    # timestamp = dt.utcnow()
    color = ctx.me.color
    footer = {'text': post['score'], 'icon_url': 'https://images-ext-1.discordapp.net/external/W2k0ZzhU7ngvN_-CdqAa3H3FmkfCNYQTxPG_DsvacB4/https/emojipedia-us.s3.amazonaws.com/thumbs/320/twitter/103/sparkles_2728.png'}
    # image = 'https://e621.net/post/show/54360'
    thumbnail = post['file_url']
    author = {'name': post['id'], 'url': f'https://e621.net/post/show/{post["id"]}', 'icon_url': ctx.author.avatar_url}

    fields = []
    names = ('File', 'Sources', 'Description', 'tags', 'tags (ext.)')
    values = (f'[{post["md5"]}]({post["file_url"]}) | [{post["file_ext"]}](https://e621.net/post?tags=type:{post["file_ext"]})\n\n**Size** [{size(post["file_size"], system=alternative)}](https://e621.net/post?tags=filesize:{post["file_size"]})\n**Resolution** [{post["width"]} x {post["height"]}](https://e621.net/post?tags=width:{post["width"]},height:{post["height"]}) | [{u.get_aspectratio(post["width"], post["height"])}](https://e621.net/post?tags=ratio:{post["width"]/post["height"]:.2f})', '\n'.join([f'[{urlparse(source).netloc}]({source})' for source in post['sources']]), post_description, ' '.join(tags[:20]), ' '.join(tags[20:]))
    inlines = (False, False, False, True, True)
    for name, value, inline in zip(names, values, inlines):
        fields.append({'name': name, 'value': value, 'inline': inline})

    embed = u.generate_embed(ctx, title=title, description=description, url=url, colour=color, footer=footer, thumbnail=thumbnail, author=author, fields=fields)

    await ctx.send(embed=embed)
    # print(ctx.args)
    # print(ctx.kwargs)
    # if '<:N_:368917475531816962>' in message:
    #     await ctx.send('<:N_:368917475531816962>')
    # logs = []
    # async for entry in ctx.guild.audit_logs(limit=None, action=d.AuditLogAction.message_delete):
    #     logs.append(
    #         f'@{entry.user.name} deleted {entry.extra.count} messages from @{entry.target.name} in #{entry.extra.channel.name}')
    # pprint(logs)
    # channel = bot.get_channel(int(cid))
    # voice = await channel.connect()
    # voice.play(d.AudioSource, after=lambda: after(voice))

bot.run(u.config['token'], bot=not u.config['selfbot'])
