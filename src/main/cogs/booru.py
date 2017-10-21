import asyncio
import json
import re
import traceback as tb
from contextlib import suppress

import discord as d
from discord import errors as err
from discord import reaction
from discord.ext import commands
from discord.ext.commands import errors as errext

from cogs import tools
from misc import exceptions as exc
from misc import checks
from utils import utils as u
from utils import formatter, scraper


class MsG:

    def __init__(self, bot):
        self.bot = bot
        self.color = d.Color(0x1A1A1A)
        self.LIMIT = 100
        self.HISTORY_LIMIT = 100
        self.RATE_LIMIT = u.RATE_LIMIT
        self.qualiqueue = asyncio.Queue()
        self.qualitifying = False

        self.favorites = u.setdefault('cogs/favorites.pkl', {'tags': set(), 'posts': set()})
        self.blacklists = u.setdefault(
            'cogs/blacklists.pkl', {'global_blacklist': set(), 'guild_blacklist': {}, 'user_blacklist': {}})
        self.aliases = u.setdefault('cogs/aliases.pkl', {})

        if u.tasks['auto_qual']:
            for channel in u.tasks['auto_qual']:
                temp = self.bot.get_channel(channel)
                self.bot.loop.create_task(self.qualiqueue_for_qualitification(temp))
                print('AUTO-QUALITIFYING : #{}'.format(temp.name))
            self.bot.loop.create_task(self._qualitify())
            self.qualitifying = True

    async def get_post(self, channel):
        post_request = await u.fetch('https://e621.net/post/index.json', json=True)

    @commands.command()
    async def auto_post(self, ctx):
        try:
            if ctx.channel.id not in u.tasks['auto_post']:
                u.tasks['auto_post'].append(ctx.channel.id)
                u.dump(u.tasks, 'cogs/tasks.pkl')
                self.bot.loop.create_task(self.qualiqueue_for_qualitification(ctx.channel))
                if not self.qualitifying:
                    self.bot.loop.create_task(self._qualitify())
                    self.qualitifying = True

                print('AUTO-POSTING : #{}'.format(ctx.channel.name))
                await ctx.send('**Auto-posting all images in {}.**'.format(ctx.channel.mention), delete_after=5)
                await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            else:
                raise exc.Exists

        except exc.Exists:
            await ctx.send('**Already auto-posting in {}.** Type `stop` to stop.'.format(ctx.channel.mention), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    # Tag search
    @commands.command(aliases=['rel'], brief='e621 Search for related tags', description='e621 | NSFW\nReturn related tags for a number of given tags', usage='[related|rel]')
    @checks.del_ctx()
    async def related(self, ctx, *args):
        kwargs = u.get_kwargs(ctx, args)
        dest, tags = kwargs['destination'], kwargs['remaining']
        related = []

        await dest.trigger_typing()

        for tag in tags:
            tag_request = await u.fetch('https://e621.net/tag/related.json', params={'tags': tag, 'type': 'general'}, json=True)
            for rel in tag_request.get(tag, []):
                related.append(rel[0])

            await dest.send('`{}` **related tags:**\n```\n{}```'.format(tag, formatter.tostring(related)))

            await asyncio.sleep(self.RATE_LIMIT)

            related.clear()

        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    # Tag aliases
    @commands.command(name='aliases', aliases=['alias'], brief='e621 Tag aliases', description='e621 | NSFW\nSearch aliases for given tag')
    @checks.del_ctx()
    async def tag_aliases(self, ctx, *args):
        kwargs = u.get_kwargs(ctx, args)
        dest, tags = kwargs['destination'], kwargs['remaining']
        aliases = []

        await dest.trigger_typing()

        for tag in tags:
            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            for dic in alias_request:
                aliases.append(dic['name'])

            await dest.send('`{}` **aliases:**\n```\n{}```'.format(tag, formatter.tostring(aliases)))

            await asyncio.sleep(self.RATE_LIMIT)

            aliases.clear()

        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @commands.command(name='getimage', aliases=['geti', 'gi'])
    @checks.del_ctx()
    async def get_image(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            dest, urls = kwargs['destination'], kwargs['remaining']

            if not urls:
                raise exc.MissingArgument

            for url in urls:
                try:
                    await dest.trigger_typing()

                    await dest.send('{}'.format(await scraper.get_image(url)))

                finally:
                    await asyncio.sleep(self.RATE_LIMIT)

            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.MissingArgument:
            await ctx.send('**Invalid url or file.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    # Reverse image searches a linked image using the public iqdb
    @commands.command(name='reverse', aliases=['rev', 'ris'], brief='e621 Reverse image search', description='e621 | NSFW\nReverse-search an image with given URL')
    @checks.del_ctx()
    async def reverse_image_search(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            dest, urls = kwargs['destination'], kwargs['remaining']
            c = 0

            if not urls and not ctx.message.attachments:
                raise exc.MissingArgument

            for url in urls:
                try:
                    await dest.trigger_typing()

                    await dest.send('**Probable match:**\n{}'.format(await scraper.get_post(url)))

                    c += 1
                    await asyncio.sleep(self.RATE_LIMIT)

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)

            for attachment in ctx.message.attachments:
                try:
                    await dest.trigger_typing()

                    await dest.send('**Probable match:**\n{}'.format(await scraper.get_post(attachment.url)))

                    c += 1
                    await asyncio.sleep(self.RATE_LIMIT)

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)

            if c:
                await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            else:
                await ctx.message.add_reaction('\N{CROSS MARK}')

        except exc.MissingArgument:
            await ctx.send('**Invalid url or file.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @commands.command(name='quality', aliases=['qual', 'qrev', 'qis'])
    @checks.del_ctx()
    async def quality_reverse_image_search(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            dest, urls = kwargs['destination'], kwargs['remaining']
            c = 0

            if not urls and not ctx.message.attachments:
                raise exc.MissingArgument

            for url in urls:
                try:
                    await dest.trigger_typing()

                    post = await scraper.get_post(url)

                    await dest.send('**Probable match:**\n{}'.format(await scraper.get_image(post)))

                    c += 1
                    await asyncio.sleep(self.RATE_LIMIT)

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)

            for attachment in ctx.message.attachments:
                try:
                    await dest.trigger_typing()

                    post = await scraper.get_post(attachment.url)

                    await dest.send('**Probable match:**\n{}'.format(await scraper.get_image(post)))

                    c += 1
                    await asyncio.sleep(self.RATE_LIMIT)

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)

            if c:
                await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            else:
                await ctx.message.add_reaction('\N{CROSS MARK}')

        except exc.MissingArgument:
            await ctx.send('**Invalid url or file.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @commands.command(name='reversify', aliases=['revify', 'risify', 'rify'])
    @checks.del_ctx()
    async def reversify(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args, limit=self.HISTORY_LIMIT / 5)
            dest, remove, limit = kwargs['destination'], kwargs['remove'], kwargs['limit']
            urls = []
            attachments = []

            if not ctx.author.permissions_in(ctx.channel).manage_messages:
                dest = ctx.author

            async for message in ctx.channel.history(limit=self.HISTORY_LIMIT * limit):
                if len(urls) + len(attachments) >= limit:
                    break
                if message.author.id != self.bot.user.id and re.search('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content) is not None:
                    urls.append(message)
                    await message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')
                elif message.author.id != self.bot.user.id and message.attachments:
                    attachments.append(message)
                    await message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

            if not urls and not attachments:
                raise exc.NotFound

            for message in urls:
                for match in re.finditer('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content):
                    try:
                        await dest.trigger_typing()

                        await dest.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_post(match.group(0))))
                        await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                        await asyncio.sleep(self.RATE_LIMIT)

                        if remove:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                        await message.add_reaction('\N{CROSS MARK}')

            for message in attachments:
                for attachment in message.attachments:
                    try:
                        await dest.trigger_typing()

                        await dest.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_post(attachment.url)))
                        await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                        await asyncio.sleep(self.RATE_LIMIT)

                        if remove:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                        await message.add_reaction('\N{CROSS MARK}')

            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.NotFound:
            await ctx.send('**No matches found.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.BoundsError as e:
            await ctx.send('`{}` **invalid limit.** Images limited to 20'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @commands.command(name='qualitify', aliases=['qualify', 'qrevify', 'qrisify', 'qify'])
    @checks.del_ctx()
    async def qualitify(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args, limit=self.HISTORY_LIMIT / 5)
            dest, remove, limit = kwargs['destination'], kwargs['remove'], kwargs['limit']
            urls = []
            attachments = []

            if not ctx.author.permissions_in(ctx.channel).manage_messages:
                dest = ctx.author

            async for message in ctx.channel.history(limit=self.HISTORY_LIMIT * limit):
                if len(urls) + len(attachments) >= limit:
                    break
                if message.author.id != self.bot.user.id and re.search('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content) is not None:
                    urls.append(message)
                    await message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')
                elif message.author.id != self.bot.user.id and message.attachments:
                    attachments.append(message)
                    await message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

            if not urls and not attachments:
                raise exc.NotFound

            for message in urls:
                for match in re.finditer('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content):
                    try:
                        await dest.trigger_typing()

                        post = await scraper.get_post(match.group(0))

                        await dest.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_image(post)))
                        await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                        await asyncio.sleep(self.RATE_LIMIT)

                        if remove:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                        await message.add_reaction('\N{CROSS MARK}')

            for message in attachments:
                for attachment in message.attachments:
                    try:
                        await dest.trigger_typing()

                        post = await scraper.get_post(attachment.url)

                        await dest.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_image(post)))
                        await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                        await asyncio.sleep(self.RATE_LIMIT)

                        if remove:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                        await message.add_reaction('\N{CROSS MARK}')

            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.NotFound:
            await ctx.send('**No matches found.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.BoundsError as e:
            await ctx.send('`{}` **invalid limit.** Images limited to 20'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    async def _qualitify(self):
        while self.qualitifying:
            message = await self.qualiqueue.get()

            for match in re.finditer('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content):
                try:
                    await message.channel.trigger_typing()

                    post = await scraper.get_post(match.group(0))

                    await message.channel.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_image(post)))
                    await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                    await asyncio.sleep(self.RATE_LIMIT)

                    with suppress(err.NotFound):
                        await message.delete()

                except exc.MatchError as e:
                    await message.channel.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                    await message.add_reaction('\N{CROSS MARK}')

            for attachment in message.attachments:
                try:
                    await message.channel.trigger_typing()

                    post = await scraper.get_post(attachment.url)

                    await message.channel.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_image(post)))
                    await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

                    await asyncio.sleep(self.RATE_LIMIT)

                    with suppress(err.NotFound):
                        await message.delete()

                except exc.MatchError as e:
                    await message.channel.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                    await message.add_reaction('\N{CROSS MARK}')

        print('STOPPED : qualitifying')

    async def queue_for_qualitification(self, channel):
        def check(msg):
            if msg.content.lower() == 'stop' and msg.channel is channel and msg.author.guild_permissions.administrator:
                raise exc.Abort
            elif msg.channel is channel and message.author.id != self.bot.user.id and (re.search('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', msg.content) is not None or msg.attachments):
                return True
            return False

        try:
            while not self.bot.is_closed():
                message = await self.bot.wait_for('message', check=check)
                await self.qualiqueue.put(message)
                await message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

        except exc.Abort:
            u.tasks['auto_qual'].remove(channel.id)
            u.dump(u.tasks, 'cogs/tasks.pkl')
            if not u.tasks['auto_qual']:
                self.qualitifying = False
            print('STOPPED : qualitifying #{}'.format(channel.name))
            await channel.send('**Stopped queueing messages for qualitification in** {}**.**'.format(channel.mention), delete_after=5)

    @commands.command(name='autoqualitify', aliases=['autoqual'])
    @commands.has_permissions(manage_channels=True)
    async def auto_qualitify(self, ctx):
        try:
            if ctx.channel.id not in u.tasks['auto_qual']:
                u.tasks['auto_qual'].append(ctx.channel.id)
                u.dump(u.tasks, 'cogs/tasks.pkl')
                self.bot.loop.create_task(self.qualiqueue_for_qualitification(ctx.channel))
                if not self.qualitifying:
                    self.bot.loop.create_task(self._qualitify())
                    self.qualitifying = True

                print('AUTO-QUALITIFYING : #{}'.format(ctx.channel.name))
                await ctx.send('**Auto-qualitifying all images in {}.**'.format(ctx.channel.mention), delete_after=5)
                await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            else:
                raise exc.Exists

        except exc.Exists:
            await ctx.send('**Already auto-qualitifying in {}.** Type `stop` to stop.'.format(ctx.channel.mention), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    def _get_favorites(self, ctx, args):
        if '-f' in args or '-favs' in args or '-faves' in args or '-favorites' in args:
            if self.favorites.get(ctx.author.id, {}).get('tags', set()):
                args = ['~{}'.format(tag) for tag in self.favorites[ctx.author.id]['tags']]
            else:
                raise exc.FavoritesNotFound

        return args

    async def _get_pool(self, ctx, *, booru='e621', query=[]):
        def on_message(msg):
            if msg.content.lower() == 'cancel' and msg.author is ctx.author and msg.channel is ctx.channel:
                raise exc.Abort
            elif msg.content.isdigit():
                if int(msg.content) <= len(pools) and int(msg.content) > 0 and msg.author is ctx.author and msg.channel is ctx.channel:
                    return True
            return False

        posts = {}
        pool = {}

        pools = []
        pool_request = await u.fetch('https://{}.net/pool/index.json'.format(booru), params={'query': ' '.join(query)}, json=True)
        if len(pool_request) > 1:
            for pool in pool_request:
                pools.append(pool['name'])
            match = await ctx.send('**Multiple pools found.** Type in the correct match.\n```\n{}```\nor `cancel` to cancel.'.format('\n'.join(['{} {}'.format(c, elem) for c, elem in enumerate(pools, 1)])))
            try:
                selection = await self.bot.wait_for('message', check=on_message, timeout=5 * 60)
            except exc.Abort:
                raise exc.Abort
            finally:
                await match.delete()
            tempool = [pool for pool in pool_request if pool['name']
                       == pools[int(selection.content) - 1]][0]
            await selection.delete()
            pool = {'name': tempool['name'], 'id': tempool['id']}
        elif pool_request:
            tempool = pool_request[0]
            pool = {'name': pool_request[0]['name'], 'id': pool_request[0]['id']}
        else:
            raise exc.NotFound

        page = 1
        while len(posts) < tempool['post_count']:
            posts_request = await u.fetch('https://{}.net/pool/show.json'.format(booru), params={'id': tempool['id'], 'page': page}, json=True)
            for post in posts_request['posts']:
                posts[post['id']] = {'author': post['author'], 'url': post['file_url']}
            page += 1

        return pool, posts

    # Creates reaction-based paginator for linked pools
    @commands.command(name='pool', aliases=['e6pp', '6pp'], brief='e621 pool paginator', description='e621 | NSFW\nShow pools in a page format', hidden=True)
    @checks.del_ctx()
    async def pool_paginator(self, ctx, *args):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and reaction.message.id == ctx.message.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Abort
            elif reaction.emoji == '\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}' and reaction.message.id == paginator.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.GoTo
            elif reaction.emoji == '\N{LEFTWARDS BLACK ARROW}' and reaction.message.id == paginator.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Left
            elif reaction.emoji == '\N{GROWING HEART}' and reaction.message.id == paginator.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Save
            elif reaction.emoji == '\N{BLACK RIGHTWARDS ARROW}' and reaction.message.id == paginator.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Right
            return False

        def on_message(msg):
            if msg.content.isdigit():
                if int(msg.content) <= len(posts) and msg.author is ctx.author and msg.channel is ctx.channel:
                    return True
            return False

        try:
            kwargs = u.get_kwargs(ctx, args)
            dest, query = kwargs['destination'], kwargs['remaining']
            starred = []
            c = 1

            await dest.trigger_typing()

            pool, posts = await self.return_pool(ctx, booru='e621', query=query)
            keys = list(posts.keys())
            values = list(posts.values())

            embed = d.Embed(
                title=values[c - 1]['author'], url='https://e621.net/post/show/{}'.format(keys[c - 1]), color=dest.me.color if isinstance(dest.channel, d.TextChannel) else self.color)
            embed.set_image(url=values[c - 1]['url'])
            embed.set_author(name=pool['name'],
                             url='https://e621.net/pool/show?id={}'.format(pool['id']), icon_url=ctx.author.avatar_url)
            embed.set_footer(text='{} / {}'.format(c, len(posts)),
                             icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')

            paginator = await dest.send(embed=embed)

            for emoji in ('\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}', '\N{LEFTWARDS BLACK ARROW}', '\N{GROWING HEART}', '\N{BLACK RIGHTWARDS ARROW}'):
                await paginator.add_reaction(emoji)
            await ctx.message.add_reaction('\N{OCTAGONAL SIGN}')
            await asyncio.sleep(1)

            while not self.bot.is_closed():
                try:
                    done, pending = await asyncio.wait([self.bot.wait_for('reaction_add', check=on_reaction, timeout=10 * 60),
                                                        self.bot.wait_for('reaction_remove', check=on_reaction, timeout=10 * 60)], return_when=asyncio.FIRST_COMPLETED)
                    for future in done:
                        future.result()

                except exc.GoTo:
                    await paginator.edit(content='**Enter image number...**')
                    number = await self.bot.wait_for('message', check=on_message, timeout=10 * 60)

                    c = int(number.content)
                    await number.delete()
                    embed.title = values[c - 1]['author']
                    embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                    embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                     icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                    embed.set_image(url=values[c - 1]['url'])

                    await paginator.edit(content='\N{HEAVY BLACK HEART}' if values[c - 1]['url'] in starred else None, embed=embed)

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                        embed.set_image(url=values[c - 1]['url'])

                        await paginator.edit(content='\N{HEAVY BLACK HEART}' if values[c - 1]['url'] in starred else None, embed=embed)
                    else:
                        await paginator.edit(content='**First image.**')

                except exc.Save:
                    if values[c - 1]['url'] not in starred:
                        starred.append(values[c - 1]['url'])

                        await paginator.edit(content='\N{HEAVY BLACK HEART}')
                    else:
                        starred.remove(values[c - 1]['url'])

                        await paginator.edit(content='\N{BROKEN HEART}')

                except exc.Right:
                    if c < len(keys):
                        c += 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                        embed.set_image(url=values[c - 1]['url'])

                        await paginator.edit(content='\N{HEAVY BLACK HEART}' if values[c - 1]['url'] in starred else None, embed=embed)

        except exc.Abort:
            try:
                await paginator.edit(content='**Exited paginator.**')

            except UnboundLocalError:
                await dest.send('**Exited paginator.**')
        except asyncio.TimeoutError:
            try:
                await paginator.edit(content='**Paginator timed out.**')

            except UnboundLocalError:
                await dest.send('**Paginator timed out.**')
        except exc.NotFound:
            await ctx.send('**Pool not found.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out.**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

        finally:
            if starred:
                await ctx.message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

                for url in starred:
                    await ctx.author.send('`{} / {}`\n{}'.format(starred.index(url) + 1, len(starred), url))
                    if len(starred) > 5:
                        await asyncio.sleep(self.RATE_LIMIT)

            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    # Messy code that checks image limit and tags in blacklists
    async def check_return_posts(self, ctx, *, booru='e621', tags=[], limit=1, previous={}):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        blacklist = set()
        # Creates temp blacklist based on context
        for tag in self.blacklists['global_blacklist']:
            blacklist.update(list(self.aliases[tag]) + [tag])
        for tag in self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()):
            blacklist.update(list(self.aliases[tag]) + [tag])
        for tag in self.blacklists['user_blacklist'].get(ctx.author.id, set()):
            blacklist.update(list(self.aliases[tag]) + [tag])
        # Checks if tags are in local blacklists
        if tags:
            if (len(tags) > 5 and booru == 'e621') or (len(tags) > 4 and booru == 'e926'):
                raise exc.TagBoundsError(formatter.tostring(tags[5:]))
            for tag in tags:
                if tag == 'swf' or tag == 'webm' or tag in blacklist:
                    raise exc.TagBlacklisted(tag)

        # Checks for blacklisted tags in endpoint blacklists - try/except is for continuing the parent loop
        posts = {}
        c = 0
        while len(posts) < limit:
            if c == limit * 5 + self.LIMIT:
                raise exc.Timeout
            request = await u.fetch('https://{}.net/post/index.json'.format(booru), params={'tags': ','.join(['order:random'] + tags), 'limit': int(self.LIMIT * limit)}, json=True)
            if len(request) == 0:
                raise exc.NotFound(formatter.tostring(tags))
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
                    posts[post['id']] = {'author': post['author'], 'url': post['file_url']}
                if len(posts) == limit:
                    break
            c += 1

        return posts

    @commands.command(name='e621p', aliases=['e6p', '6p'])
    @checks.del_ctx()
    @checks.is_nsfw()
    async def e621_paginator(self, ctx, *args):
        def on_reaction(reaction, user):
            if reaction.emoji == '\N{OCTAGONAL SIGN}' and reaction.message.id == ctx.message.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Abort
            elif reaction.emoji == '\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}' and reaction.message.id == paginator.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.GoTo
            elif reaction.emoji == '\N{LEFTWARDS BLACK ARROW}' and reaction.message.id == paginator.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Left
            elif reaction.emoji == '\N{GROWING HEART}' and reaction.message.id == paginator.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Save
            elif reaction.emoji == '\N{BLACK RIGHTWARDS ARROW}' and reaction.message.id == paginator.id and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Right
            return False

        def on_message(msg):
            if msg.content.isdigit():
                if int(msg.content) <= len(posts) and msg.author is ctx.author and msg.channel is ctx.channel:
                    return True
            return False

        try:
            kwargs = u.get_kwargs(ctx, args)
            dest, tags = kwargs['destination'], kwargs['remaining']
            limit = self.LIMIT / 5
            starred = []
            c = 1

            tags = self.get_favorites(ctx, tags)

            await ctx.trigger_typing()

            posts = await self.check_return_posts(ctx, booru='e621', tags=tags, limit=limit)
            keys = list(posts.keys())
            values = list(posts.values())

            embed = d.Embed(
                title=values[c - 1]['author'], url='https://e621.net/post/show/{}'.format(keys[c - 1]), color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else self.color)
            embed.set_image(url=values[c - 1]['url'])
            embed.set_author(name=formatter.tostring(tags, random=True),
                             url='https://e621.net/post?tags={}'.format(','.join(tags)), icon_url=ctx.author.avatar_url)
            embed.set_footer(text='{} / {}'.format(c, len(posts)),
                             icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')

            paginator = await dest.send(embed=embed)

            for emoji in ('\N{NUMBER SIGN}\N{COMBINING ENCLOSING KEYCAP}', '\N{LEFTWARDS BLACK ARROW}', '\N{GROWING HEART}', '\N{BLACK RIGHTWARDS ARROW}'):
                await paginator.add_reaction(emoji)
            await ctx.message.add_reaction('\N{OCTAGONAL SIGN}')
            await asyncio.sleep(1)

            while not self.bot.is_closed():
                try:
                    done, pending = await asyncio.wait([self.bot.wait_for('reaction_add', check=on_reaction, timeout=10 * 60),
                                                        self.bot.wait_for('reaction_remove', check=on_reaction, timeout=10 * 60)], return_when=asyncio.FIRST_COMPLETED)
                    for future in done:
                        future.result()

                except exc.GoTo:
                    await paginator.edit(content='**Enter image number...**')
                    number = await self.bot.wait_for('message', check=on_message, timeout=10 * 60)

                    c = int(number.content)
                    await number.delete()
                    embed.title = values[c - 1]['author']
                    embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                    embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                     icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                    embed.set_image(url=values[c - 1]['url'])

                    await paginator.edit(content='\N{HEAVY BLACK HEART}' if values[c - 1]['url'] in starred else None, embed=embed)

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                        embed.set_image(url=values[c - 1]['url'])
                        await paginator.edit(content='\N{HEAVY BLACK HEART}' if values[c - 1]['url'] in starred else None, embed=embed)
                    else:
                        await paginator.edit(content='**First image.**')

                except exc.Save:
                    if values[c - 1]['url'] not in starred:
                        starred.append(values[c - 1]['url'])

                        await paginator.edit(content='\N{HEAVY BLACK HEART}')
                    else:
                        starred.remove(values[c - 1]['url'])

                        await paginator.edit(content='\N{BROKEN HEART}')

                except exc.Right:
                    if c % limit == 0:
                        await dest.trigger_typing()
                        try:
                            posts.update(await self.check_return_posts(ctx, booru='e621', tags=tags, limit=limit, previous=posts))

                        except exc.NotFound:
                            await paginator.edit(content='**No more images found.**')

                        keys = list(posts.keys())
                        values = list(posts.values())

                    c += 1
                    embed.title = values[c - 1]['author']
                    embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                    embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                     icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                    embed.set_image(url=values[c - 1]['url'])
                    await paginator.edit(content='\N{HEAVY BLACK HEART}' if values[c - 1]['url'] in starred else None, embed=embed)

        except exc.Abort:
            try:
                await paginator.edit(content='**Exited paginator.**')

            except UnboundLocalError:
                await dest.send('**Exited paginator.**')
        except asyncio.TimeoutError:
            try:
                await paginator.edit(content='**Paginator timed out.**')

            except UnboundLocalError:
                await dest.send('**Paginator timed out.**')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBlacklisted as e:
            await ctx.send('\N{NO ENTRY SIGN} `{}` **blacklisted.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{NO ENTRY SIGN}')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5, currently.'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out.**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

        finally:
            if starred:
                await ctx.message.add_reaction('\N{HOURGLASS WITH FLOWING SAND}')

                for url in starred:
                    await ctx.author.send('`{} / {}`\n{}'.format(starred.index(url) + 1, len(starred), url))
                    if len(starred) > 5:
                        await asyncio.sleep(self.RATE_LIMIT)

            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @e621_paginator.error
    async def e621_paginator_error(self, ctx, error):
        if isinstance(error, errext.CheckFailure):
            await ctx.send('\N{NO ENTRY} {} **is not an NSFW channel.**'.format(ctx.channel.mention), delete_after=10)
            return await ctx.message.add_reaction('\N{NO ENTRY}')

    # Searches for and returns images from e621.net given tags when not blacklisted
    @commands.group(aliases=['e6', '6'], brief='e621 | NSFW', description='e621 | NSFW\nTag-based search for e621.net\n\nYou can only search 5 tags and 6 images at once for now.\ne6 [tags...] ([# of images])')
    @checks.del_ctx()
    @checks.is_nsfw()
    async def e621(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args, limit=3)
            dest, args, limit = kwargs['destination'], kwargs['remaining'], kwargs['limit']

            tags = self.get_favorites(ctx, args)

            await dest.trigger_typing()

            posts = await self.check_return_posts(ctx, booru='e621', tags=tags, limit=limit)

            for ident, post in posts.items():
                embed = d.Embed(title=post['author'], url='https://e621.net/post/show/{}'.format(ident),
                                color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else self.color).set_image(url=post['url'])
                embed.set_author(name=formatter.tostring(tags, random=True),
                                 url='https://e621.net/post?tags={}'.format(','.join(tags)), icon_url=ctx.author.avatar_url)
                embed.set_footer(
                    text=str(ident), icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')

                await dest.send(embed=embed)

            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.TagBlacklisted as e:
            await ctx.send('`{}` **blacklisted.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.BoundsError as e:
            await ctx.send('`{}` **out of bounds.** Images limited to 3.'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5.'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out.**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

        # tools.command_dict.setdefault(str(ctx.author.id), {}).update(
        #     {'command': ctx.command, 'args': ctx.args})

    @e621.error
    async def e621_error(self, ctx, error):
        if isinstance(error, errext.CheckFailure):
            await ctx.send('\N{NO ENTRY} {} **is not an NSFW channel.**'.format(ctx.channel.mention), delete_after=10)
            return await ctx.message.add_reaction('\N{NO ENTRY}')

    # Searches for and returns images from e926.net given tags when not blacklisted
    @commands.command(aliases=['e9', '9'], brief='e926 | SFW', description='e926 | SFW\nTag-based search for e926.net\n\nYou can only search 5 tags and 6 images at once for now.\ne9 [tags...] ([# of images])')
    @checks.del_ctx()
    async def e926(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args, limit=3)
            dest, args, limit = kwargs['destination'], kwargs['remaining'], kwargs['limit']

            tags = self.get_favorites(ctx, args)

            await dest.trigger_typing()

            posts = await self.check_return_posts(ctx, booru='e926', tags=tags, limit=limit)

            for ident, post in posts.items():
                embed = d.Embed(title=post['author'], url='https://e926.net/post/show/{}'.format(ident),
                                color=ctx.me.color if isinstance(ctx.channel, d.TextChannel) else self.color).set_image(url=post['url'])
                embed.set_author(name=formatter.tostring(tags, random=True),
                                 url='https://e621.net/post?tags={}'.format(','.join(tags)), icon_url=ctx.author.avatar_url)
                embed.set_footer(
                    text=str(ident), icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')

                await dest.send(embed=embed)

            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.TagBlacklisted as e:
            await ctx.send('`{}` **blacklisted.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.BoundsError as e:
            await ctx.send('`{}` **out of bounds.** Images limited to 3.'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5.'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.Timeout:
            await ctx.send('**Request timed out.**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @commands.group(aliases=['fave', 'fav', 'f'])
    @checks.del_ctx()
    async def favorite(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Use a flag to manage favorites.**\n*Type* `{}help fav` *for more info.*'.format(ctx.prefix), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @favorite.error
    async def favorite_error(self, ctx, error):
        pass

    @favorite.group(name='get', aliases=['g'])
    async def _get_favorite(self, ctx):
        pass

    @_get_favorite.command(name='tags', aliases=['t'])
    async def __get_favorite_tags(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        await dest.send('\N{WHITE MEDIUM STAR} {}**\'s favorite tags:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(self.favorites.get(ctx.author.id, {}).get('tags', set()))), delete_after=10)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

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
            dest, tags = kwargs['destination'], kwargs['remaining']

            for tag in tags:
                if tag in self.blacklists['user_blacklist'].get(ctx.author.id, set()):
                    raise exc.TagBlacklisted(tag)
            if len(self.favorites[ctx.author.id]['tags']) + len(tags) > 5:
                raise exc.BoundsError

            self.favorites.setdefault(ctx.author.id, {}).setdefault('tags', set()).update(tags)
            u.dump(self.favorites, 'cogs/favorites.pkl')

            await dest.send('{} **added to their favorites:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(tags)), delete_after=5)
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.BoundsError:
            await ctx.send('**Favorites list currently limited to:** `5`', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')
        except exc.TagBlacklisted as e:
            await ctx.send('\N{NO ENTRY SIGN} `{}` **blacklisted.**', delete_after=10)
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
            dest, tags = kwargs['destination'], kwargs['remaining']

            for tag in tags:
                try:
                    self.favorites[ctx.author.id].get('tags', set()).remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.favorites, 'cogs/favorites.pkl')

            await dest.send('{} **removed from their favorites:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(tags)), delete_after=5)
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.TagError as e:
            await ctx.send('`{}` **not in favorites.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_remove_favorite.command(name='posts', aliases=['p'])
    async def __remove_favorite_posts(self, ctx):
        pass

    @favorite.group(name='clear', aliases=['c'])
    async def _clear_favorite(self, ctx):
        pass

    @_clear_favorite.command(name='tags', aliases=['t'])
    async def __clear_favorite_tags(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        with suppress(KeyError):
            del self.favorites[ctx.author.id]
            u.dump(self.favorites, 'cogs/favorites.pkl')

        await dest.send('{}**\'s favorites cleared.**'.format(ctx.author.mention), delete_after=5)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_clear_favorite.command(name='posts', aliases=['p'])
    async def __clear_favorite_posts(self, ctx):
        pass

    # Umbrella command structure to manage global, channel, and user blacklists
    @commands.group(aliases=['bl', 'b'], brief='Manage blacklists', description='Blacklist base command for managing blacklists\n\n`bl get [blacklist]` to show a blacklist\n`bl set [blacklist] [tags]` to replace a blacklist\n`bl clear [blacklist]` to clear a blacklist\n`bl add [blacklist] [tags]` to add tags to a blacklist\n`bl remove [blacklist] [tags]` to remove tags from a blacklist', usage='[flag] [blacklist] ([tags])')
    @checks.del_ctx()
    async def blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Use a flag to manage blacklists.**\n*Type* `{}help bl` *for more info.*'.format(ctx.prefix), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    # @blacklist.error
    # async def blacklist_error(self, ctx, error):
        # if isinstance(error, KeyError):
        #     return await ctx.send('**Blacklist does not exist.**', delete_after=10)

    @blacklist.group(name='get', aliases=['g'])
    async def _get_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_get_blacklist.command(name='global', aliases=['gl', 'g'])
    async def __get_global_blacklist(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        await dest.send('\N{NO ENTRY SIGN} **Global blacklist:**\n```\n{}```'.format(formatter.tostring(self.blacklists['global_blacklist'])))
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_get_blacklist.command(name='channel', aliases=['ch', 'c'])
    async def __get_channel_blacklist(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await dest.send('\N{NO ENTRY SIGN} {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, formatter.tostring(self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()))))
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_get_blacklist.command(name='me', aliases=['m'])
    async def __get_user_blacklist(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        await dest.send('\N{NO ENTRY SIGN} {}**\'s blacklist:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(self.blacklists['user_blacklist'].get(ctx.author.id, set()))), delete_after=10)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_get_blacklist.command(name='here', aliases=['h'])
    async def __get_here_blacklists(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await dest.send('\N{NO ENTRY SIGN} **__Blacklisted:__**\n\n**Global:**\n```\n{}```\n**{}:**\n```\n{}```'.format(formatter.tostring(self.blacklists['global_blacklist']), ctx.channel.mention, formatter.tostring(self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()))))
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_get_blacklist.group(name='all', aliases=['a'])
    async def __get_all_blacklists(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**')
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @__get_all_blacklists.command(name='guild', aliases=['g'])
    @commands.has_permissions(manage_channels=True)
    async def ___get_all_guild_blacklists(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await dest.send('\N{NO ENTRY SIGN} **__{} blacklists:__**\n\n{}'.format(guild.name, formatter.dict_tostring(self.blacklists['guild_blacklist'].get(guild.id, {}))))
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @__get_all_blacklists.command(name='user', aliases=['u', 'member', 'm'])
    @commands.is_owner()
    async def ___get_all_user_blacklists(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        await dest.send('\N{NO ENTRY SIGN} **__User blacklists:__**\n\n{}'.format(formatter.dict_tostring(self.blacklists['user_blacklist'])))
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @blacklist.group(name='add', aliases=['a'])
    async def _add_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_add_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __add_global_tags(self, ctx, *args):
        kwargs = u.get_kwargs(ctx, args)
        dest, tags = kwargs['destination'], kwargs['remaining']

        await dest.trigger_typing()

        self.blacklists['global_blacklist'].update(tags)
        for tag in tags:
            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            if alias_request:
                for dic in alias_request:
                    self.aliases.setdefault(tag, set()).add(dic['name'])
            else:
                self.aliases.setdefault(tag, set())
        u.dump(self.blacklists, 'cogs/blacklists.pkl')
        u.dump(self.aliases, 'cogs/aliases.pkl')

        await dest.send('**Added to global blacklist:**\n```\n{}```'.format(formatter.tostring(tags)), delete_after=5)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_add_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __add_channel_tags(self, ctx, *args):
        kwargs = u.get_kwargs(ctx, args)
        dest, tags = kwargs['destination'], kwargs['remaining']

        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await dest.trigger_typing()

        self.blacklists['guild_blacklist'].setdefault(
            guild.id, {}).setdefault(ctx.channel.id, set()).update(tags)
        for tag in tags:
            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            if alias_request:
                for dic in alias_request:
                    self.aliases.setdefault(tag, set()).add(dic['name'])
            else:
                self.aliases.setdefault(tag, set())
        u.dump(self.blacklists, 'cogs/blacklists.pkl')
        u.dump(self.aliases, 'cogs/aliases.pkl')

        await dest.send('**Added to** {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, formatter.tostring(tags)), delete_after=5)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_add_tags.command(name='me', aliases=['m'])
    async def __add_user_tags(self, ctx, *args):
        kwargs = u.get_kwargs(ctx, args)
        dest, tags = kwargs['destination'], kwargs['remaining']

        await dest.trigger_typing()

        self.blacklists['user_blacklist'].setdefault(ctx.author.id, set()).update(tags)
        for tag in tags:
            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            if alias_request:
                for dic in alias_request:
                    self.aliases.setdefault(tag, set()).add(dic['name'])
            else:
                self.aliases.setdefault(tag, set())
        u.dump(self.blacklists, 'cogs/blacklists.pkl')
        u.dump(self.aliases, 'cogs/aliases.pkl')

        await dest.send('{} **added to their blacklist:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(tags)), delete_after=5)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @blacklist.group(name='remove', aliases=['rm', 'r'])
    async def _remove_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_remove_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __remove_global_tags(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            dest, tags = kwargs['destination'], kwargs['remaining']

            for tag in tags:
                try:
                    self.blacklists['global_blacklist'].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await dest.send('**Removed from global blacklist:**\n```\n{}```'.format(formatter.tostring(tags)), delete_after=5)
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_remove_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __remove_channel_tags(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            dest, tags = kwargs['destination'], kwargs['remaining']

            guild = ctx.guild if isinstance(
                ctx.guild, d.Guild) else ctx.channel

            for tag in tags:
                try:
                    self.blacklists['guild_blacklist'][guild.id][ctx.channel.id].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await dest.send('**Removed from** {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, formatter.tostring(tags), delete_after=5))
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_remove_tags.command(name='me', aliases=['m'])
    async def __remove_user_tags(self, ctx, *args):
        try:
            kwargs = u.get_kwargs(ctx, args)
            dest, tags = kwargs['destination'], kwargs['remaining']

            for tag in tags:
                try:
                    self.blacklists['user_blacklist'][ctx.author.id].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await dest.send('{} **removed from their blacklist:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(tags)), delete_after=5)
            await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @blacklist.group(name='clear', aliases=['cl', 'c'])
    async def _clear_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**', delete_after=10)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @_clear_blacklist.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __clear_global_blacklist(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        self.blacklists['global_blacklist'].clear()
        u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await dest.send('**Global blacklist cleared.**', delete_after=5)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_clear_blacklist.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __clear_channel_blacklist(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        with suppress(KeyError):
            del self.blacklists['guild_blacklist'][guild.id][ctx.channel.id]
            u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await dest.send('{} **blacklist cleared.**'.format(ctx.channel.mention), delete_after=5)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    @_clear_blacklist.command(name='me', aliases=['m'])
    async def __clear_user_blacklist(self, ctx, *args):
        dest = u.get_kwargs(ctx, args)['destination']

        with suppress(KeyError):
            del self.blacklists['user_blacklist'][ctx.author.id]
            u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await dest.send('{}**\'s blacklist cleared.**'.format(ctx.author.mention), delete_after=5)
        await ctx.message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
