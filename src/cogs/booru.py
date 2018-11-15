import asyncio
import json
import re
import sys
import traceback as tb
from contextlib import suppress
from datetime import datetime as dt
from datetime import timedelta as td
from fractions import gcd
import copy

import discord as d
from discord import errors as err
from discord import reaction
from discord.ext import commands as cmds
from discord.ext.commands import errors as errext

from cogs import tools
from misc import exceptions as exc
from misc import checks
from utils import utils as u
from utils import formatter, scraper


class MsG:

    def __init__(self, bot):
        self.bot = bot
        self.LIMIT = 100
        self.HISTORY_LIMIT = 150
        self.reversiqueue = asyncio.Queue()
        self.heartqueue = asyncio.Queue()
        self.reversifying = False
        self.updating = False
        self.hearting = False

        time = (dt.utcnow() - td(days=29)).strftime('%d/%m/%Y/%H:%M:%S')
        self.suggested = u.setdefault('cogs/suggested.pkl', 7)
        # self.suggested = u.setdefault('cogs/suggested.pkl', {'last_update': 'test', 'tags': {}, 'total': 1})
        print(self.suggested)
        self.favorites = u.setdefault('cogs/favorites.pkl', {})
        self.blacklists = u.setdefault('cogs/blacklists.pkl', {'global': {}, 'channel': {}, 'user': {}})

        if not self.hearting:
            self.hearting = True
            self.bot.loop.create_task(self._send_hearts())
            print('STARTED : hearting')
        if u.tasks['auto_rev']:
            for channel in u.tasks['auto_rev']:
                temp = self.bot.get_channel(channel)
                self.bot.loop.create_task(self.queue_for_reversification(temp))
                print('STARTED : auto-reversifying in #{}'.format(temp.name))
            self.reversifying = True
            self.bot.loop.create_task(self._reversify())
        if u.tasks['auto_hrt']:
            for channel in u.tasks['auto_hrt']:
                temp = self.bot.get_channel(channel)
                self.bot.loop.create_task(self.queue_for_hearts(channel=temp))
                print(f'STARTED : auto-hearting in #{temp.name}')
        # if not self.updating:
        #     self.updating = True
        #     self.bot.loop.create_task(self._update_suggested())

    async def _update_suggested(self):
        while self.updating:
            print('Checking for tag updates...')
            print(self.suggested)

            time = dt.utcnow()
            last_update = dt.strptime(self.suggested['last_update'], '%d/%m/%Y/%H:%M:%S')
            delta = time - last_update
            print(delta.days)

            if delta.days < 30:
                print('Up to date.')
            else:
                page = 1
                pages = len(list(self.suggested['tags'].keys()))

                print(f'Last updated: {self.suggested["last_update"]}')
                print('Updating tags...')

                content = await u.fetch('https://e621.net/tag/index.json', params={'order': 'count', 'limit': 500, 'page': page}, json=True)
                while content:
                    for tag in content:
                        self.suggested['tags'][tag['name']] = tag['count']
                        self.suggested['total'] += tag['count']
                    print(f'    UPDATED : PAGE {page} / {pages}', end='\r')

                    page += 1
                    content = await u.fetch('https://e621.net/tag/index.json', params={'order': 'count', 'limit': 500, 'page': page}, json=True)

                u.dump(self.suggested, 'cogs/suggested.pkl')
                self.suggested['last_update'] = time.strftime('%d/%m/%Y/%H:%M:%S')

                print('\nFinished updating tags.')

            await asyncio.sleep(24 * 60 * 60)

    def _get_favorites(self, ctx, args):
        if '-f' in args or '-favs' in args or '-faves' in args or '-favorites' in args:
            if self.favorites.get(ctx.author.id, {}).get('tags', set()):
                args = ['~{}'.format(tag)
                        for tag in self.favorites[ctx.author.id]['tags']]
            else:
                raise exc.FavoritesNotFound

        return args

    def _get_score(self, score):
        if score < 0:
            return 'https://emojipedia-us.s3.amazonaws.com/thumbs/320/twitter/103/pouting-face_1f621.png'
        elif score == 0:
            return 'https://emojipedia-us.s3.amazonaws.com/thumbs/320/mozilla/36/pile-of-poo_1f4a9.png'
        elif 10 > score > 0:
            return 'https://emojipedia-us.s3.amazonaws.com/thumbs/320/twitter/103/white-medium-star_2b50.png'
        elif 50 > score >= 10:
            return 'https://emojipedia-us.s3.amazonaws.com/thumbs/320/twitter/103/glowing-star_1f31f.png'
        elif 100 > score >= 50:
            return 'https://emojipedia-us.s3.amazonaws.com/thumbs/320/twitter/103/dizzy-symbol_1f4ab.png'
        elif score >= 100:
            return 'https://emojipedia-us.s3.amazonaws.com/thumbs/320/twitter/103/sparkles_2728.png'
        return None

    async def _send_hearts(self):
        while self.hearting:
            temp = await self.heartqueue.get()

            if isinstance(temp[1], d.Embed):
                await temp[0].send(embed=temp[1])

            elif isinstance(temp[1], d.Message):
                for match in re.finditer('(https?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', temp[1].content):
                    await temp[0].send(match)

                for attachment in temp[1].attachments:
                    await temp[0].send(attachment.url)

        print('STOPPED : hearting')

    async def queue_for_hearts(self, *, message=None, send=None, channel=None, reaction=True, timeout=60 * 60):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{HEAVY BLACK HEART}' and reaction.message.id == message.id and not user.bot:
                raise exc.Save(user)
            return False
        def on_reaction_channel(reaction, user):
            if reaction.message.channel.id == channel.id and not user.bot:
                if reaction.emoji == '\N{OCTAGONAL SIGN}' and user.permissions_in(reaction.message.channel).administrator:
                    raise exc.Abort
                if reaction.emoji == '\N{HEAVY BLACK HEART}' and (re.search('(https?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', reaction.message.content) or reaction.message.attachments):
                    raise exc.Save(user, reaction.message)
            return False

        if message:
            try:
                if reaction:
                    await message.add_reaction('\N{HEAVY BLACK HEART}')
                    await asyncio.sleep(1)

                while self.hearting:
                    try:
                        await self.bot.wait_for('reaction_add', check=on_reaction, timeout=timeout)

                    except exc.Save as e:
                        await self.heartqueue.put((e.user, send if send else message))

            except asyncio.TimeoutError:
                await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
        else:
            try:
                while self.hearting:
                    try:
                        await self.bot.wait_for('reaction_add', check=on_reaction_channel)

                    except exc.Save as e:
                        await self.heartqueue.put((e.user, message))

            except exc.Abort:
                u.tasks['auto_hrt'].remove(channel.id)
                u.dump(u.tasks, 'cogs/tasks.pkl')
                print('STOPPED : auto-hearting in #{}'.format(channel.name))
                await channel.send('**Stopped queueing messages for hearting in** {}'.format(channel.mention))

    @cmds.command(name='autoheart', aliases=['autohrt'])
    @cmds.has_permissions(administrator=True)
    async def auto_heart(self, ctx):
        try:
            if ctx.channel.id not in u.tasks['auto_hrt']:
                u.tasks['auto_hrt'].append(ctx.channel.id)
                u.dump(u.tasks, 'cogs/tasks.pkl')
                self.bot.loop.create_task(self.queue_for_hearts(channel=ctx.channel))
                print('STARTED : auto-hearting in #{}'.format(ctx.channel.name))
                await ctx.send('**Auto-hearting all messages in {}**'.format(ctx.channel.mention))
            else:
                raise exc.Exists

        except exc.Exists:
            message = await ctx.send('**Already auto-hearting in {}.** React with \N{OCTAGONAL SIGN} to stop.'.format(ctx.channel.mention))
            await message.add_reaction('\N{OCTAGONAL SIGN}')

    # @cmds.command()
    # async def auto_post(self, ctx):
    #     try:
    #         if ctx.channel.id not in u.tasks['auto_post']:
    #             u.tasks['auto_post'].append(ctx.channel.id)
    #             u.dump(u.tasks, 'cogs/tasks.pkl')
    #             self.bot.loop.create_task(self.queue_for_posting(ctx.channel))
    #             if not self.posting:
    #                 self.bot.loop.create_task(self._post())
    #                 self.posting = True
    #
    #             print('STARTED : auto-posting in #{}'.format(ctx.channel.name))
    #             await ctx.send('**Auto-posting all images in {}**'.format(ctx.channel.mention))
    #         else:
    #             raise exc.Exists
    #
    #     except exc.Exists:
    #         await ctx.send('**Already auto-posting in {}.** Type `stop` to stop.'.format(ctx.channel.mention))
    #         await ctx.message.add_reaction('\N{CROSS MARK}')

    @cmds.group(aliases=['tag', 't'], brief='(G) Get info on tags', description='Group command for obtaining info on tags\n\nUsage:\n\{p\}tag \{flag\} \{tag(s)\}')
    async def tags(self, ctx):
        pass

    # Tag search
    @tags.command(name='related', aliases=['relate', 'rel', 'r'], brief='(tags) Search for related tags', description='Return related tags for given tag(s)\n\nExample:\n\{p\}tag related wolf')
    async def _tags_related(self, ctx, *args):
        kwargs = u.get_kwargs(ctx, args)
        tags = kwargs['remaining']
        related = []
        c = 0

        await ctx.trigger_typing()

        for tag in tags:
            tag_request = await u.fetch('https://e621.net/tag/related.json', params={'tags': tag}, json=True)
            for rel in tag_request.get(tag, []):
                related.append(rel[0])

            if related:
                await ctx.send('`{}` **related tags:**\n```\n{}```'.format(tag, ' '.join(related)))
            else:
                await ctx.send(f'**No related tags found for:** `{tag}`')

            related.clear()
            c += 1

        if not c:
            await ctx.message.add_reaction('\N{CROSS MARK}')

    # Tag aliases
    @tags.command(name='aliases', aliases=['alias', 'als', 'a'], brief='(tags) Search for tag aliases', description='Return aliases for given tag(s)\n\nExample:\n\{p\}tag alias wolf')
    async def _tags_aliases(self, ctx, *args):
        kwargs = u.get_kwargs(ctx, args)
        tags = kwargs['remaining']
        aliases = []
        c = 0

        await ctx.trigger_typing()

        for tag in tags:
            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            for dic in alias_request:
                aliases.append(dic['name'])

            if aliases:
                await ctx.send('`{}` **aliases:**\n```\n{}```'.format(tag, ' '.join(aliases)))
            else:
                await ctx.send(f'**No aliases found for:** `{tag}`')

            aliases.clear()
            c += 1

        if not c:
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @cmds.group(aliases=['g'], brief='(G) Get e621 elements', description='Group command for obtaining various elements like post info\n\nUsage:\n\{p\}get \{flag\} \{args\}')
    async def get(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send('**Use a flag to get items.**\n*Type* `{}help get` *for more info.*'.format(ctx.prefix))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @get.command(name='info', aliases=['i'], brief='(get) Get info from post', description='Return info for given post URL or ID\n\nExample:\n\{p\}get info 1145042')
    async def _get_info(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            posts = kwargs['remaining']

            if not posts:
                raise exc.MissingArgument

            for ident in posts:
                await ctx.trigger_typing()

                ident = ident if not ident.isdigit() else re.search(
                    'show/([0-9]+)', ident).group(1)
                post = await u.fetch('https://e621.net/post/show.json', params={'id': ident}, json=True)

                embed = d.Embed(
                    title=', '.join(post['artist']), url=f'https://e621.net/post/show/{post["id"]}', color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else u.color)
                embed.set_thumbnail(url=post['file_url'])
                embed.set_author(name=f'{post["width"]} x {post["height"]}',
                                 url=f'https://e621.net/post?tags=ratio:{post["width"]/post["height"]:.2f}', icon_url=ctx.author.avatar_url)
                embed.set_footer(text=post['score'],
                                 icon_url=self._get_score(post['score']))

        except exc.MissingArgument:
            await ctx.send('**Invalid url**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @get.command(name='image', aliases=['img'], brief='(get) Get direct image from post', description='Return direct image URL for given post\n\nExample:\n\{p\}get image 1145042')
    async def _get_image(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            urls = kwargs['remaining']
            c = 0

            if not urls:
                raise exc.MissingArgument

            for url in urls:
                await ctx.trigger_typing()

                await ctx.send(await scraper.get_image(url))

                c += 1

                # except
                    # await ctx.send(f'**No aliases found for:** `{tag}`')

            if not c:
                await ctx.message.add_reaction('\N{CROSS MARK}')

        except exc.MissingArgument:
            await ctx.send('**Invalid url or file**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @get.command(name='pool', aliases=['p'], brief='(get) Get pool from query', description='Return pool info for given query\n\nExample:\n\{p\}get pool 1145042')
    async def _get_pool(self, ctx, *args):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and reaction.message.id == ctx.message.id and user is ctx.author:
                raise exc.Abort(match)
            return False

        def on_message(msg):
            return msg.content.isdigit() and int(msg.content) <= len(pools) and int(msg.content) > 0 and msg.author is ctx.author and msg.channel is ctx.channel

        try:
            kwargs = u.get_kwargs(ctx, args)
            query = kwargs['remaining']
            ident = None

            await ctx.trigger_typing()

            pools = []
            pool_request = await u.fetch('https://e621.net/pool/index.json', params={'query': ' '.join(query)}, json=True)
            if len(pool_request) > 1:
                for pool in pool_request:
                    pools.append(pool['name'])
                match = await ctx.send('**Multiple pools found for `{}`.** Type the number of the correct match\n```\n{}```'.format(' '.join(query), '\n'.join(['{} {}'.format(c, elem) for c, elem in enumerate(pools, 1)])))

                await ctx.message.add_reaction('\N{OCTAGONAL SIGN}')
                done, pending = await asyncio.wait([self.bot.wait_for('reaction_add', check=on_reaction, timeout=60),
                                                    self.bot.wait_for('reaction_remove', check=on_reaction, timeout=60), self.bot.wait_for('message', check=on_message, timeout=60)], return_when=asyncio.FIRST_COMPLETED)
                for future in done:
                    selection = future.result()

                with suppress(err.Forbidden):
                    await match.delete()
                tempool = [pool for pool in pool_request if pool['name']
                           == pools[int(selection.content) - 1]][0]
                with suppress(err.Forbidden):
                    await selection.delete()
            elif pool_request:
                tempool = pool_request[0]
            else:
                raise exc.NotFound

            await ctx.send(f'**{tempool["name"]}**\nhttps://e621.net/pool/show/{tempool["id"]}')

        except exc.Abort as e:
            await e.message.edit(content='\N{NO ENTRY SIGN}')

    # Reverse image searches a linked image using the public iqdb
    @cmds.command(name='reverse', aliases=['rev', 'ris'], brief='Reverse image search from e621', description='NSFW\nReverse-search an image with given URL')
    async def reverse(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            urls, remove = kwargs['remaining'], kwargs['remove']
            c = 0

            if not urls and not ctx.message.attachments:
                raise exc.MissingArgument

            for attachment in ctx.message.attachments:
                urls.append(attachment.url)

            for url in urls:
                try:
                    await ctx.trigger_typing()

                    post = await scraper.get_post(url)

                    embed = d.Embed(
                        title=', '.join(post['artist']), url=f'https://e621.net/post/show/{post["id"]}', color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else u.color)
                    embed.set_image(url=post['file_url'])
                    embed.set_author(name=f'{post["width"]} x {post["height"]}',
                                     url=f'https://e621.net/post?tags=ratio:{post["width"]/post["height"]:.2f}', icon_url=ctx.author.avatar_url)
                    embed.set_footer(text=post['score'],
                                     icon_url=self._get_score(post['score']))

                    await ctx.send('**Probable match**', embed=embed)

                    c += 1

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e))

            if not c:
                await ctx.message.add_reaction('\N{CROSS MARK}')
            elif remove:
                with suppress(err.NotFound):
                    await ctx.message.delete()

        except exc.MissingArgument:
            await ctx.send('**Invalid url or file.** Be sure the link directs to an image file')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.SizeError as e:
            await ctx.send(f'`{e}` **too large.** Maximum is 8 MB')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except err.HTTPException:
            await ctx.send('\N{CROSS MARK} **The image database returned an unexpected result.** It may be offline')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @cmds.command(name='reversify', aliases=['revify', 'risify', 'rify'])
    async def reversify(self, ctx, *args):
        try:
            dest = ctx
            kwargs = u.get_kwargs(ctx, args, limit=self.HISTORY_LIMIT / 5)
            remove, limit = kwargs['remove'], kwargs['limit']
            links = {}
            c = 0

            if not ctx.author.permissions_in(ctx.channel).manage_messages:
                dest = ctx.author

            async for message in ctx.channel.history(limit=self.HISTORY_LIMIT * limit):
                if c >= limit:
                    break
                if message.author.id != self.bot.user.id and (re.search('(https?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content) is not None or message.embeds or message.attachments):
                    links[message] = []
                    for match in re.finditer('(https?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content):
                        links[message].append(match.group(0))
                    for embed in message.embeds:
                        if embed.image.url is not d.Embed.Empty:
                            links[message].append(embed.image.url)
                    for attachment in message.attachments:
                        links[message].append(attachment.url)

                    await message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')
                    c += 1

            if not links:
                raise exc.NotFound

            n = 1
            for message, urls in links.items():
                for url in urls:
                    try:
                        await ctx.trigger_typing()

                        post = await scraper.get_post(url)

                        embed = d.Embed(
                            title=', '.join(post['artist']), url=f'https://e621.net/post/show/{post["id"]}', color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else u.color)
                        embed.set_image(url=post['file_url'])
                        embed.set_author(name=f'{post["width"]} x {post["height"]}',
                                         url=f'https://e621.net/post?tags=ratio:{post["width"]/post["height"]:.2f}', icon_url=ctx.author.avatar_url)
                        embed.set_footer(
                            text=post['score'], icon_url=self._get_score(post['score']))

                        await dest.send(f'**Probable match from** {message.author.display_name}', embed=embed)
                        await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                        if remove:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await dest.send('`{} / {}` **No probable match for:** `{}`'.format(n, len(links), e))
                        await message.add_reaction('\N{CROSS MARK}')
                        c -= 1
                    except exc.SizeError as e:
                        await dest.send(f'`{e}` **too large.** Maximum is 8 MB')
                        await message.add_reaction('\N{CROSS MARK}')
                        c -= 1

                    finally:
                        n += 1

            if c <= 0:
                await ctx.message.add_reaction('\N{CROSS MARK}')

        except exc.NotFound:
            await dest.send('**No matches found**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.BoundsError as e:
            await dest.send('`{}` **invalid limit.** Query limited to 30'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except err.HTTPException:
            await dest.send('\N{CROSS MARK} **The image database returned an unexpected result.** It may be offline')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    async def _reversify(self):
        while self.reversifying:
            message = await self.reversiqueue.get()
            urls = []

            for match in re.finditer('(https?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content):
                urls.append(match.group(0))
            for embed in message.embeds:
                if embed.image.url is not d.Embed.Empty:
                    urls.append(embed.image.url)
            for attachment in message.attachments:
                urls.append(attachment.url)

            for url in urls:
                try:
                    await message.channel.trigger_typing()

                    post = await scraper.get_post(url)

                    embed = d.Embed(
                        title=', '.join(post['artist']), url=f'https://e621.net/post/show/{post["id"]}', color=message.channel.guild.me.color if isinstance(message.channel, d.TextChannel) else u.color)
                    embed.set_image(url=post['file_url'])
                    embed.set_author(name=f'{post["width"]} x {post["height"]}',
                                     url=f'https://e621.net/post?tags=ratio:{post["width"]/post["height"]:.2f}', icon_url=message.author.avatar_url)
                    embed.set_footer(text=post['score'],
                                     icon_url=self._get_score(post['score']))

                    await message.channel.send('**Probable match from** {}'.format(message.author.display_name), embed=embed)

                    await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                    with suppress(err.NotFound):
                        await message.delete()

                except exc.MatchError as e:
                    await message.channel.send('**No probable match for:** `{}`'.format(e))
                    await message.add_reaction('\N{CROSS MARK}')
                except exc.SizeError as e:
                    await message.channel.send(f'`{e}` **too large.** Maximum is 8 MB')
                    await message.add_reaction('\N{CROSS MARK}')
                except Exception:
                    await message.channel.send(f'**An unknown error occurred.**')
                    await message.add_reaction('\N{WARNING SIGN}')

        print('STOPPED : reversifying')

    async def queue_for_reversification(self, channel):
        def check(msg):
            if 'stop r' in msg.content.lower() and msg.channel is channel and msg.author.guild_permissions.administrator:
                raise exc.Abort
            elif msg.channel is channel and msg.author.id != self.bot.user.id and (re.search('(https?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', msg.content) is not None or msg.attachments or msg.embeds):
                return True
            return False

        try:
            while self.reversifying:
                message = await self.bot.wait_for('message', check=check)
                await self.reversiqueue.put(message)
                await message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

        except exc.Abort:
            u.tasks['auto_rev'].remove(channel.id)
            u.dump(u.tasks, 'cogs/tasks.pkl')
            if not u.tasks['auto_rev']:
                self.reversifying = False
            print('STOPPED : reversifying #{}'.format(channel.name))
            await channel.send('**Stopped queueing messages for reversification in** {}'.format(channel.mention))

    @cmds.command(name='autoreversify', aliases=['autorev'])
    @cmds.has_permissions(manage_channels=True)
    async def auto_reversify(self, ctx):
        if ctx.channel.id not in u.tasks['auto_rev']:
            u.tasks['auto_rev'].append(ctx.channel.id)
            u.dump(u.tasks, 'cogs/tasks.pkl')
            self.bot.loop.create_task(
                self.queue_for_reversification(ctx.channel))
            if not self.reversifying:
                self.bot.loop.create_task(self._reversify())
                self.reversifying = True

            print('STARTED : auto-reversifying in #{}'.format(ctx.channel.name))
            await ctx.send('**Auto-reversifying all images in** {}'.format(ctx.channel.mention))
        else:
            await ctx.send('**Already auto-reversifying in {}.** Type `stop r(eversifying)` to stop.'.format(ctx.channel.mention))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    async def _get_pool(self, ctx, *, booru='e621', query=[]):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and reaction.message.id == ctx.message.id and user is ctx.author:
                raise exc.Abort(match)
            return False

        def on_message(msg):
            return msg.content.isdigit() and int(msg.content) <= len(pools) and int(msg.content) > 0 and msg.author is ctx.author and msg.channel is ctx.channel

        posts = {}
        pool = {}

        try:
            pools = []
            pool_request = await u.fetch('https://{}.net/pool/index.json'.format(booru), params={'query': ' '.join(query)}, json=True)
            if len(pool_request) > 1:
                for pool in pool_request:
                    pools.append(pool['name'])
                match = await ctx.send('**Multiple pools found for `{}`.** Type the number of the correct match.\n```\n{}```'.format(' '.join(query), '\n'.join(['{} {}'.format(c, elem) for c, elem in enumerate(pools, 1)])))

                await ctx.message.add_reaction('\N{OCTAGONAL SIGN}')
                done, pending = await asyncio.wait([self.bot.wait_for('reaction_add', check=on_reaction, timeout=60),
                                                    self.bot.wait_for('reaction_remove', check=on_reaction, timeout=60), self.bot.wait_for('message', check=on_message, timeout=60)], return_when=asyncio.FIRST_COMPLETED)
                for future in done:
                    selection = future.result()

                with suppress(err.Forbidden):
                    await match.delete()
                tempool = [pool for pool in pool_request if pool['name']
                           == pools[int(selection.content) - 1]][0]
                with suppress(err.Forbidden):
                    await selection.delete()
                pool = {'name': tempool['name'], 'id': tempool['id']}

                await ctx.trigger_typing()
            elif pool_request:
                tempool = pool_request[0]
                pool = {'name': pool_request[0]
                        ['name'], 'id': pool_request[0]['id']}
            else:
                raise exc.NotFound

            page = 1
            while len(posts) < tempool['post_count']:
                posts_request = await u.fetch('https://{}.net/pool/show.json'.format(booru), params={'id': tempool['id'], 'page': page}, json=True)
                for post in posts_request['posts']:
                    posts[post['id']] = {'artist': ', '.join(
                        post['artist']), 'file_url': post['file_url'], 'score': post['score']}
                page += 1

            return pool, posts

        except exc.Abort as e:
            await e.message.edit(content='\N{NO ENTRY SIGN}')
            raise exc.Continue

    # Messy code that checks image limit and tags in blacklists
    async def _get_posts(self, ctx, *, booru='e621', tags=[], limit=1, previous={}):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        blacklist = set()
        # Creates temp blacklist based on context
        for bl in (self.blacklists['global_blacklist'], self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()), self.blacklists['user_blacklist'].get(ctx.author.id, set())):
            for tag in bl:
                blacklist.update([tag] + list(self.aliases[tag]))
        # Checks for, assigns, and removes first order in tags if possible
        order = [tag for tag in tags if 'order:' in tag]
        if order:
            order = order[0]
            tags.remove(order)
        else:
            order = 'order:random'
        # Checks if tags are in local blacklists
        if tags:
            if (len(tags) > 5 and booru == 'e621') or (len(tags) > 4 and booru == 'e926'):
                raise exc.TagBoundsError(' '.join(tags[5:]))
            for tag in tags:
                if tag == 'swf' or tag == 'webm' or tag in blacklist:
                    raise exc.TagBlacklisted(tag)

        # Checks for blacklisted tags in endpoint blacklists - try/except is for continuing the parent loop
        posts = {}
        temposts = len(posts)
        empty = 0
        c = 0
        while len(posts) < limit:
            if c == limit * 5 + (self.LIMIT / 5):
                raise exc.Timeout
            request = await u.fetch('https://{}.net/post/index.json'.format(booru), params={'tags': ','.join([order] + tags), 'limit': int(self.LIMIT * limit)}, json=True)
            if len(request) == 0:
                raise exc.NotFound(' '.join(tags))
            if len(request) < limit:
                limit = len(request)

            for post in request:
                if 'swf' in post['file_ext'] or 'webm' in post['file_ext']:
                    continue
                try:
                    for tag in blacklist:
                        if tag in post['tags']:
                            raise exc.Continue
                except exc.Continue:
                    continue
                if post['id'] not in posts.keys() and post['id'] not in previous.keys():
                    posts[post['id']] = {'artist': ', '.join(
                        post['artist']), 'file_url': post['file_url'], 'score': post['score']}
                if len(posts) == limit:
                    break

            if len(posts) == temposts:
                empty += 1
                if empty == 5:
                    break
            else:
                empty = 0
                temposts = len(posts)
                c += 1

        if posts:
            return posts, order
        else:
            raise exc.NotFound(' '.join(tags))

    # Creates reaction-based paginator for linked pools
    @cmds.command(name='poolpage', aliases=['poolp', 'pp', 'e621pp', 'e6pp', '6pp'], brief='e621 pool paginator', description='e621 | NSFW\nShow pools in a page format')
    async def pool_paginator(self, ctx, *args):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and reaction.message.id == ctx.message.id and (user is ctx.author or user.permissions_in(reaction.message.channel).manage_messages):
                raise exc.Abort
            elif reaction.emoji == '\N{HEAVY BLACK HEART}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Save
            elif reaction.emoji == '\N{LEFTWARDS BLACK ARROW}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Left
            elif reaction.emoji == '\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.GoTo
            elif reaction.emoji == '\N{BLACK RIGHTWARDS ARROW}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Right
            return False

        def on_message(msg):
            return msg.content.isdigit() and 0 <= int(msg.content) <= len(posts) and msg.author is ctx.author and msg.channel is ctx.channel

        try:
            kwargs = u.get_kwargs(ctx, args)
            query = kwargs['remaining']
            hearted = {}
            c = 1

            await ctx.trigger_typing()

            pool, posts = await self._get_pool(ctx, booru='e621', query=query)
            keys = list(posts.keys())
            values = list(posts.values())

            embed = d.Embed(
                title=values[c - 1]['artist'], url='https://e621.net/post/show/{}'.format(keys[c - 1]), color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else u.color)
            embed.set_image(url=values[c - 1]['file_url'])
            embed.set_author(name=pool['name'],
                             url='https://e621.net/pool/show?id={}'.format(pool['id']), icon_url=ctx.author.avatar_url)
            embed.set_footer(text='{} / {}'.format(c, len(posts)),
                             icon_url=self._get_score(values[c - 1]['score']))

            paginator = await ctx.send(embed=embed)

            for emoji in ('\N{HEAVY BLACK HEART}', '\N{LEFTWARDS BLACK ARROW}', '\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}', '\N{BLACK RIGHTWARDS ARROW}'):
                await paginator.add_reaction(emoji)
            await ctx.message.add_reaction('\N{OCTAGONAL SIGN}')
            await asyncio.sleep(1)

            while not self.bot.is_closed():
                try:
                    await asyncio.gather(*[self.bot.wait_for('reaction_add', check=on_reaction, timeout=8 * 60),
                                           self.bot.wait_for('reaction_remove', check=on_reaction, timeout=8 * 60)])

                except exc.Save:
                    if keys[c - 1] not in hearted:
                        hearted[keys[c - 1]] = copy.deepcopy(embed)

                        await paginator.edit(content='\N{HEAVY BLACK HEART}')
                    else:
                        del hearted[keys[c - 1]]

                        await paginator.edit(content='\N{BROKEN HEART}')

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['artist']
                        embed.url = 'https://e621.net/post/show/{}'.format(
                            keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url=self._get_score(values[c - 1]['score']))
                        embed.set_image(url=values[c - 1]['file_url'])

                        await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)
                    else:
                        await paginator.edit(content='\N{BLACK RIGHTWARDS ARROW}')

                except exc.GoTo:
                    await paginator.edit(content='\N{INPUT SYMBOL FOR NUMBERS}')
                    number = await self.bot.wait_for('message', check=on_message, timeout=8 * 60)

                    if int(number.content) != 0:
                        c = int(number.content)

                        embed.title = values[c - 1]['artist']
                        embed.url = 'https://e621.net/post/show/{}'.format(
                            keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url=self._get_score(values[c - 1]['score']))
                        embed.set_image(url=values[c - 1]['file_url'])

                    if ctx.channel is d.TextChannel:
                        with suppress(errext.CheckFailure):
                            await number.delete()

                    await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)

                except exc.Right:
                    if c < len(keys):
                        c += 1
                        embed.title = values[c - 1]['artist']
                        embed.url = 'https://e621.net/post/show/{}'.format(
                            keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url=self._get_score(values[c - 1]['score']))
                        embed.set_image(url=values[c - 1]['file_url'])

                        await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)
                    else:
                        await paginator.edit(content='\N{LEFTWARDS BLACK ARROW}')

        except exc.Abort:
            try:
                await paginator.edit(content='\N{WHITE HEAVY CHECK MARK}')
            except UnboundLocalError:
                await ctx.send('\N{WHITE HEAVY CHECK MARK}')
        except asyncio.TimeoutError:
            try:
                await paginator.edit(content='\N{HOURGLASS}')
            except UnboundLocalError:
                await ctx.send('\N{HOURGLASS}')
        except exc.NotFound:
            await ctx.send('**Pool not found**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Continue:
            pass

        finally:
            if hearted:
                await ctx.message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

                n = 1
                for embed in hearted.values():
                    await ctx.author.send(content=f'`{n} / {len(hearted)}`', embed=embed)
                    n += 1

    @cmds.command(name='e621page', aliases=['e621p', 'e6p', '6p'])
    @checks.is_nsfw()
    async def e621_paginator(self, ctx, *args):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and reaction.message.id == ctx.message.id and (user is ctx.author or user.permissions_in(reaction.message.channel).manage_messages):
                raise exc.Abort
            elif reaction.emoji == '\N{HEAVY BLACK HEART}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Save
            elif reaction.emoji == '\N{LEFTWARDS BLACK ARROW}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Left
            elif reaction.emoji == '\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.GoTo
            elif reaction.emoji == '\N{BLACK RIGHTWARDS ARROW}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Right
            return False

        def on_message(msg):
            return msg.content.isdigit() and 0 <= int(msg.content) <= len(posts) and msg.author is ctx.author and msg.channel is ctx.channel

        try:
            kwargs = u.get_kwargs(ctx, args)
            tags = kwargs['remaining']
            limit = self.LIMIT / 5
            hearted = {}
            c = 1

            tags = self._get_favorites(ctx, tags)

            await ctx.trigger_typing()

            posts, order = await self._get_posts(ctx, booru='e621', tags=tags, limit=limit)
            keys = list(posts.keys())
            values = list(posts.values())

            embed = d.Embed(
                title=values[c - 1]['artist'], url='https://e621.net/post/show/{}'.format(keys[c - 1]), color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else u.color)
            embed.set_image(url=values[c - 1]['file_url'])
            embed.set_author(name=' '.join(tags) if tags else order,
                             url='https://e621.net/post?tags={}'.format(','.join(tags)), icon_url=ctx.author.avatar_url)
            embed.set_footer(text=values[c - 1]['score'],
                             icon_url=self._get_score(values[c - 1]['score']))

            paginator = await ctx.send(embed=embed)

            for emoji in ('\N{HEAVY BLACK HEART}', '\N{LEFTWARDS BLACK ARROW}', '\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}', '\N{BLACK RIGHTWARDS ARROW}'):
                await paginator.add_reaction(emoji)
            await ctx.message.add_reaction('\N{OCTAGONAL SIGN}')
            await asyncio.sleep(1)

            while not self.bot.is_closed():
                try:
                    await asyncio.gather(*[self.bot.wait_for('reaction_add', check=on_reaction, timeout=8 * 60),
                                           self.bot.wait_for('reaction_remove', check=on_reaction, timeout=8 * 60)])

                except exc.Save:
                    if keys[c - 1] not in hearted.keys():
                        hearted[keys[c - 1]] = copy.deepcopy(embed)

                        await paginator.edit(content='\N{HEAVY BLACK HEART}')
                    else:
                        del hearted[keys[c - 1]]

                        await paginator.edit(content='\N{BROKEN HEART}')

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['artist']
                        embed.url = 'https://e621.net/post/show/{}'.format(
                            keys[c - 1])
                        embed.set_footer(text=values[c - 1]['score'],
                                         icon_url=self._get_score(values[c - 1]['score']))
                        embed.set_image(url=values[c - 1]['file_url'])

                        await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)
                    else:
                        await paginator.edit(content='\N{BLACK RIGHTWARDS ARROW}')

                except exc.GoTo:
                    await paginator.edit(content=f'`{c} / {len(posts)}`')
                    number = await self.bot.wait_for('message', check=on_message, timeout=8 * 60)

                    if int(number.content) != 0:
                        c = int(number.content)

                        embed.title = values[c - 1]['artist']
                        embed.url = 'https://e621.net/post/show/{}'.format(
                            keys[c - 1])
                        embed.set_footer(text=values[c - 1]['score'],
                                         icon_url=self._get_score(values[c - 1]['score']))
                        embed.set_image(url=values[c - 1]['file_url'])

                    if ctx.channel is d.TextChannel:
                        with suppress(errext.CheckFailure):
                            await number.delete()

                    await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)

                except exc.Right:
                    try:
                        if c % limit == 0:
                            await ctx.trigger_typing()
                            temposts, order = await self._get_posts(ctx, booru='e621', tags=tags, limit=limit, previous=posts)
                            posts.update(temposts)

                            keys = list(posts.keys())
                            values = list(posts.values())

                        if c < len(keys):
                            c += 1
                            embed.title = values[c - 1]['artist']
                            embed.url = 'https://e621.net/post/show/{}'.format(
                                keys[c - 1])
                            embed.set_footer(text=values[c - 1]['score'],
                                             icon_url=self._get_score(values[c - 1]['score']))
                            embed.set_image(url=values[c - 1]['file_url'])

                            await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)
                        else:
                            await paginator.edit(content='\N{LEFTWARDS BLACK ARROW}')

                    except exc.NotFound:
                        await paginator.edit(content='\N{LEFTWARDS BLACK ARROW}')

        except exc.Abort:
            try:
                await paginator.edit(content='\N{WHITE HEAVY CHECK MARK}')
            except UnboundLocalError:
                await ctx.send('\N{HOURGLASS}')
        except asyncio.TimeoutError:
            try:
                await paginator.edit(content='\N{HOURGLASS}')
            except UnboundLocalError:
                await ctx.send('\N{HOURGLASS}')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBlacklisted as e:
            await ctx.send('\N{NO ENTRY SIGN} `{}` **blacklisted**'.format(e))
            await ctx.message.add_reaction('\N{NO ENTRY SIGN}')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5.'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

        finally:
            if hearted:
                await ctx.message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

                n = 1
                for embed in hearted.values():
                    await ctx.author.send(content=f'`{n} / {len(hearted)}`', embed=embed)
                    n += 1

    # @e621_paginator.error
    # async def e621_paginator_error(self, ctx, error):
    #     if isinstance(error, exc.NSFW):
    #         await ctx.send('\N{NO ENTRY} {} **is not an NSFW channel**'.format(ctx.channel.mention))
    #         await ctx.message.add_reaction('\N{NO ENTRY}')

    @cmds.command(name='e926page', aliases=['e926p', 'e9p', '9p'])
    async def e926_paginator(self, ctx, *args):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and reaction.message.id == ctx.message.id and (user is ctx.author or user.permissions_in(reaction.message.channel).manage_messages):
                raise exc.Abort
            elif reaction.emoji == '\N{HEAVY BLACK HEART}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Save
            elif reaction.emoji == '\N{LEFTWARDS BLACK ARROW}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Left
            elif reaction.emoji == '\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.GoTo
            elif reaction.emoji == '\N{BLACK RIGHTWARDS ARROW}' and reaction.message.id == paginator.id and user is ctx.author:
                raise exc.Right
            return False

        def on_message(msg):
            return msg.content.isdigit() and 0 <= int(msg.content) <= len(posts) and msg.author is ctx.author and msg.channel is ctx.channel

        try:
            kwargs = u.get_kwargs(ctx, args)
            tags = kwargs['remaining']
            limit = self.LIMIT / 5
            hearted = {}
            c = 1

            tags = self._get_favorites(ctx, tags)

            await ctx.trigger_typing()

            posts, order = await self._get_posts(ctx, booru='e926', tags=tags, limit=limit)
            keys = list(posts.keys())
            values = list(posts.values())

            embed = d.Embed(
                title=values[c - 1]['artist'], url='https://e926.net/post/show/{}'.format(keys[c - 1]), color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else u.color)
            embed.set_image(url=values[c - 1]['file_url'])
            embed.set_author(name=' '.join(tags) if tags else order,
                             url='https://e926.net/post?tags={}'.format(','.join(tags)), icon_url=ctx.author.avatar_url)
            embed.set_footer(text=values[c - 1]['score'],
                             icon_url=self._get_score(values[c - 1]['score']))

            paginator = await ctx.send(embed=embed)

            for emoji in ('\N{HEAVY BLACK HEART}', '\N{LEFTWARDS BLACK ARROW}', '\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}', '\N{BLACK RIGHTWARDS ARROW}'):
                await paginator.add_reaction(emoji)
            await ctx.message.add_reaction('\N{OCTAGONAL SIGN}')
            await asyncio.sleep(1)

            while not self.bot.is_closed():
                try:
                    await asyncio.gather(*[self.bot.wait_for('reaction_add', check=on_reaction, timeout=8 * 60),
                                           self.bot.wait_for('reaction_remove', check=on_reaction, timeout=8 * 60)])

                except exc.Save:
                    if keys[c - 1] not in hearted:
                        hearted[keys[c - 1]] = copy.deepcopy(embed)

                        await paginator.edit(content='\N{HEAVY BLACK HEART}')
                    else:
                        del hearted[keys[c - 1]]

                        await paginator.edit(content='\N{BROKEN HEART}')

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['artist']
                        embed.url = 'https://e926.net/post/show/{}'.format(
                            keys[c - 1])
                        embed.set_footer(text=values[c - 1]['score'],
                                         icon_url=self._get_score(values[c - 1]['score']))
                        embed.set_image(url=values[c - 1]['file_url'])

                        await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)
                    else:
                        await paginator.edit(content='\N{BLACK RIGHTWARDS ARROW}')

                except exc.GoTo:
                    await paginator.edit(content=f'`{c} / {len(posts)}`')
                    number = await self.bot.wait_for('message', check=on_message, timeout=8 * 60)

                    if int(number.content) != 0:
                        c = int(number.content)

                        embed.title = values[c - 1]['artist']
                        embed.url = 'https://e926.net/post/show/{}'.format(
                            keys[c - 1])
                        embed.set_footer(text=values[c - 1]['score'],
                                         icon_url=self._get_score(values[c - 1]['score']))
                        embed.set_image(url=values[c - 1]['file_url'])

                    await number.delete()

                    await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)

                except exc.Right:
                    try:
                        if c % limit == 0:
                            await ctx.trigger_typing()
                            temposts, order = await self._get_posts(ctx, booru='e926', tags=tags, limit=limit, previous=posts)
                            posts.update(temposts)

                            keys = list(posts.keys())
                            values = list(posts.values())

                        if c < len(keys):
                            c += 1
                            embed.title = values[c - 1]['artist']
                            embed.url = 'https://e926.net/post/show/{}'.format(
                                keys[c - 1])
                            embed.set_footer(text=values[c - 1]['score'],
                                             icon_url=self._get_score(values[c - 1]['score']))
                            embed.set_image(url=values[c - 1]['file_url'])

                            await paginator.edit(content='\N{HEAVY BLACK HEART}' if keys[c - 1] in hearted.keys() else None, embed=embed)
                        else:
                            await paginator.edit(content='\N{LEFTWARDS BLACK ARROW}')

                    except exc.NotFound:
                        await paginator.edit(content='\N{LEFTWARDS BLACK ARROW}')

        except exc.Abort:
            try:
                await paginator.edit(content='\N{WHITE HEAVY CHECK MARK}')
            except UnboundLocalError:
                await ctx.send('\N{WHITE HEAVY CHECK MARK}')
        except asyncio.TimeoutError:
            try:
                await paginator.edit(content='\N{HOURGLASS}')
            except UnboundLocalError:
                await ctx.send('\N{HOURGLASS}')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBlacklisted as e:
            await ctx.send('\N{NO ENTRY SIGN} `{}` **blacklisted**'.format(e))
            await ctx.message.add_reaction('\N{NO ENTRY SIGN}')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5.'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

        finally:
            if hearted:
                await ctx.message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

                n = 1
                for embed in hearted.values():
                    await ctx.author.send(content=f'`{n} / {len(hearted)}`', embed=embed)
                    n += 1

    # Searches for and returns images from e621.net given tags when not blacklisted
    @cmds.command(aliases=['e6', '6'], brief='e621 | NSFW', description='e621 | NSFW\nTag-based search for e621.net\n\nYou can only search 5 tags and 6 images at once for now.\ne6 [tags...] ([# of images])')
    @checks.is_nsfw()
    async def e621(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args, limit=3)
            args, limit = kwargs['remaining'], kwargs['limit']

            tags = self._get_favorites(ctx, args)

            await ctx.trigger_typing()

            posts, order = await self._get_posts(ctx, booru='e621', tags=tags, limit=limit)

            for ident, post in posts.items():
                embed = d.Embed(title=post['artist'], url='https://e621.net/post/show/{}'.format(ident),
                                color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else u.color)
                embed.set_image(url=post['file_url'])
                embed.set_author(name=' '.join(tags) if tags else order,
                                 url='https://e621.net/post?tags={}'.format(','.join(tags)), icon_url=ctx.author.avatar_url)
                embed.set_footer(
                    text=post['score'], icon_url=self._get_score(post['score']))

                message = await ctx.send(embed=embed)

                self.bot.loop.create_task(self.queue_for_hearts(message=message, send=embed))

        except exc.TagBlacklisted as e:
            await ctx.send('`{}` **blacklisted**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.BoundsError as e:
            await ctx.send('`{}` **out of bounds.** Images limited to 3.'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5.'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    # @e621.error
    # async def e621_error(self, ctx, error):
    #     if isinstance(error, exc.NSFW):
    #         await ctx.send('\N{NO ENTRY} {} **is not an NSFW channel**'.format(ctx.channel.mention))
    #         await ctx.message.add_reaction('\N{NO ENTRY}')

    # Searches for and returns images from e926.net given tags when not blacklisted
    @cmds.command(aliases=['e9', '9'], brief='e926 | SFW', description='e926 | SFW\nTag-based search for e926.net\n\nYou can only search 5 tags and 6 images at once for now.\ne9 [tags...] ([# of images])')
    async def e926(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args, limit=3)
            args, limit = kwargs['remaining'], kwargs['limit']

            tags = self._get_favorites(ctx, args)

            await ctx.trigger_typing()

            posts, order = await self._get_posts(ctx, booru='e926', tags=tags, limit=limit)

            for ident, post in posts.items():
                embed = d.Embed(title=post['artist'], url='https://e926.net/post/show/{}'.format(ident),
                                color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else u.color)
                embed.set_image(url=post['file_url'])
                embed.set_author(name=' '.join(tags) if tags else order,
                                 url='https://e621.net/post?tags={}'.format(','.join(tags)), icon_url=ctx.author.avatar_url)
                embed.set_footer(
                    text=post['score'], icon_url=self._get_score(post['score']))

                message = await ctx.send(embed=embed)

                self.bot.loop.create_task(self.queue_for_hearts(message=message, send=embed))

        except exc.TagBlacklisted as e:
            await ctx.send('`{}` **blacklisted**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.BoundsError as e:
            await ctx.send('`{}` **out of bounds.** Images limited to 3.'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5.'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @cmds.group(aliases=['fave', 'fav', 'f'])
    async def favorite(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send('**Use a flag to manage favorites.**\n*Type* `{}help fav` *for more info.*'.format(ctx.prefix))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @favorite.error
    async def favorite_error(self, ctx, error):
        pass

    @favorite.group(name='get', aliases=['g'])
    async def _get_favorite(self, ctx):
        pass

    @_get_favorite.command(name='tags', aliases=['t'])
    async def __get_favorite_tags(self, ctx, *args):
        await ctx.send('\N{WHITE MEDIUM STAR} {}**\'s favorite tags:**\n```\n{}```'.format(ctx.author.mention, ' '.join(self.favorites.get(ctx.author.id, {}).get('tags', set()))))

    @_get_favorite.command(name='posts', aliases=['p'])
    async def __get_favorite_posts(self, ctx):
        pass

    @favorite.group(name='add', aliases=['a'])
    async def _add_favorite(self, ctx):
        pass

    @_add_favorite.command(name='tags', aliases=['t'])
    async def __add_favorite_tags(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            tags = kwargs['remaining']

            for tag in tags:
                if tag in self.blacklists['user_blacklist'].get(ctx.author.id, set()):
                    raise exc.TagBlacklisted(tag)
            with suppress(KeyError):
                if len(self.favorites[ctx.author.id]['tags']) + len(tags) > 5:
                    raise exc.BoundsError

            self.favorites.setdefault(ctx.author.id, {}).setdefault(
                'tags', set()).update(tags)
            u.dump(self.favorites, 'cogs/favorites.pkl')

            await ctx.send('{} **added to their favorites:**\n```\n{}```'.format(ctx.author.mention, ' '.join(tags)))

        except exc.BoundsError:
            await ctx.send('**Favorites list currently limited to:** `5`')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBlacklisted as e:
            await ctx.send('\N{NO ENTRY SIGN} `{}` **blacklisted**')
            await ctx.message.add_reaction('\N{NO ENTRY SIGN}')

    @_add_favorite.command(name='posts', aliases=['p'])
    async def __add_favorite_posts(self, ctx, *posts):
        pass

    @favorite.group(name='remove', aliases=['r'])
    async def _remove_favorite(self, ctx):
        pass

    @_remove_favorite.command(name='tags', aliases=['t'])
    async def __remove_favorite_tags(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            tags = kwargs['remaining']

            for tag in tags:
                try:
                    self.favorites[ctx.author.id].get(
                        'tags', set()).remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.favorites, 'cogs/favorites.pkl')

            await ctx.send('{} **removed from their favorites:**\n```\n{}```'.format(ctx.author.mention, ' '.join(tags)))

        except KeyError:
            await ctx.send('**You do not have any favorites**')
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagError as e:
            await ctx.send('`{}` **not in favorites**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_remove_favorite.command(name='posts', aliases=['p'])
    async def __remove_favorite_posts(self, ctx):
        pass

    @favorite.group(name='clear', aliases=['c'])
    async def _clear_favorite(self, ctx):
        pass

    @_clear_favorite.command(name='tags', aliases=['t'])
    async def __clear_favorite_tags(self, ctx, *args):
        with suppress(KeyError):
            del self.favorites[ctx.author.id]
            u.dump(self.favorites, 'cogs/favorites.pkl')

        await ctx.send('{}**\'s favorites cleared**'.format(ctx.author.mention))

    @_clear_favorite.command(name='posts', aliases=['p'])
    async def __clear_favorite_posts(self, ctx):
        pass

    # Umbrella command structure to manage global, channel, and user blacklists
    @cmds.group(aliases=['bl', 'b'], brief='(G) Manage blacklists', description='Manage channel or personal blacklists\n\nUsage:\n{p}bl get {blacklist} to show a blacklist\n{p}bl clear {blacklist} to clear a blacklist\n{p}bl add {blacklist} {tags...} to add tag(s) to a blacklist\n{p}bl remove {blacklist} {tags...} to remove tags from a blacklist')
    async def blacklist(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send('**Use a flag to manage blacklists.**\n*Type* `{}help bl` *for more info.*'.format(ctx.prefix))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    # @blacklist.error
    # async def blacklist_error(self, ctx, error):
        # if isinstance(error, KeyError):
        #     return await ctx.send('**Blacklist does not exist**')

    @blacklist.group(name='get', aliases=['g'], brief='(G) Get a blacklist\n\nUsage:\n\{p\}bl get \{blacklist\}')
    async def _get_blacklist(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send('**Invalid blacklist**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_get_blacklist.command(name='alias', aliases=['aliases'])
    async def __get_blacklist_aliases(self, ctx, *args):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel
        args, lst = u.kwargs(args)

        aliases = {}
        # Creates temp aliases based on context
        for bl in (self.blacklists['global_blacklist'], self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()), self.blacklists['user_blacklist'].get(ctx.author.id, set())):
            for tag in bl:
                aliases[tag] = list(self.aliases[tag])

            # paginator.add_line(f'{tag}\n```{" ".join(alias_list)}```')
        args, lst = u.kwargs(args)

        await formatter.paginate(ctx, aliases, start='\N{NO ENTRY SIGN} **Contextual blacklist aliases:**\n')

    @_get_blacklist.command(name='global', aliases=['gl', 'g'], brief='Get current global blacklist', description='Get current global blacklist\n\nThis applies to all booru commands, in accordance with Discord\'s ToS agreement\n\nExample:\n\{p\}bl get global')
    async def __get_global_blacklist(self, ctx, *args):
        await ctx.send('\N{NO ENTRY SIGN} **Global blacklist:**\n```\n{}```'.format(' '.join(self.blacklists['global_blacklist'])))
        args, lst = u.kwargs(args)

    @_get_blacklist.command(name='channel', aliases=['ch', 'c'], brief='Get current channel blacklist', description='Get current channel blacklist\n\nThis is based on context - the channel where the command was executed\n\nExample:\{p\}bl get channel')
    async def __get_channel_blacklist(self, ctx, *args):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await ctx.send('\N{NO ENTRY SIGN} {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, ' '.join(self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()))))

    @_get_blacklist.command(name='me', aliases=['m'], brief='Get your personal blacklist', description='Get your personal blacklist\n\nYour blacklist is not viewable by anyone but you, except if you call this command in a public channel. The blacklist will be deleted soon after for your privacy\n\nExample:\n\{p\}bl get me')
    async def __get_user_blacklist(self, ctx, *args):
        await ctx.send('\N{NO ENTRY SIGN} {}**\'s blacklist:**\n```\n{}```'.format(ctx.author.mention, ' '.join(self.blacklists['user_blacklist'].get(ctx.author.id, set()))))

    @_get_blacklist.command(name='here', aliases=['h'], brief='Get current global and channel blacklists', description='Get current global and channel blacklists in a single message\n\nExample:\{p\}bl get here')
    async def __get_here_blacklists(self, ctx, *args):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await ctx.send('\N{NO ENTRY SIGN} **__Blacklisted:__**\n\n**Global:**\n```\n{}```\n**{}:**\n```\n{}```'.format(' '.join(self.blacklists['global_blacklist']), ctx.channel.mention, ' '.join(self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()))))

    @blacklist.group(name='add', aliases=['a'], brief='(G) Add tag(s) to a blacklist\n\nUsage:\n\{p\}bl add \{blacklist\} \{tags...\}')
    async def _add_tags(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send('**Invalid blacklist**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    async def _aliases(self, ctx, tags, blacklist):
        def on_reaction(reaction, user):
            if user is ctx.author and reaction.message.channel is ctx.message.channel:
                if reaction.emoji == '\N{THUMBS DOWN SIGN}':
                    raise exc.Continue
                if reaction.emoji == '\N{HEAVY MINUS SIGN}':
                    raise exc.Remove
                if reaction.emoji == '\N{THUMBS UP SIGN}':
                    return True
            return False

        def on_message(msg):
            if msg.author is ctx.message.author and msg.channel is ctx.message.channel:
                if msg.content == '0':
                    raise exc.Continue
                return True
            return False

        if not tags:
            raise exc.MissingArgument

        aliases = {}
        messages = []

        try:
            for tag in tags:
                blacklist.add(tag)
                aliases[tag] = set()

                alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
                if alias_request:
                    for dic in alias_request:
                        if dic['name']:
                            aliases[tag].add(dic['name'])

            messages = await formatter.paginate(ctx, aliases)
            message = await ctx.send(
                '**Also add aliases?** React with the minus sign (\N{HEAVY MINUS SIGN}) to remove unwanted aliases')
            await message.add_reaction('\N{THUMBS DOWN SIGN}')
            await message.add_reaction('\N{HEAVY MINUS SIGN}')
            await message.add_reaction('\N{THUMBS UP SIGN}')

            try:
                await self.bot.wait_for('reaction_add', check=on_reaction, timeout=8 * 60)

            except exc.Remove:
                await message.edit(content=f'Type the tag(s) to remove or `0` to continue:')

                try:
                    while not self.bot.is_closed():
                        response = await self.bot.wait_for('message', check=on_message, timeout=8 * 60)

                        for tag in response.content.split(' '):
                            try:
                                for e in aliases.values():
                                    e.remove(tag)
                                messages.append(await ctx.send(f'\N{WHITE HEAVY CHECK MARK} `{tag}` **removed**'))
                            except KeyError:
                                await ctx.send(f'\N{CROSS MARK} `{tag}` **not in aliases**', delete_after=8)
                except exc.Continue:
                    pass

                await message.edit(content=f'Confirm or deny changes')
                await self.bot.wait_for('reaction_add', check=on_reaction, timeout=8 * 60)

            self.aliases.update(aliases)
            u.dump(self.aliases, 'cogs/aliases.pkl')

            return blacklist

        except exc.Continue:
            return tags
        except asyncio.TimeoutError:
            await ctx.send('\N{CROSS MARK} **Command timed out**')
            raise exc.Abort
        except exc.Abort:
            raise exc.Abort

        finally:
            if messages:
                with suppress(err.NotFound):
                    for msg in messages:
                        await msg.delete()
                    await message.delete()

    @_add_tags.command(name='global', aliases=['gl', 'g'])
    @cmds.is_owner()
    async def __add_global_tags(self, ctx, *args):
        tags, lst = u.kwargs(args)

        try:
            async with ctx.channel.typing():
                tags = await self._aliases(ctx, tags, self.blacklists['global_blacklist'])

                u.dump(self.blacklists, 'cogs/blacklists.pkl')

                await ctx.send('\N{WHITE HEAVY CHECK MARK} **Added to global blacklist:**\n```\n{}```'.format(' '.join(tags)))

        except exc.Abort:
            await ctx.send('**Aborted**')
        except exc.MissingArgument:
            await ctx.send('\N{CROSS MARK} **Missing tags**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_add_tags.command(name='channel', aliases=['ch', 'c'], brief='@manage_channel@ Add tag(s) to the current channel blacklist (requires manage_channel)', description='Add tag(s) to the current channel blacklist ')
    @cmds.has_permissions(manage_channels=True)
    async def __add_channel_tags(self, ctx, *args):
        tags, lst = u.kwargs(args)

        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        try:
            async with ctx.channel.typing():
                tags = await self._aliases(ctx, tags, self.blacklists['guild_blacklist'].setdefault(guild.id, {}).setdefault(ctx.channel.id, set()))

                u.dump(self.blacklists, 'cogs/blacklists.pkl')

                await ctx.send('\N{WHITE HEAVY CHECK MARK} **Added to** {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, ' '.join(tags)))

        except exc.Abort:
            await ctx.send('**Aborted**')
        except exc.MissingArgument:
            await ctx.send('\N{CROSS MARK} **Missing tags**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_add_tags.command(name='me', aliases=['m'])
    async def __add_user_tags(self, ctx, *args):
        kwargs = u.get_kwargs(ctx, args)
        tags = kwargs['remaining']
        tags, lst = u.kwargs(args)

        try:
            async with ctx.channel.typing():
                tags = await self._aliases(ctx, tags, self.blacklists['user_blacklist'].setdefault(ctx.author.id, set()))

                u.dump(self.blacklists, 'cogs/blacklists.pkl')

                await ctx.send('\N{WHITE HEAVY CHECK MARK} {} **added to their blacklist:**\n```\n{}```'.format(ctx.author.mention, ' '.join(tags)))

        except exc.Abort:
            await ctx.send('**Aborted**')
        except exc.MissingArgument:
            await ctx.send('\N{CROSS MARK} **Missing tags**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @blacklist.group(name='remove', aliases=['rm', 'r'])
    async def _remove_tags(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send('**Invalid blacklist**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_remove_tags.command(name='global', aliases=['gl', 'g'])
    @cmds.is_owner()
    async def __remove_global_tags(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            tags = kwargs['remaining']

            for tag in tags:
                try:
                    self.blacklists['global_blacklist'].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')
        tags, lst = u.kwargs(args)

            await ctx.send('**Removed from global blacklist:**\n```\n{}```'.format(' '.join(tags)))

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_remove_tags.command(name='channel', aliases=['ch', 'c'])
    @cmds.has_permissions(manage_channels=True)
    async def __remove_channel_tags(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            tags = kwargs['remaining']

            guild = ctx.guild if isinstance(
                ctx.guild, d.Guild) else ctx.channel

            for tag in tags:
                try:
                    self.blacklists['guild_blacklist'][guild.id][ctx.channel.id].remove(
                        tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await ctx.send('**Removed from** {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, ' '.join(tags)))

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_remove_tags.command(name='me', aliases=['m'])
    async def __remove_user_tags(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            tags = kwargs['remaining']

            for tag in tags:
                try:
                    self.blacklists['user_blacklist'][ctx.author.id].remove(
                        tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await ctx.send('{} **removed from their blacklist:**\n```\n{}```'.format(ctx.author.mention, ' '.join(tags)))

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist**'.format(e))
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @blacklist.group(name='clear', aliases=['cl', 'c'])
    async def _clear_blacklist(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send('**Invalid blacklist**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_clear_blacklist.command(name='global', aliases=['gl', 'g'])
    @cmds.is_owner()
    async def __clear_global_blacklist(self, ctx, *args):
        args, lst = u.kwargs(args)
        u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('**Global blacklist cleared**')

    @_clear_blacklist.command(name='channel', aliases=['ch', 'c'])
    @cmds.has_permissions(manage_channels=True)
    async def __clear_channel_blacklist(self, ctx, *args):
        args, lst = u.kwargs(args)
            ctx.guild, d.Guild) else ctx.channel

        with suppress(KeyError):
            del self.blacklists['guild_blacklist'][guild.id][ctx.channel.id]
            u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('{} **blacklist cleared**'.format(ctx.channel.mention))
        args, lst = u.kwargs(args)

    @_clear_blacklist.command(name='me', aliases=['m'])
    async def __clear_user_blacklist(self, ctx, *args):
        with suppress(KeyError):
            del self.blacklists['user_blacklist'][ctx.author.id]
            u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('{}**\'s blacklist cleared**'.format(ctx.author.mention))
