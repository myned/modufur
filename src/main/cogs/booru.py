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
        self.LIMIT = 100
        self.RATE_LIMIT = u.RATE_LIMIT
        self.queue = asyncio.Queue()
        self.qualitifying = False

        self.favorites = u.setdefault('cogs/favorites.pkl', {'tags': set(), 'posts': set()})
        self.blacklists = u.setdefault(
            'cogs/blacklists.pkl', {'global_blacklist': set(), 'guild_blacklist': {}, 'user_blacklist': {}})
        self.aliases = u.setdefault('cogs/aliases.pkl', {})

        if u.tasks['auto_qual']:
            for channel in u.tasks['auto_qual']:
                temp = self.bot.get_channel(channel)
                self.bot.loop.create_task(self.queue_for_qualitification(temp))
                print('AUTO-QUALITIFYING : #{}'.format(temp.name))
            self.bot.loop.create_task(self._qualitify())
            self.qualitifying = True

    # Tag search
    @commands.command(aliases=['rel'], brief='e621 Related tag search', description='e621 | NSFW\nReturn a link search for given tags')
    @checks.del_ctx()
    async def related(self, ctx, tag=None):
        related = []

        try:
            if tag is None:
                raise exc.MissingArgument

            await ctx.trigger_typing()

            tag_request = await u.fetch('https://e621.net/tag/related.json', params={'tags': tag, 'type': 'general'}, json=True)
            for rel in tag_request.get(tag, []):
                related.append(rel[0])

            await ctx.send('`{}` **related tags:**\n```\n{}```'.format(tag, formatter.tostring(related)))
            await ctx.message.add_reaction('✅')

        except exc.MissingArgument:
            await ctx.send('**No tags given.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    # Tag aliases
    @commands.command(name='aliases', aliases=['alias'], brief='e621 Tag aliases', description='e621 | NSFW\nSearch aliases for given tag')
    @checks.del_ctx()
    async def tag_aliases(self, ctx, tag=None):
        aliases = []

        try:
            if tag is None:
                raise exc.MissingArgument

            await ctx.trigger_typing()

            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            for dic in alias_request:
                aliases.append(dic['name'])

            await ctx.send('`{}` **aliases:**\n```\n{}```'.format(tag, formatter.tostring(aliases)))
            await ctx.message.add_reaction('✅')

        except exc.MissingArgument:
            await ctx.send('**No tags given.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    @commands.command(name='getimage', aliases=['geti', 'gi'])
    @checks.del_ctx()
    async def get_image(self, ctx, *urls):
        try:
            if not urls:
                raise exc.MissingArgument

            for url in urls:
                try:
                    await ctx.trigger_typing()

                    await ctx.send('{}'.format(await scraper.get_image(url)))

                finally:
                    await asyncio.sleep(self.RATE_LIMIT)

            await ctx.message.add_reaction('✅')

        except exc.MissingArgument:
            await ctx.send('**Invalid url or file.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    # Reverse image searches a linked image using the public iqdb
    @commands.command(name='reverse', aliases=['rev', 'ris'], brief='e621 Reverse image search', description='e621 | NSFW\nReverse-search an image with given URL')
    @checks.del_ctx()
    async def reverse_image_search(self, ctx, *urls):
        try:
            if not urls and not ctx.message.attachments:
                raise exc.MissingArgument

            for url in urls:
                try:
                    await ctx.trigger_typing()

                    await ctx.send('**Probable match:**\n{}'.format(await scraper.get_post(url)))

                    await asyncio.sleep(self.RATE_LIMIT)

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)

            for attachment in ctx.message.attachments:
                try:
                    await ctx.trigger_typing()

                    await ctx.send('**Probable match:**\n{}'.format(await scraper.get_post(attachment.url)))

                    await asyncio.sleep(self.RATE_LIMIT)

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)

            await ctx.message.add_reaction('✅')

        except exc.MissingArgument:
            await ctx.send('**Invalid url or file.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    @commands.command(name='reversify', aliases=['revify', 'risify', 'rify'])
    @checks.del_ctx()
    @commands.has_permissions(manage_messages=True)
    async def reversify(self, ctx, arg=None, limit=1):
        urls = []
        attachments = []
        delete = False

        try:
            await ctx.message.add_reaction('✅')

            if arg == '-d' or arg == '-del' or arg == '-delete':
                delete = True
            elif arg is not None:
                limit = int(arg)

            async for message in ctx.channel.history(limit=limit + 1):
                if message.author.id != self.bot.user.id and re.search('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content) is not None:
                    urls.append(message)
                    await message.add_reaction('⏳')
                elif message.author.id != self.bot.user.id and message.attachments:
                    attachments.append(message)
                    await message.add_reaction('⏳')

            if not urls and not attachments:
                raise exc.NotFound

            for message in urls:
                for match in re.finditer('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content):
                    try:
                        await ctx.trigger_typing()

                        await ctx.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_post(match.group(0))))
                        await message.add_reaction('✅')

                        await asyncio.sleep(self.RATE_LIMIT)

                        if delete:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                        await message.add_reaction('❌')

            for message in attachments:
                for attachment in message.attachments:
                    try:
                        await ctx.trigger_typing()

                        await ctx.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_post(attachment.url)))
                        await message.add_reaction('✅')

                        await asyncio.sleep(self.RATE_LIMIT)

                        if delete:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                        await message.add_reaction('❌')

        except exc.NotFound:
            await ctx.send('**No matches found.**', delete_after=10)
            await ctx.message.add_reaction('❌')
        except ValueError:
            await ctx.send('**Invalid limit.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    @commands.command(name='quality', aliases=['qual', 'qrev', 'qis'])
    @checks.del_ctx()
    async def quality_reverse_image_search(self, ctx, *urls):
        try:
            if not urls and not ctx.message.attachments:
                raise exc.MissingArgument

            await ctx.message.add_reaction('✅')

            for url in urls:
                try:
                    await ctx.trigger_typing()

                    post = await scraper.get_post(url)

                    await ctx.send('**Probable match:**\n{}'.format(await scraper.get_image(post)))

                    await asyncio.sleep(self.RATE_LIMIT)

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)

            for attachment in ctx.message.attachments:
                try:
                    await ctx.trigger_typing()

                    post = await scraper.get_post(attachment.url)

                    await ctx.send('**Probable match:**\n{}'.format(await scraper.get_image(post)))

                    await asyncio.sleep(self.RATE_LIMIT)

                except exc.MatchError as e:
                    await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)

        except exc.MissingArgument:
            await ctx.send('**Invalid url or file.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    @commands.command(name='qualitify', aliases=['qualify', 'qrevify', 'qrisify', 'qify'])
    @checks.del_ctx()
    @commands.has_permissions(manage_messages=True)
    async def qualitify(self, ctx, arg=None, limit=1):
        urls = []
        attachments = []
        delete = False

        await ctx.message.add_reaction('✅')

        try:
            if arg == '-d' or arg == '-del' or arg == '-delete':
                delete = True
            elif arg is not None:
                limit = int(arg)

            async for message in ctx.channel.history(limit=limit + 1):
                if message.author.id != self.bot.user.id and re.search('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content) is not None:
                    urls.append(message)
                    await message.add_reaction('⏳')
                elif message.author.id != self.bot.user.id and message.attachments:
                    attachments.append(message)
                    await message.add_reaction('⏳')

            if not urls and not attachments:
                raise exc.NotFound

            for message in urls:
                for match in re.finditer('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content):
                    try:
                        await ctx.trigger_typing()

                        post = await scraper.get_post(match.group(0))

                        await ctx.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_image(post)))
                        await message.add_reaction('✅')

                        await asyncio.sleep(self.RATE_LIMIT)

                        if delete:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                        await message.add_reaction('❌')

            for message in attachments:
                for attachment in message.attachments:
                    try:
                        await ctx.trigger_typing()

                        post = await scraper.get_post(attachment.url)

                        await ctx.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_image(post)))
                        await message.add_reaction('✅')

                        await asyncio.sleep(self.RATE_LIMIT)

                        if delete:
                            with suppress(err.NotFound):
                                await message.delete()

                    except exc.MatchError as e:
                        await ctx.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                        await message.add_reaction('❌')

        except exc.NotFound:
            await ctx.send('**No matches found.**', delete_after=10)
            await ctx.message.add_reaction('❌')
        except ValueError:
            await ctx.send('**Invalid limit.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    async def _qualitify(self):
        while self.qualitifying:
            message = await self.queue.get()

            for match in re.finditer('(http[a-z]?:\/\/[^ ]*\.(?:gif|png|jpg|jpeg))', message.content):
                try:
                    await message.channel.trigger_typing()

                    post = await scraper.get_post(match.group(0))

                    await message.channel.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_image(post)))
                    await message.add_reaction('✅')

                    await asyncio.sleep(self.RATE_LIMIT)

                    with suppress(err.NotFound):
                        await message.delete()

                except exc.MatchError as e:
                    await message.channel.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                    await message.add_reaction('❌')

            for attachment in message.attachments:
                try:
                    await message.channel.trigger_typing()

                    post = await scraper.get_post(attachment.url)

                    await message.channel.send('**Probable match from** {}**:**\n{}'.format(message.author.display_name, await scraper.get_image(post)))
                    await message.add_reaction('✅')

                    await asyncio.sleep(self.RATE_LIMIT)

                    with suppress(err.NotFound):
                        await message.delete()

                except exc.MatchError as e:
                    await message.channel.send('**No probable match for:** `{}`'.format(e), delete_after=10)
                    await message.add_reaction('❌')

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
                await self.queue.put(message)
                await message.add_reaction('⏳')

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
                self.bot.loop.create_task(self.queue_for_qualitification(ctx.channel))
                if not self.qualitifying:
                    self.bot.loop.create_task(self._qualitify())
                    self.qualitifying = True

                print('AUTO-QUALITIFYING : #{}'.format(ctx.channel.name))
                await ctx.send('**Auto-qualitifying all images in {}.**'.format(ctx.channel.mention), delete_after=5)
                await ctx.message.add_reaction('✅')
            else:
                raise exc.Exists

        except exc.Exists:
            await ctx.send('**Already auto-qualitifying in {}.** Type `stop` to stop.'.format(ctx.channel.mention), delete_after=10)
            await ctx.message.add_reaction('❌')

    def get_favorites(self, ctx, args):
        if '-f' in args or '-favs' in args or '-faves' in args or '-favorites' in args:
            if self.favorites.get(ctx.author.id, {}).get('tags', set()):
                args = ['~{}'.format(tag) for tag in self.favorites[ctx.author.id]['tags']]
            else:
                raise exc.FavoritesNotFound

        return args

    async def return_pool(self, *, ctx, booru='e621', query=[]):
        def on_message(msg):
            if msg.content.lower() == 'cancel' and msg.author is ctx.author and msg.channel is ctx.channel:
                raise exc.Abort
            with suppress(ValueError):
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
                selection = await self.bot.wait_for('message', check=on_message, timeout=10 * 60)
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
    @commands.command(name='pool', aliases=['e6pp'], brief='e621 pool paginator', description='e621 | NSFW\nShow pools in a page format', hidden=True)
    @checks.del_ctx()
    async def pool_paginator(self, ctx, *kwords):
        def on_reaction(reaction, user):
            if reaction.emoji == '🚫' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Abort
            elif reaction.emoji == '📁' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Save
            elif reaction.emoji == '⬅' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Left
            elif reaction.emoji == '🔢' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.GoTo
            elif reaction.emoji == '➡' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Right
            return False

        def on_message(msg):
            with suppress(ValueError):
                if int(msg.content) <= len(posts) and msg.author is ctx.author and msg.channel is ctx.channel:
                    return True
            return False

        starred = []
        c = 1

        try:
            await ctx.trigger_typing()

            pool, posts = await self.return_pool(ctx=ctx, booru='e621', query=kwords)
            keys = list(posts.keys())
            values = list(posts.values())

            embed = d.Embed(
                title=values[c - 1]['author'], url='https://e621.net/post/show/{}'.format(keys[c - 1]), color=ctx.me.color).set_image(url=values[c - 1]['url'])
            embed.set_author(name=pool['name'],
                             url='https://e621.net/pool/show?id={}'.format(pool['id']), icon_url=ctx.author.avatar_url)
            embed.set_footer(text='{} / {}'.format(c, len(posts)),
                             icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')

            paginator = await ctx.send(embed=embed)

            await paginator.add_reaction('🚫')
            await paginator.add_reaction('📁')
            await paginator.add_reaction('⬅')
            await paginator.add_reaction('🔢')
            await paginator.add_reaction('➡')
            await asyncio.sleep(1)
            await ctx.message.add_reaction('✅')

            while not self.bot.is_closed():
                try:
                    await self.bot.wait_for('reaction_add', check=on_reaction, timeout=10 * 60)

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                        embed.set_image(url=values[c - 1]['url'])

                        await paginator.edit(content=None, embed=embed)
                    else:
                        await paginator.edit(content='**First image.**')

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

                    await paginator.edit(content=None, embed=embed)

                except exc.Save:
                    if values[c - 1]['url'] not in starred:
                        starred.append(values[c - 1]['url'])

                        await paginator.edit(content='**Image** `{}` **saved.**'.format(len(starred)))
                    else:
                        starred.remove(values[c - 1])['url']

                        await paginator.edit(content='**Image removed.**')

                except exc.Right:
                    if c < len(keys):
                        c += 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                        embed.set_image(url=values[c - 1]['url'])

                        await paginator.edit(content=None, embed=embed)

        except exc.Abort:
            try:
                await paginator.edit(content='🚫 **Exited paginator.**')

            except UnboundLocalError:
                await ctx.send('🚫 **Exited paginator.**')
            await ctx.message.add_reaction('🚫')
        except asyncio.TimeoutError:
            try:
                await paginator.edit(content='**Paginator timed out.**')

            except UnboundLocalError:
                await ctx.send('**Paginator timed out.**')
            await ctx.message.add_reaction('❌')
        except exc.NotFound:
            await ctx.send('**Pool not found.**', delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.Timeout:
            await ctx.send('**Request timed out.**')
            await ctx.message.add_reaction('❌')

        finally:
            for url in starred:
                await ctx.author.send(url)
                if len(starred) > 5:
                    await asyncio.sleep(self.RATE_LIMIT)

    # Messy code that checks image limit and tags in blacklists
    async def check_return_posts(self, *, ctx, booru='e621', tags=[], limit=1, previous={}):
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
            if len(tags) > 5:
                raise exc.TagBoundsError(formatter.tostring(tags[5:]))
            for tag in tags:
                if tag == 'swf' or tag == 'webm' or tag in blacklist:
                    raise exc.TagBlacklisted(tag)

        # Checks for blacklisted tags in endpoint blacklists - try/except is for continuing the parent loop
        posts = {}
        c = 0
        while len(posts) < limit:
            if c == 50 + limit * 3:
                raise exc.Timeout
            request = await u.fetch('https://{}.net/post/index.json'.format(booru), params={'tags': ','.join(['order:random'] + tags), 'limit': self.LIMIT}, json=True)
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
            if reaction.emoji == '🚫' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Abort
            elif reaction.emoji == '📁' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Save
            elif reaction.emoji == '⬅' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Left
            elif reaction.emoji == '🔢' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.GoTo
            elif reaction.emoji == '➡' and reaction.message.content == paginator.content and (user is ctx.author or user.id == u.config['owner_id']):
                raise exc.Right
            return False

        def on_message(msg):
            with suppress(ValueError):
                if int(msg.content) <= len(posts) and msg.author is ctx.author and msg.channel is ctx.channel:
                    return True
            return False

        args = list(args)
        limit = self.LIMIT / 5
        starred = []
        c = 1

        try:
            args = self.get_favorites(ctx, args)

            await ctx.trigger_typing()

            posts = await self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit)
            keys = list(posts.keys())
            values = list(posts.values())

            embed = d.Embed(
                title=values[c - 1]['author'], url='https://e621.net/post/show/{}'.format(keys[c - 1]), color=ctx.me.color).set_image(url=values[c - 1]['url'])
            embed.set_author(name=formatter.tostring(args, random=True),
                             url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=ctx.author.avatar_url)
            embed.set_footer(text='{} / {}'.format(c, len(posts)),
                             icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')

            paginator = await ctx.send(embed=embed)

            await paginator.add_reaction('🚫')
            await paginator.add_reaction('📁')
            await paginator.add_reaction('⬅')
            await paginator.add_reaction('🔢')
            await paginator.add_reaction('➡')
            await asyncio.sleep(1)
            await ctx.message.add_reaction('✅')

            while not self.bot.is_closed():
                try:
                    await self.bot.wait_for('reaction_add', check=on_reaction, timeout=10 * 60)

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')
                        embed.set_image(url=values[c - 1]['url'])
                        await paginator.edit(content=None, embed=embed)
                    else:
                        await paginator.edit(content='**First image.**')

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

                    await paginator.edit(content=None, embed=embed)

                except exc.Save:
                    if values[c - 1]['url'] not in starred:
                        starred.append(values[c - 1]['url'])

                        await paginator.edit(content='**Image** `{}` **saved.**'.format(len(starred)))
                    else:
                        starred.remove(values[c - 1])['url']

                        await paginator.edit(content='**Image removed.**')

                except exc.Right:
                    if c % limit == 0:
                        await ctx.trigger_typing()
                        try:
                            posts.update(await self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit, previous=posts))

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
                    await paginator.edit(content=None, embed=embed)

        except exc.Abort:
            try:
                await paginator.edit(content='🚫 **Exited paginator.**')

            except UnboundLocalError:
                await ctx.send('🚫 **Exited paginator.**')
            await ctx.message.add_reaction('🚫')
        except asyncio.TimeoutError:
            try:
                await paginator.edit(content='**Paginator timed out.**')

            except UnboundLocalError:
                await ctx.send('**Paginator timed out.**')
            await ctx.message.add_reaction('❌')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.TagBlacklisted as e:
            await ctx.send('🚫 `{}` **blacklisted.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('🚫')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5, currently.'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags.**', delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.Timeout:
            await ctx.send('**Request timed out.**')
            await ctx.message.add_reaction('❌')

        finally:
            for url in starred:
                await ctx.author.send(url)
                if len(starred) > 5:
                    await asyncio.sleep(self.RATE_LIMIT)

    @e621_paginator.error
    async def e621_paginator_error(self, ctx, error):
        if isinstance(error, errext.CheckFailure):
            await ctx.send('⛔️ {} **is not an NSFW channel.**'.format(ctx.channel.mention), delete_after=10)
            return await ctx.message.add_reaction('❌')

    def get_limit(self, args):
        limit = 1

        for arg in args:
            if len(arg) == 1:
                with suppress(ValueError):
                    if int(arg) <= 3 and int(arg) >= 1:
                        limit = int(arg)
                        args.remove(arg)
                        break
                    else:
                        raise exc.BoundsError(arg)

        return limit

    # Searches for and returns images from e621.net given tags when not blacklisted
    @commands.group(aliases=['e6', '6'], brief='e621 | NSFW', description='e621 | NSFW\nTag-based search for e621.net\n\nYou can only search 5 tags and 6 images at once for now.\ne6 [tags...] ([# of images])')
    @checks.del_ctx()
    @checks.is_nsfw()
    async def e621(self, ctx, *args):
        args = list(args)

        try:
            args = self.get_favorites(ctx, args)
            limit = self.get_limit(args)

            await ctx.trigger_typing()

            posts = await self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit)

            for ident, post in posts.items():
                embed = d.Embed(title=post['author'], url='https://e621.net/post/show/{}'.format(ident),
                                color=ctx.me.color).set_image(url=post['url'])
                embed.set_author(name=formatter.tostring(args, random=True),
                                 url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=ctx.author.avatar_url)
                embed.set_footer(
                    text=str(ident), icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')

                await ctx.send(embed=embed)

            await ctx.message.add_reaction('✅')

        except exc.TagBlacklisted as e:
            await ctx.send('`{}` **blacklisted.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.BoundsError as e:
            await ctx.send('`{}` **out of bounds.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5, currently.'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags.**', delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.Timeout:
            await ctx.send('**Request timed out.**')
            await ctx.message.add_reaction('❌')

        tools.command_dict.setdefault(str(ctx.author.id), {}).update(
            {'command': ctx.command, 'args': ctx.args})

    @e621.error
    async def e621_error(self, ctx, error):
        if isinstance(error, errext.CheckFailure):
            return await ctx.send('⛔️ {} **is not an NSFW channel.**'.format(ctx.channel.mention), delete_after=10)

    # Searches for and returns images from e926.net given tags when not blacklisted
    @commands.command(aliases=['e9', '9'], brief='e926 | SFW', description='e926 | SFW\nTag-based search for e926.net\n\nYou can only search 5 tags and 6 images at once for now.\ne9 [tags...] ([# of images])')
    @checks.del_ctx()
    async def e926(self, ctx, *args):
        args = list(args)

        try:
            args = self.get_favorites(ctx, args)
            limit = self.get_limit(args)

            await ctx.trigger_typing()

            posts = await self.check_return_posts(ctx=ctx, booru='e926', tags=args, limit=limit)

            for ident, post in posts.items():
                embed = d.Embed(title=post['author'], url='https://e926.net/post/show/{}'.format(ident),
                                color=ctx.me.color).set_image(url=post['url'])
                embed.set_author(name=formatter.tostring(args, random=True),
                                 url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=ctx.author.avatar_url)
                embed.set_footer(
                    text=str(ident), icon_url='http://lh6.ggpht.com/d3pNZNFCcJM8snBsRSdKUhR9AVBnJMcYYrR92RRDBOzCrxZMhuTeoGOQSmSEn7DAPQ=w300')

                await ctx.send(embed=embed)

            await ctx.message.add_reaction('✅')

        except exc.TagBlacklisted as e:
            await ctx.send('`{}` **blacklisted.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.BoundsError as e:
            await ctx.send('`{}` **out of bounds.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.TagBoundsError as e:
            await ctx.send('`{}` **out of bounds.** Tags limited to 5, currently.'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.NotFound as e:
            await ctx.send('`{}` **not found.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.FavoritesNotFound:
            await ctx.send('**You have no favorite tags.**', delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.Timeout:
            await ctx.send('**Request timed out.**')
            await ctx.message.add_reaction('❌')

    @commands.group(aliases=['fave', 'fav', 'f'])
    @checks.del_ctx()
    async def favorite(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Use a flag to manage favorites.**\n*Type* `{}help fav` *for more info.*'.format(ctx.prefix), delete_after=10)
            await ctx.message.add_reaction('❌')

    @favorite.error
    async def favorite_error(self, ctx, error):
        pass

    @favorite.group(name='get', aliases=['g'])
    async def _get_favorite(self, ctx):
        pass

    @_get_favorite.command(name='tags', aliases=['t'])
    async def __get_favorite_tags(self, ctx):
        await ctx.send('⭐ {}**\'s favorite tags:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(self.favorites.get(ctx.author.id, {}).get('tags', set()))), delete_after=10)
        await ctx.message.add_reaction('✅')

    @_get_favorite.command(name='posts', aliases=['p'])
    async def __get_favorite_posts(self, ctx):
        pass

    @favorite.group(name='add', aliases=['a'])
    async def _add_favorite(self, ctx):
        pass

    @_add_favorite.command(name='tags', aliases=['t'])
    async def __add_favorite_tags(self, ctx, *tags):
        try:
            for tag in tags:
                if tag in self.blacklists['user_blacklist'].get(ctx.author.id, set()):
                    raise exc.TagBlacklisted(tag)
            if len(self.favorites[ctx.author.id]['tags']) + len(tags) > 5:
                raise exc.BoundsError

            self.favorites.setdefault(ctx.author.id, {}).setdefault('tags', set()).update(tags)
            u.dump(self.favorites, 'cogs/favorites.pkl')

            await ctx.send('{} **added to their favorites:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(tags)), delete_after=5)
            await ctx.message.add_reaction('✅')

        except exc.BoundsError:
            await ctx.send('**Favorites list currently limited to:** `5`', delete_after=10)
            await ctx.message.add_reaction('❌')
        except exc.TagBlacklisted as e:
            await ctx.send('🚫 `{}` **blacklisted.**', delete_after=10)
            await ctx.message.add_reaction('🚫')

    @_add_favorite.command(name='posts', aliases=['p'])
    async def __add_favorite_posts(self, ctx, *posts):
        pass

    @favorite.group(name='remove', aliases=['r'])
    async def _remove_favorite(self, ctx):
        pass

    @_remove_favorite.command(name='tags', aliases=['t'])
    async def __remove_favorite_tags(self, ctx, *tags):
        try:
            for tag in tags:
                try:
                    self.favorites[ctx.author.id].get('tags', set()).remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.favorites, 'cogs/favorites.pkl')

            await ctx.send('{} **removed from their favorites:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(tags)), delete_after=5)
            await ctx.message.add_reaction('✅')

        except exc.TagError as e:
            await ctx.send('`{}` **not in favorites.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')

    @_remove_favorite.command(name='posts', aliases=['p'])
    async def __remove_favorite_posts(self, ctx):
        pass

    @favorite.group(name='clear', aliases=['c'])
    async def _clear_favorite(self, ctx):
        pass

    @_clear_favorite.command(name='tags', aliases=['t'])
    async def __clear_favorite_tags(self, ctx):
        with suppress(KeyError):
            del self.favorites[ctx.author.id]
            u.dump(self.favorites, 'cogs/favorites.pkl')

        await ctx.send('{}**\'s favorites cleared.**'.format(ctx.author.mention), delete_after=5)
        await ctx.message.add_reaction('✅')

    @_clear_favorite.command(name='posts', aliases=['p'])
    async def __clear_favorite_posts(self, ctx):
        pass

    # Umbrella command structure to manage global, channel, and user blacklists
    @commands.group(aliases=['bl', 'b'], brief='Manage blacklists', description='Blacklist base command for managing blacklists\n\n`bl get [blacklist]` to show a blacklist\n`bl set [blacklist] [tags]` to replace a blacklist\n`bl clear [blacklist]` to clear a blacklist\n`bl add [blacklist] [tags]` to add tags to a blacklist\n`bl remove [blacklist] [tags]` to remove tags from a blacklist', usage='[flag] [blacklist] ([tags])')
    @checks.del_ctx()
    async def blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Use a flag to manage blacklists.**\n*Type* `{}help bl` *for more info.*'.format(ctx.prefix), delete_after=10)
            await ctx.message.add_reaction('❌')

    # @blacklist.error
    # async def blacklist_error(self, ctx, error):
        # if isinstance(error, KeyError):
        #     return await ctx.send('**Blacklist does not exist.**', delete_after=10)

    @blacklist.group(name='get', aliases=['g'])
    async def _get_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    @_get_blacklist.command(name='global', aliases=['gl', 'g'])
    async def __get_global_blacklist(self, ctx):
        await ctx.send('🚫 **Global blacklist:**\n```\n{}```'.format(formatter.tostring(self.blacklists['global_blacklist'])))
        await ctx.message.add_reaction('✅')

    @_get_blacklist.command(name='channel', aliases=['ch', 'c'])
    async def __get_channel_blacklist(self, ctx):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await ctx.send('🚫 {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, formatter.tostring(self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()))))
        await ctx.message.add_reaction('✅')

    @_get_blacklist.command(name='me', aliases=['m'])
    async def __get_user_blacklist(self, ctx):
        await ctx.send('🚫 {}**\'s blacklist:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(self.blacklists['user_blacklist'].get(ctx.author.id, set()))), delete_after=10)
        await ctx.message.add_reaction('✅')

    @_get_blacklist.command(name='here', aliases=['h'])
    async def __get_here_blacklists(self, ctx):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await ctx.send('🚫 **__Blacklisted:__**\n\n**Global:**\n```\n{}```\n**{}:**\n```\n{}```'.format(formatter.tostring(self.blacklists['global_blacklist']), ctx.channel.mention, formatter.tostring(self.blacklists['guild_blacklist'].get(guild.id, {}).get(ctx.channel.id, set()))))
        await ctx.message.add_reaction('✅')

    @_get_blacklist.group(name='all', aliases=['a'])
    async def __get_all_blacklists(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**')
            await ctx.message.add_reaction('❌')

    @__get_all_blacklists.command(name='guild', aliases=['g'])
    @commands.has_permissions(manage_channels=True)
    async def ___get_all_guild_blacklists(self, ctx):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await ctx.send('🚫 **__{} blacklists:__**\n\n{}'.format(guild.name, formatter.dict_tostring(self.blacklists['guild_blacklist'].get(guild.id, {}))))
        await ctx.message.add_reaction('✅')

    @__get_all_blacklists.command(name='user', aliases=['u', 'member', 'm'])
    @commands.is_owner()
    async def ___get_all_user_blacklists(self, ctx):
        await ctx.send('🚫 **__User blacklists:__**\n\n{}'.format(formatter.dict_tostring(self.blacklists['user_blacklist'])))
        await ctx.message.add_reaction('✅')

    @blacklist.group(name='add', aliases=['a'])
    async def _add_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    @_add_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __add_global_tags(self, ctx, *tags):
        await ctx.trigger_typing()

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

        await ctx.send('**Added to global blacklist:**\n```\n{}```'.format(formatter.tostring(tags)), delete_after=5)
        await ctx.message.add_reaction('✅')

    @_add_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __add_channel_tags(self, ctx, *tags):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        await ctx.trigger_typing()

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

        await ctx.send('**Added to** {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, formatter.tostring(tags)), delete_after=5)
        await ctx.message.add_reaction('✅')

    @_add_tags.command(name='me', aliases=['m'])
    async def __add_user_tags(self, ctx, *tags):
        await ctx.trigger_typing()

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

        await ctx.send('{} **added to their blacklist:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(tags)), delete_after=5)
        await ctx.message.add_reaction('✅')

    @blacklist.group(name='remove', aliases=['rm', 'r'])
    async def _remove_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    @_remove_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __remove_global_tags(self, ctx, *tags):
        try:
            for tag in tags:
                try:
                    self.blacklists['global_blacklist'].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await ctx.send('**Removed from global blacklist:**\n```\n{}```'.format(formatter.tostring(tags)), delete_after=5)
            await ctx.message.add_reaction('✅')

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')

    @_remove_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __remove_channel_tags(self, ctx, *tags):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        try:
            for tag in tags:
                try:
                    self.blacklists['guild_blacklist'][guild.id][ctx.channel.id].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await ctx.send('**Removed from** {} **blacklist:**\n```\n{}```'.format(ctx.channel.mention, formatter.tostring(tags), delete_after=5))
            await ctx.message.add_reaction('✅')

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')

    @_remove_tags.command(name='me', aliases=['m'])
    async def __remove_user_tags(self, ctx, *tags):
        try:
            for tag in tags:
                try:
                    self.blacklists['user_blacklist'][ctx.author.id].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await ctx.send('{} **removed from their blacklist:**\n```\n{}```'.format(ctx.author.mention, formatter.tostring(tags)), delete_after=5)
            await ctx.message.add_reaction('✅')

        except exc.TagError as e:
            await ctx.send('`{}` **not in blacklist.**'.format(e), delete_after=10)
            await ctx.message.add_reaction('❌')

    @blacklist.group(name='clear', aliases=['cl', 'c'])
    async def _clear_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('**Invalid blacklist.**', delete_after=10)
            await ctx.message.add_reaction('❌')

    @_clear_blacklist.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __clear_global_blacklist(self, ctx):
        self.blacklists['global_blacklist'].clear()
        u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('**Global blacklist cleared.**', delete_after=5)
        await ctx.message.add_reaction('✅')

    @_clear_blacklist.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __clear_channel_blacklist(self, ctx):
        guild = ctx.guild if isinstance(
            ctx.guild, d.Guild) else ctx.channel

        with suppress(KeyError):
            del self.blacklists['guild_blacklist'][guild.id][ctx.channel.id]
            u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('{} **blacklist cleared.**'.format(ctx.channel.mention), delete_after=5)
        await ctx.message.add_reaction('✅')

    @_clear_blacklist.command(name='me', aliases=['m'])
    async def __clear_user_blacklist(self, ctx):
        with suppress(KeyError):
            del self.blacklists['user_blacklist'][ctx.author.id]
            u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('{}**\'s blacklist cleared.**'.format(ctx.author.mention), delete_after=5)
        await ctx.message.add_reaction('✅')
