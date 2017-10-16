import asyncio
import traceback as tb
from contextlib import suppress

import discord as d
from discord import errors as err
from discord.ext import commands

from misc import exceptions as exc
from misc import checks
from utils import utils as u


class Administration:

    def __init__(self, bot):
        self.bot = bot
        self.RATE_LIMIT = 2.1
        self.queue = asyncio.Queue()
        self.deleting = False

        if u.tasks['auto_del']:
            for channel in u.tasks['auto_del']:
                temp = self.bot.get_channel(channel)
                self.bot.loop.create_task(self.queue_for_deletion(temp))
                print('AUTO-DELETING : #{}'.format(temp.name))
            self.bot.loop.create_task(self.delete())
            self.deleting = True

    @commands.command(name=',prunefromguild', aliases=[',pfg', ',prunefromserver', ',pfs'], brief='Prune a user\'s messages from the guild', description='about flag centers on message 50 of 101 messages\n\npfg \{user id\} [before|after|about] [\{message id\}]\n\nExample:\npfg \{user id\} before \{message id\}')
    @commands.is_owner()
    @checks.del_ctx()
    async def prune_all_user(self, ctx, uid, when=None, reference=None):
        def yes(msg):
            if msg.content.lower() == 'y' and msg.channel is ctx.channel and msg.author is ctx.author:
                return True
            elif msg.content.lower() == 'n' and msg.channel is ctx.channel and msg.author is ctx.author:
                raise exc.CheckFail
            else:
                return False

        channels = ctx.guild.text_channels
        if reference is not None:
            for channel in channels:
                try:
                    ref = await channel.get_message(reference)

                except err.NotFound:
                    continue

        history = []
        try:
            pru_sent = await ctx.send('⏳ **Pruning** <@{}>**\'s messages will take some time.**'.format(uid))
            ch_sent = await ctx.send('🗄 **Caching channels...**')

            if when is None:
                for channel in channels:
                    history.extend(await channel.history(limit=None).flatten())
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels.**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(self.RATE_LIMIT)
            elif when == 'before':
                for channel in channels:
                    history.extend(await channel.history(limit=None, before=ref.created_at).flatten())
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels.**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(self.RATE_LIMIT)
            elif when == 'after':
                for channel in channels:
                    history.extend(await channel.history(limit=None, after=ref.created_at).flatten())
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels.**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(self.RATE_LIMIT)
            elif when == 'about':
                for channel in channels:
                    history.extend(await channel.history(limit=101, about=ref.created_at).flatten())
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels.**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(self.RATE_LIMIT)

            history = [message for message in history if message.author.id == int(uid)]
            est_sent = await ctx.send('⏱ **Estimated time to delete history:** `{}m {}s`'.format(int(self.RATE_LIMIT * len(history) / 60), int(self.RATE_LIMIT * len(history) % 60)))
            cont_sent = await ctx.send('{} **Continue?** `Y` or `N`'.format(ctx.author.mention))
            await self.bot.wait_for('message', check=yes, timeout=60)
            await cont_sent.delete()
            del_sent = await ctx.send('🗑 **Deleting messages...**')
            for message in history:
                with suppress(err.NotFound):
                    await message.delete()
                await del_sent.edit(content='🗑 **Deleted** `{}/{}` **messages.**'.format(history.index(message) + 1, len(history)))
                await asyncio.sleep(self.RATE_LIMIT)
            await del_sent.edit(content='🗑 `{}` **of** <@{}>**\'s messages deleted from** {}**.**'.format(len(history), uid, ctx.guild.name))

            await ctx.message.add_reaction('✅')

        except exc.CheckFail:
            await ctx.send('**Deletion aborted.**', delete_after=10)
            await ctx.message.add_reaction('❌')

        except TimeoutError:
            await ctx.send('**Deletion timed out.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    async def delete(self):
        while self.deleting:
            message = await self.queue.get()
            await asyncio.sleep(self.RATE_LIMIT)
            with suppress(err.NotFound):
                if not message.pinned:
                    await message.delete()

        print('STOPPED : deleting')

    async def queue_for_deletion(self, channel):
        def check(msg):
            if msg.content.lower() == 'stop' and msg.channel is channel and msg.author.guild_permissions.administrator:
                raise exc.Abort
            elif msg.channel is channel and not msg.pinned:
                return True
            return False

        try:
            async for message in channel.history(limit=None):
                if message.content.lower() == 'stop' and message.author.guild_permissions.administrator:
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
            print('STOPPED : looping #{}'.format(channel.name))
            await channel.send('**Stopped queueing messages for deletion in** {}**.**'.format(channel.mention), delete_after=5)

    @commands.command(name='autodelete', aliases=['autodel', 'ad'])
    @commands.has_permissions(administrator=True)
    @checks.del_ctx()
    async def auto_delete(self, ctx):
        try:
            if ctx.channel.id not in u.tasks['auto_del']:
                u.tasks['auto_del'].append(ctx.channel.id)
                u.dump(u.tasks, 'cogs/tasks.pkl')
                self.bot.loop.create_task(self.queue_for_deletion(ctx.channel))
                if not self.deleting:
                    self.bot.loop.create_task(self.delete())
                    self.deleting = True
                print('AUTO-DELETING : #{}'.format(ctx.channel.name))
                await ctx.send('**Auto-deleting all messages in {}.**'.format(ctx.channel.mention), delete_after=5)
                await ctx.message.add_reaction('✅')
            else:
                raise exc.Exists

        except exc.Exists:
            await ctx.send('**Already auto-deleting in {}.** Type `stop` to stop.'.format(ctx.channel.mention), delete_after=10)
            await ctx.message.add_reaction('❌')

    @commands.command(name='deletecommands', aliases=['delcmds'])
    @commands.has_permissions(administrator=True)
    async def delete_commands(self, ctx):
        if ctx.guild.id not in u.settings['del_ctx']:
            u.settings['del_ctx'].append(ctx.guild.id)
        else:
            u.settings['del_ctx'].remove(ctx.guild.id)
        u.dump(u.settings, 'settings.pkl')

        await ctx.send('**Delete command invocations:** `{}`'.format(ctx.guild.id in u.settings['del_ctx']))
        await ctx.message.add_reaction('✅')
