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
        self.RATE_LIMIT = u.RATE_LIMIT
        self.queue = asyncio.Queue()
        self.deleting = False

        if u.tasks['auto_del']:
            for channel in u.tasks['auto_del']:
                temp = self.bot.get_channel(channel)
                self.bot.loop.create_task(self.queue_for_deletion(temp))
                print('AUTO-DELETING : #{}'.format(temp.id))
            self.bot.loop.create_task(self.delete())
            self.deleting = True

    @commands.command(name=',prunefromguild', aliases=[',pfg', ',prunefromserver', ',pfs'], brief='Prune a user\'s messages from the guild', description='about flag centers on message 50 of 101 messages\n\npfg \{user id\} [before|after|about] [\{message id\}]\n\nExample:\npfg \{user id\} before \{message id\}')
    @commands.is_owner()
    @checks.del_ctx()
    async def prune_all_user(self, ctx, user, when=None, reference=None):
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
            pru_sent = await ctx.send('⌛️ **Pruning** <@{}>**\'s messages will take some time**'.format(user))
            ch_sent = await ctx.send('🗄 **Caching channels...**')

            if when is None:
                for channel in channels:
                    async for message in channel.history(limit=None):
                        if message.author.id == int(user):
                            history.append(message)
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(self.RATE_LIMIT)
            elif when == 'before':
                for channel in channels:
                    async for message in channel.history(limit=None, before=ref.created_at):
                        if message.author.id == int(user):
                            history.append(message)
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(self.RATE_LIMIT)
            elif when == 'after':
                for channel in channels:
                    async for message in channel.history(limit=None, after=ref.created_at):
                        if message.author.id == int(user):
                            history.append(message)
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(self.RATE_LIMIT)
            elif when == 'about':
                for channel in channels:
                    async for message in channel.history(limit=None, about=ref.created_at):
                        if message.author.id == int(user):
                            history.append(message)
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(self.RATE_LIMIT)

            est_sent = await ctx.send('⏱ **Estimated time to delete history:** `{}m {}s`'.format(int(self.RATE_LIMIT * len(history) / 60), int(self.RATE_LIMIT * len(history) % 60)))
            cont_sent = await ctx.send('{} **Continue?** `Y` or `N`'.format(ctx.author.mention))
            await self.bot.wait_for('message', check=yes, timeout=10 * 60)
            await cont_sent.delete()
            del_sent = await ctx.send('🗑 **Deleting messages..**')
            await del_sent.pin()
            c = 0
            for message in history:
                with suppress(err.NotFound):
                    await message.delete()
                    c += 1
                await del_sent.edit(content='🗑 **Deleted** `{}/{}` **messages**'.format(history.index(message) + 1, len(history)))
                await asyncio.sleep(self.RATE_LIMIT)
            await del_sent.unpin()

            await ctx.send('🗑 `{}` **of** <@{}>**\'s messages left in** {}****'.format(len(history) - c, user, ctx.guild.name))
            await ctx.message.add_reaction('✅')

        except exc.CheckFail:
            await ctx.send('**Deletion aborted**', delete_after=10)
            await ctx.message.add_reaction('❌')

        except TimeoutError:
            await ctx.send('**Deletion timed out**', delete_after=10)
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
            print('STOPPED : deleting #{}'.format(channel.id))
            await channel.send('**Stopped queueing messages for deletion in** {}'.format(channel.mention), delete_after=5)

    @commands.command(name='autodelete', aliases=['autodel'])
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
                print('AUTO-DELETING : #{}'.format(ctx.channel.id))
                await ctx.send('**Auto-deleting all messages in {}**'.format(ctx.channel.mention), delete_after=5)
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

    @commands.command(name='setprefix', aliases=['setpre', 'spre'])
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx, prefix=None):
        if prefix is not None:
            u.settings['prefixes'][ctx.guild.id] = prefix
        else:
            with suppress(KeyError):
                del u.settings['prefixes'][ctx.guild.id]

        await ctx.send(f'**Prefix set to:** `{"` or `".join(prefix if ctx.guild.id in u.settings["prefixes"] else u.config["prefix"])}`')
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    # @commands.group(aliases=['rep', 'r'])
    # async def report(self, ctx, user: d.User):
    #     if not ctx.kwargs.get('user', None):
    #         await ctx.send('User required', delete_after=10)
    #         await ctx.message.add_reaction('\N{CROSS MARK}')

    @commands.command(aliases=['rep'])
    async def report(self, ctx, *, user: d.User):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and user.id == ctx.author.id:
                raise exc.Abort
            elif reaction.emoji == '\N{CROSS MARK}' and user.id == ctx.author.id:
                raise exc.Wrong
            elif reaction.emoji == '\N{SQUARED OK}' and user.id == ctx.author.id:
                return True
            return False

        def on_message(msg):
            if msg.content.lower() == 'done' and msg.author.id == ctx.author.id:
                raise exc.Abort
            elif msg.author.id == ctx.author.id:
                return True
            return False

        time = dt.utcnow()

        try:
            confirm = await ctx.send(f'@{user.name}#{user.discriminator} **has been found.**\nClick \N{SQUARED OK} to confirm or \N{CROSS MARK} to enter a user ID instead')
            for emoji in ('\N{OCTAGONAL SIGN}', '\N{CROSS MARK}', '\N{SQUARED OK}'):
                await confirm.add_reaction(emoji)
            try:
                await self.bot.wait_for('reaction_add', check=on_reaction, timeout=5 * 60)

            except exc.Wrong:
                await confirm.edit(content='Please enter the user ID')
                # message = await self.bot.wait_for('message', check=lambda msg: return msg.content.isdigit() and msg.author.id == ctx.author.id)
                user = await self.bot.get_user_info(message.content)
                await confirm.edit(content=f'@{user.name}#{user.discriminator} **has been found.**\nClick \N{SQUARED OK} to confirm')
                await asyncio.wait([self.bot.wait_for('reaction_add', check=on_reaction, timeout=5 * 60), self.bot.wait_for('reaction_remove', check=on_reaction, timeout=5 * 60)], asyncio.FIRST_COMPLETED)

            urls = set()
            for match in re.finditer('(https?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', ctx.message.content):
                urls.add(match.group(0))
            for attachment in ctx.message.attachments:
                urls.add(attachment.url)

            temport = {time: {'reason': reason, 'proof': urls, 'aliases': set()}}
            # temport = u.info['reports'].setdefault(user.id, {dt.utcnow(): {'report': reason, 'proof': urls}})
            embed = d.Embed(author=user.name, color=ctx.me.color if isinstance(
                ctx.channel, d.TextChannel) else u.color)

            confirm = await ctx.send('**The following will be added to the report database.** This will be available across servers.\nClick \N{SQUARED OK} to confirm or \N{NEGATIVE SQUARED LATIN CAPITAL LETTER A} to add username aliases')
            await ctx.send(embed=embed)
            for emoji in ('\N{OCTAGONAL SIGN}', '\N{NEGATIVE SQUARED LATIN CAPITAL LETTER A}', '\N{SQUARED OK}'):
                await confirm.add_reaction(emoji)
            await asyncio.sleep(1)
            try:
                reaction = await self.bot.wait_for('reaction_add', check=on_reaction)

            except exc.Add:
                aliases = ctx.send('Type single usernames at a time')
                try:
                    while not self.bot.is_closed:
                        message = await self.bot.wait_for('message', check=on_message)
                        temport[time]['aliases'].add(message.content)
                except exc.Abort:
                    pass

        except exc.Abort:
            await confirm.edit(content='Report cancelled', delete_after=10)

    @commands.command(name='remove', aliases=['rm'])
    async def _report_remove(self, ctx, user: d.User):
        pass
