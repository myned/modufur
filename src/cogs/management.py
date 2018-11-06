import asyncio
import traceback as tb
from contextlib import suppress
from datetime import datetime as dt

import discord as d
from discord import errors as err
from discord.ext import commands as cmds
from discord.ext.commands import errors as errext

from misc import exceptions as exc
from misc import checks
from utils import utils as u


class Administration:

    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue()
        self.deleting = False

        if u.tasks['auto_del']:
            for channel in u.tasks['auto_del']:
                temp = self.bot.get_channel(channel)
                self.bot.loop.create_task(self.queue_for_deletion(temp))
                print('STARTED : auto-deleting in #{}'.format(temp.name))
            self.deleting = True
            self.bot.loop.create_task(self.delete())

    @cmds.group(aliases=['pru', 'purge', 'pur', 'clear', 'cl'], hidden=True)
    @cmds.is_owner()
    async def prune(self, ctx):
        pass

    @prune.group(name='user', aliases=['u', 'member', 'm'])
    async def _prune_user(self, ctx):
        pass

    @_prune_user.command(name='channel', aliases=['channels', 'chans', 'chan', 'ch', 'c'])
    async def _prune_user_channel(self, ctx, user: d.User, *channels: d.TextChannel):
        def confirm(r, u):
            if u is ctx.author:
                if r.emoji == '\N{OCTAGONAL SIGN}':
                    raise exc.Abort
                if r.emoji == '\N{THUMBS UP SIGN}':
                    return True
            return False

        if not channels:
            channels = [ctx.channel]

        try:
            pruning = await ctx.send(f'\N{HOURGLASS} **Pruning** {user.mention}**\'s messages from** {"**,** ".join([channel.mention for channel in channels])} **might take some time.** Proceed, {ctx.author.mention}?')
            await pruning.add_reaction('\N{THUMBS UP SIGN}')
            await pruning.add_reaction('\N{OCTAGONAL SIGN}')
            await asyncio.sleep(1)

            await self.bot.wait_for('reaction_add', check=confirm, timeout=10 * 60)

            deleting = await ctx.send(f'\N{WASTEBASKET} **Deleting** {user.mention}**\'s messages...**')
            await asyncio.sleep(1)

            c = 0
            for channel in channels:
                await deleting.edit(content=f'\N{WASTEBASKET} **Deleting** {user.mention}**\'s messages from** {channel.mention}')

                deleted = await channel.purge(check=lambda m: m.author.id == user.id, before=pruning, limit=None)
                c += len(deleted)

            await asyncio.sleep(1)

            for channel in channels:
                missed = 0
                async for message in channel.history(before=pruning, limit=None):
                    if message.author.id == user.id:
                        missed += 1

                if missed > 0:
                    await ctx.send(f'\N{DOUBLE EXCLAMATION MARK} `{missed}` **messages were not deleted in** {channel.mention}')

            await ctx.send(f'\N{WHITE HEAVY CHECK MARK} **Finished deleting** `{c}` **of** {user.mention}**\'s messages**')

        except exc.Abort:
            await ctx.send('**Deletion aborted**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except TimeoutError:
            await ctx.send('**Deletion timed out**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_prune_user.command(name='all', aliases=['a'], brief='Prune a user\'s messages from the guild', description='about flag centers on message 50 of 101 messages\n\npfg \{user id\} [before|after|about] [\{message id\}]\n\nExample:\npfg \{user id\} before \{message id\}', hidden=True)
    @cmds.is_owner()
    async def _prune_user_all(self, ctx, user: d.User):
        def confirm(r, u):
            if u is ctx.author:
                if r.emoji == '\N{OCTAGONAL SIGN}':
                    raise exc.Abort
                if r.emoji == '\N{THUMBS UP SIGN}':
                    return True
            return False

        try:
            pruning = await ctx.send(f'\N{HOURGLASS} **Pruning** {user.mention}**\'s messages might take some time.** Proceed, {ctx.author.mention}?')
            await pruning.add_reaction('\N{THUMBS UP SIGN}')
            await pruning.add_reaction('\N{OCTAGONAL SIGN}')
            await asyncio.sleep(1)

            await self.bot.wait_for('reaction_add', check=confirm, timeout=10 * 60)

            deleting = await ctx.send(f'\N{WASTEBASKET} **Deleting** {user.mention}**\'s messages...**')
            await asyncio.sleep(1)

            c = 0
            for channel in ctx.guild.text_channels:
                await deleting.edit(content=f'\N{WASTEBASKET} **Deleting** {user.mention}**\'s messages from** {channel.mention}')

                deleted = await channel.purge(check=lambda m: m.author.id == user.id, before=pruning, limit=None)
                c += len(deleted)

            await asyncio.sleep(1)

            for channel in ctx.guild.text_channels:
                missed = 0
                async for message in channel.history(before=pruning, limit=None):
                    if message.author.id == user.id:
                        missed += 1

                if missed > 0:
                    await ctx.send(f'\N{DOUBLE EXCLAMATION MARK} `{missed}` **messages were not deleted in** {channel.mention}')

            await ctx.send(f'\N{WHITE HEAVY CHECK MARK} **Finished deleting** `{c}` **of** {user.mention}**\'s messages**')

        except exc.Abort:
            await ctx.send('**Deletion aborted**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except TimeoutError:
            await ctx.send('**Deletion timed out**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @cmds.group(aliases=['task', 'tsk'])
    async def tasks(self):
        pass

    async def delete(self):
        while self.deleting:
            message = await self.queue.get()
            with suppress(err.NotFound):
                if not message.pinned:
                    await message.delete()

        print('STOPPED : deleting')

    async def queue_for_deletion(self, channel):
        def check(msg):
            if 'stop d' in msg.content.lower() and msg.channel is channel and msg.author.guild_permissions.administrator:
                raise exc.Abort
            elif msg.channel is channel and not msg.pinned:
                return True
            return False

        try:
            async for message in channel.history(limit=None):
                if 'stop d' in message.content.lower() and message.author.guild_permissions.administrator:
                    raise exc.Abort
                if not message.pinned:
                    await self.queue.put(message)

            while not self.bot.is_closed():
                message = await self.bot.wait_for('message', check=check)
                await self.queue.put(message)

        except exc.Abort:
            u.tasks['auto_del'].remove(channel.id)
            u.dump(u.tasks, 'cogs/tasks.pkl')
            if not u.tasks['auto_del']:
                self.deleting = False
            print('STOPPED : deleting #{}'.format(channel.name))
            await channel.send('**Stopped queueing messages for deletion in** {}'.format(channel.mention))

    @cmds.command(name='autodelete', aliases=['autodel'])
    @cmds.has_permissions(administrator=True)
    async def auto_delete(self, ctx):
        try:
            if ctx.channel.id not in u.tasks['auto_del']:
                u.tasks['auto_del'].append(ctx.channel.id)
                u.dump(u.tasks, 'cogs/tasks.pkl')
                self.bot.loop.create_task(self.queue_for_deletion(ctx.channel))
                if not self.deleting:
                    self.bot.loop.create_task(self.delete())
                    self.deleting = True
                print('STARTED : auto-deleting in #{}'.format(ctx.channel.name))
                await ctx.send('**Auto-deleting all messages in {}**'.format(ctx.channel.mention))
            else:
                raise exc.Exists

        except exc.Exists:
            await ctx.send('**Already auto-deleting in {}.** Type `stop d(eleting)` to stop.'.format(ctx.channel.mention))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @cmds.group(aliases=['setting', 'set', 's'])
    @cmds.has_permissions(administrator=True)
    async def settings(self, ctx):
        pass

    @settings.command(name='deletecommands', aliases=['delcmds', 'delcmd'])
    async def _settings_deletecommands(self, ctx):
        if ctx.guild.id not in u.settings['del_ctx']:
            u.settings['del_ctx'].append(ctx.guild.id)
        else:
            u.settings['del_ctx'].remove(ctx.guild.id)
        u.dump(u.settings, 'settings.pkl')

        await ctx.send('**Delete command invocations:** `{}`'.format(ctx.guild.id in u.settings['del_ctx']))

    @settings.command(name='prefix', aliases=['pre', 'p'])
    async def _settings_prefix(self, ctx, *prefixes):
        if prefixes:
            u.settings['prefixes'][ctx.guild.id] = prefixes
        else:
            with suppress(KeyError):
                del u.settings['prefixes'][ctx.guild.id]

        await ctx.send(f'**Prefix set to:** `{"` or `".join(prefixes if ctx.guild.id in u.settings["prefixes"] else u.config["prefix"])}`')

    @settings.command(name='deleteresponses', aliases=['delresps', 'delresp'])
    async def _settings_deleteresponses(self, ctx):
        if ctx.guild.id not in u.settings['del_resp']:
            u.settings['del_resp'].append(ctx.guild.id)
        else:
            u.settings['del_resp'].remove(ctx.guild.id)
        u.dump(u.settings, 'settings.pkl')

        await ctx.send(f'**Delete command responses:** `{ctx.guild.id in u.settings["del_resp"]}`')
