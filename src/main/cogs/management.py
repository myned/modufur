import asyncio
import discord as d
import traceback
from discord.ext import commands
from misc import checks
from misc import exceptions as exc
from utils import utils as u

RATE_LIMIT = 2.1

class Administration:

    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue()

        if u.background.get('management', {}):
            if u.background['management'].get('auto_delete', {}):
                for channel in u.background['management']['auto_delete']:
                    temp = self.bot.get_channel(channel)
                    self.bot.loop.create_task(self.on_message(temp))
                    self.bot.loop.create_task(self.delete())
                    print('Looping {}'.format(temp.id))

    # @commands.group(aliases=['pr', 'clear', 'cl'])
    # @commands.is_owner()
    # @checks.del_ctx()
    # async def prune(self, ctx):
    #     pass
    #
    # @prune.group(name='all', aliases=['a'])
    # async def _all(self, ctx):
    #     pass
    # @_all.group(name='user')
    # async def __user(self, ctx, user: d.Member):
    #     channels = ctx.message.guild.text_channels
    #     bulk_history = {}
    #     bulk = {}
    #     history = []
    #     c = 0
    #     if ctx.invoked_subcommand is None:
    #         for channel in channels:
    #             bulk_history[channel] = await channel.history(limit=None, after=dt.datetime.utcnow() - dt.timedelta(days=14)).flatten()
    #             await ch_sent.edit(content='🗄 **Cached** `' + str(channels.index(channel) + 1) + '/' + str(len(channels)) + '` **channels.**')
    #             await asyncio.sleep(RATE_LIMIT)
    #         for channel, messages in bulk_history.items():
    #             bulk[channel] = [message for message in messages if message.author.id == int(uid)]
    #         for channel, messages in bulk_history.items():
    #             bulk[channel] = [bulk[channel][i:i+100] for i in range(0, len(bulk[channel]), 100)]
    #         await ctx.send('⏱ **Estimated time to delete `bulk-history`:** `' + str(int(RATE_LIMIT * sum([len(v) for v in bulk.values()]) / 60)) + ' mins ' + str(int(RATE_LIMIT * sum([len(v) for v in bulk.values()]) % 60)) + ' secs`')
    #         check = await ctx.send(ctx.author.mention + ' **Continue?** `Y` or `N`')
    #         await self.bot.wait_for('message', check=yes, timeout=60)
    #         del_sent = await ctx.send('🗑 **Deleting messages...**')
    #         for channel, messages in bulk.items():
    #             for chunk in messages:
    #                 c += len(chunk)
    #                 await channel.delete_messages(chunk)
    #                 await del_sent.edit(content='🗑 **Deleted** `' + str(c) + '/' + str(sum([len(v) for v in bulk.values()])) + '` **messages.**')
    #                 await asyncio.sleep(5)
    #         await ctx.send('✅ `' + str(sum([len(v) for v in bulk.values()])) + '` **of** <@' + uid + '>**\'s messages deleted from** ' + ctx.message.guild.name + '**.**')
    #         for channel in channels:
    #             history.extend(await channel.history(limit=None, before=dt.datetime.utcnow() - dt.timedelta(days=14)).flatten())
    #             await ch_sent.edit(content='🗄 **Cached** `' + str(channels.index(channel) + 1) + '/' + str(len(channels)) + '` **channels.**')
    #             await asyncio.sleep(RATE_LIMIT)

    @commands.command(name=',prunefromguild', aliases=[',pfg', ',prunefromserver', ',pfs'], brief='Prune a user\'s messages from the guild', description='about flag centers on message 50 of 101 messages\n\npfg \{user id\} [before|after|about] [\{message id\}]\n\nExample:\npfg \{user id\} before \{message id\}')
    @commands.is_owner()
    @checks.del_ctx()
    async def prune_all_user(self, ctx, uid, when=None, reference=None):
        global RATE_LIMIT

        def yes(msg):
            if msg.content.lower() == 'y' and msg.channel is ctx.message.channel and msg.author is ctx.message.author:
                return True
            elif msg.content.lower() == 'n' and msg.channel is ctx.message.channel and msg.author is ctx.message.author:
                raise exc.CheckFail
            else:
                return False

        channels = ctx.message.guild.text_channels
        if reference is not None:
            for channel in channels:
                try:
                    ref = await channel.get_message(reference)
                except d.errors.NotFound:
                    continue
        history = []
        try:
            pru_sent = await ctx.send('⌛️ **Pruning** <@{}>**\'s messages will take some time.**'.format(uid))
            ch_sent = await ctx.send('🗄 **Caching channels...**')

            if when is None:
                for channel in channels:
                    history.extend(await channel.history(limit=None).flatten())
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels.**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(RATE_LIMIT)
            elif when =='before':
                for channel in channels:
                    history.extend(await channel.history(limit=None, before=ref.created_at).flatten())
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels.**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(RATE_LIMIT)
            elif when == 'after':
                for channel in channels:
                    history.extend(await channel.history(limit=None, after=ref.created_at).flatten())
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels.**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(RATE_LIMIT)
            elif when == 'about':
                for channel in channels:
                    history.extend(await channel.history(limit=101, about=ref.created_at).flatten())
                    await ch_sent.edit(content='🗄 **Cached** `{}/{}` **channels.**'.format(channels.index(channel) + 1, len(channels)))
                    await asyncio.sleep(RATE_LIMIT)

            history = [message for message in history if message.author.id == int(uid)]
            est_sent = await ctx.send('⏱ **Estimated time to delete history:** `{}m {}s`'.format(int(RATE_LIMIT * len(history) / 60), int(RATE_LIMIT * len(history) % 60)))
            cont_sent = await ctx.send('{} **Continue?** `Y` or `N`'.format(ctx.author.mention))
            await self.bot.wait_for('message', check=yes, timeout=60)
            await cont_sent.delete()
            del_sent = await ctx.send('🗑 **Deleting messages...**')
            for message in history:
                try: await message.delete()
                except d.NotFound: pass
                # print('Deleted {}/{} messages.'.format(history.index(message) + 1, len(history)))
                await del_sent.edit(content='🗑 **Deleted** `{}/{}` **messages.**'.format(history.index(message) + 1, len(history)))
                await asyncio.sleep(RATE_LIMIT)
            await del_sent.edit(content='🗑 `{}` **of** <@{}>**\'s messages deleted from** {}**.**'.format(len(history), uid, ctx.message.guild.name))
        except exc.CheckFail:
            await ctx.send('❌ **Deletion aborted.**', delete_after=10)
        except TimeoutError:
            await ctx.send('❌ **Deletion timed out.**', delete_after=10)
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, traceback.format_exc(limit=1)))
            traceback.print_exc()

    async def delete(self):
        while True:
            message = await self.queue.get()
            await asyncio.sleep(RATE_LIMIT)
            try: await message.delete()
            except d.errors.NotFound: pass

    async def on_message(self, channel):
        def check(msg):
            if msg.content == 'stop' and msg.channel is channel and msg.author.guild_permissions.administrator:
                raise exc.Abort
            elif msg.channel is channel and not msg.pinned:
                return True
            else:
                return False

        try:
            while True:
                message = await self.bot.wait_for('message', check=check)
                await self.queue.put(message)
        except exc.Abort:
            u.background['management']['auto_delete'].remove(channel.id)
            u.update(u.background, 'background.json')
            print('Stopped looping {}'.format(channel.id))
            await channel.send('✅ **Stopped deleting messages in** {}**.**'.format(channel.mention), delete_after=5)
        except AttributeError:
            pass
        except Exception:
            await channel.send(exc.base + '\n```' + traceback.format_exc(limit=1) + '```')
            traceback.print_exc()

    @commands.command(name='autodelete', aliases=['autodel', 'ad'])
    @commands.has_permissions(administrator=True)
    @checks.del_ctx()
    async def auto_delete(self, ctx):
        channel = ctx.message.channel

        try:
            if channel.id not in u.background['management']['auto_delete']:
                u.background.setdefault('management', {}).setdefault('auto_delete', []).append(channel.id)
                u.update(u.background, 'background.json')
                self.bot.loop.create_task(self.on_message(channel))
                self.bot.loop.create_task(self.delete())
                print('Looping {}'.format(channel.id))
                await ctx.send('✅ **Auto-deleting all messages in this channel.**', delete_after=5)
            else: raise exc.Exists
        except exc.Exists: await ctx.send('❌ **Already deleting in this channel.** Type `stop` to stop deleting.')
            traceback.print_exc()
