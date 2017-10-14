import asyncio
import json
import traceback as tb

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

        self.favorites = u.setdefault('cogs/favorites.pkl', {})
        self.blacklists = u.setdefault(
            'cogs/blacklists.pkl', {'global_blacklist': set(), 'guild_blacklist': {}, 'user_blacklist': {}})
        self.aliases = u.setdefault('cogs/aliases.pkl', {})

    # Tag search
    @commands.command(aliases=['tag', 't'], brief='e621 Tag search', description='e621 | NSFW\nReturn a link search for given tags')
    @checks.del_ctx()
    async def tags(self, ctx, tag):
        tags = []

        await ctx.trigger_typing()
        tag_request = await u.fetch('https://e621.net/tag/related.json', params={'tags': tag, 'type': 'general'}, json=True)
        for tag in tag_request.get('wolf', []):
            tags.append(tag[0])

        await ctx.send('✅ ``{}` **tags:**\n```\n{}```'.format(tag, formatter.tostring(tags)))

    @tags.error
    async def tags_error(self, ctx, error):
        if isinstance(error, errext.MissingRequiredArgument):
            return await ctx.send('❌ **No tags given.**', delete_after=10)

    # Tag aliases
    @commands.command(name='aliases', aliases=['alias', 'a'], brief='e621 Tag aliases', description='e621 | NSFW\nSearch aliases for given tag')
    @checks.del_ctx()
    async def tag_aliases(self, ctx, tag):
        aliases = []

        await ctx.trigger_typing()
        alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
        for dic in alias_request:
            aliases.append(dic['name'])

        await ctx.send('✅ `{}` **aliases:**\n```\n{}```'.format(tag, formatter.tostring(aliases)))

    @tag_aliases.error
    async def tag_aliases_error(self, ctx, error):
        if isinstance(error, errext.MissingRequiredArgument):
            return await ctx.send('❌ **No tags given.**', delete_after=10)

    # Reverse image searches a linked image using the public iqdb
    @commands.command(name='reverse', aliases=['rev', 'ris'], brief='e621 Reverse image search', description='e621 | NSFW\nReverse-search an image with given URL')
    @checks.del_ctx()
    async def reverse_image_search(self, ctx, url):
        try:
            await ctx.trigger_typing()
            await ctx.send('✅ **Probable match:**\n{}'.format(await scraper.check_match(url)))

        except exc.MatchError:
            await ctx.send('❌ **No probable match.**', delete_after=10)

    @reverse_image_search.error
    async def reverse_image_search_error(self, ctx, error):
        if isinstance(error, errext.MissingRequiredArgument):
            return await ctx.send('❌ **Invalid url.**', delete_after=10)

    async def return_pool(self, *, ctx, booru='e621', query=[]):
        channel = ctx.message.channel
        user = ctx.message.author

        def on_message(msg):
            if msg.content.lower() == 'cancel' and msg.author is user and msg.channel is channel:
                raise exc.Abort
            try:
                if int(msg.content) <= len(pools) and int(msg.content) > 0 and msg.author is user and msg.channel is channel:
                    return True

            except ValueError:
                pass

            else:
                return False

        posts = {}
        pool = {}

        pools = []
        pool_request = await u.fetch('https://{}.net/pool/index.json'.format(booru), params={'query': ' '.join(query)}, json=True)
        if len(pool_request) > 1:
            for pool in pool_request:
                pools.append(pool['name'])
            match = await ctx.send('✅ **Multiple pools found.** Type in the correct match.\n```\n{}```\nor `cancel` to cancel.'.format('\n'.join(['{} {}'.format(c, elem) for c, elem in enumerate(pools, 1)])))
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
        elif request:
            temppool = pool_request[0]
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
        channel = ctx.message.channel
        user = ctx.message.author

        def on_react(reaction, user):
            if reaction.emoji == '🚫' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.Abort
            elif reaction.emoji == '📁' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.Save
            elif reaction.emoji == '⬅' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.Left
            elif reaction.emoji == '🔢' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.GoTo
            elif reaction.emoji == '➡' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.Right
            else:
                return False

        def on_message(msg):
            try:
                if int(msg.content) <= len(posts) and msg.author is user and msg.channel is channel:
                    return True

            except ValueError:
                pass

            else:
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
                             url='https://e621.net/pool/show?id={}'.format(pool['id']), icon_url=user.avatar_url)
            embed.set_footer(text='{} / {}'.format(c, len(posts)),
                             icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')

            paginator = await ctx.send(embed=embed)

            await paginator.add_reaction('🚫')
            await paginator.add_reaction('📁')
            await paginator.add_reaction('⬅')
            await paginator.add_reaction('🔢')
            await paginator.add_reaction('➡')
            await asyncio.sleep(1)

            while not self.bot.is_closed():
                try:
                    await self.bot.wait_for('reaction_add', check=on_react, timeout=10 * 60)

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                        embed.set_image(url=values[c - 1]['url'])

                        await paginator.edit(content=None, embed=embed)
                    else:
                        await paginator.edit(content='❌ **First image.**')

                except exc.GoTo:
                    await paginator.edit(content='**Enter image number...**')
                    number = await self.bot.wait_for('message', check=on_message, timeout=10 * 60)

                    c = int(number.content)
                    await number.delete()
                    embed.title = values[c - 1]['author']
                    embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                    embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                     icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                    embed.set_image(url=values[c - 1]['url'])

                    await paginator.edit(content=None, embed=embed)

                except exc.Save:
                    if values[c - 1]['url'] not in starred:
                        starred.append(values[c - 1]['url'])

                        await paginator.edit(content='**Image** `{}` **saved.**'.format(len(starred)))

                except exc.Right:
                    if c < len(keys):
                        c += 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                        embed.set_image(url=values[c - 1]['url'])

                        await paginator.edit(content=None, embed=embed)

        except exc.Abort:
            try:
                await paginator.edit(content='🚫 **Exited paginator.**')

            except UnboundLocalError:
                await ctx.send('🚫 **Exited paginator.**')

        except asyncio.TimeoutError:
            try:
                await ctx.send(content='❌ **Paginator timed out.**')

            except UnboundLocalError:
                await ctx.send('❌ **Paginator timed out.**')

        except exc.NotFound:
            await ctx.send('❌ **Pool not found.**', delete_after=10)

        except exc.Timeout:
            await ctx.send('❌ **Request timed out.**')

        finally:
            for url in starred:
                await user.send(url)
                if len(starred) > 5:
                    await asyncio.sleep(2.1)

    # Messy code that checks image limit and tags in blacklists
    async def check_return_posts(self, *, ctx, booru='e621', tags=[], limit=1, previous={}):
        guild = ctx.message.guild if isinstance(
            ctx.message.guild, d.Guild) else ctx.message.channel
        channel = ctx.message.channel
        user = ctx.message.author

        blacklist = set()
        # Creates temp blacklist based on context
        for tag in self.blacklists['global_blacklist']:
            blacklist.update(list(self.aliases[tag]) + [tag])
        for tag in self.blacklists['guild_blacklist'].get(guild.id, {}).get(channel.id, set()):
            blacklist.update(list(self.aliases[tag]) + [tag])
        for tag in self.blacklists['user_blacklist'].get(user.id, set()):
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
        channel = ctx.message.channel
        user = ctx.message.author

        def on_react(reaction, user):
            if reaction.emoji == '🚫' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.Abort
            elif reaction.emoji == '📁' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.Save
            elif reaction.emoji == '⬅' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.Left
            elif reaction.emoji == '🔢' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.GoTo
            elif reaction.emoji == '➡' and reaction.message.content == paginator.content and (user is user or user.id == u.config['owner_id']):
                raise exc.Right
            else:
                return False

        def on_message(msg):
            try:
                if int(msg.content) <= len(posts) and msg.author is user and msg.channel is channel:
                    return True

            except ValueError:
                pass

            else:
                return False

        args = list(args)
        limit = self.LIMIT / 5
        starred = []
        c = 1

        try:
            await ctx.trigger_typing()
            posts = await self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit)
            keys = list(posts.keys())
            values = list(posts.values())

            embed = d.Embed(
                title=values[c - 1]['author'], url='https://e621.net/post/show/{}'.format(keys[c - 1]), color=ctx.me.color).set_image(url=values[c - 1]['url'])
            embed.set_author(name=formatter.tostring(args, random=True),
                             url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=user.avatar_url)
            embed.set_footer(text='{} / {}'.format(c, len(posts)),
                             icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')

            paginator = await ctx.send(embed=embed)

            await paginator.add_reaction('🚫')
            await paginator.add_reaction('📁')
            await paginator.add_reaction('⬅')
            await paginator.add_reaction('🔢')
            await paginator.add_reaction('➡')
            await asyncio.sleep(1)

            while not self.bot.is_closed():
                try:
                    await self.bot.wait_for('reaction_add', check=on_react, timeout=10 * 60)

                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = values[c - 1]['author']
                        embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                        embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                         icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                        embed.set_image(url=values[c - 1]['url'])
                        await paginator.edit(content=None, embed=embed)
                    else:
                        await paginator.edit(content='❌ **First image.**')

                except exc.GoTo:
                    await paginator.edit(content='**Enter image number...**')
                    number = await self.bot.wait_for('message', check=on_message, timeout=10 * 60)

                    c = int(number.content)
                    await number.delete()
                    embed.title = values[c - 1]['author']
                    embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                    embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                     icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                    embed.set_image(url=values[c - 1]['url'])

                    await paginator.edit(content=None, embed=embed)

                except exc.Save:
                    if values[c - 1]['url'] not in starred:
                        starred.append(values[c - 1]['url'])

                        await paginator.edit(content='**Image** `{}` **saved.**'.format(len(starred)))

                except exc.Right:
                    if c % limit == 0:
                        await ctx.trigger_typing()
                        try:
                            posts.update(await self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit, previous=posts))

                        except exc.NotFound:
                            await paginator.edit(content='❌ **No more images found.**')

                        keys = list(posts.keys())
                        values = list(posts.values())

                    c += 1
                    embed.title = values[c - 1]['author']
                    embed.url = 'https://e621.net/post/show/{}'.format(keys[c - 1])
                    embed.set_footer(text='{} / {}'.format(c, len(posts)),
                                     icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                    embed.set_image(url=values[c - 1]['url'])
                    await paginator.edit(content=None, embed=embed)

        except exc.Abort:
            await paginator.edit(content='🚫 **Exited paginator.**')

        except asyncio.TimeoutError:
            await paginator.edit(content='❌ **Paginator timed out.**')

        except exc.NotFound as e:
            await ctx.send('❌ `{}` **not found.**'.format(e), delete_after=10)

        except exc.TagBlacklisted as e:
            await ctx.send('❌ `{}` **blacklisted.**'.format(e), delete_after=10)

        except exc.TagBoundsError as e:
            await ctx.send('❌ `{}` **out of bounds.** Tags limited to 5, currently.'.format(e), delete_after=10)

        except exc.Timeout:
            await ctx.send('❌ **Request timed out.**')

        finally:
            for url in starred:
                await user.send(url)
                if len(starred) > 5:
                    await asyncio.sleep(2.1)

    @e621_paginator.error
    async def e621_paginator_error(self, ctx, error):
        if isinstance(error, errext.CheckFailure):
            return await ctx.send('❌ {} **is not an NSFW channel.**'.format(ctx.message.channel.mention), delete_after=10)

    # Searches for and returns images from e621.net given tags when not blacklisted
    @commands.command(aliases=['e6', '6'], brief='e621 | NSFW', description='e621 | NSFW\nTag-based search for e621.net\n\nYou can only search 5 tags and 6 images at once for now.\ne6 [tags...] ([# of images])')
    @checks.del_ctx()
    @checks.is_nsfw()
    async def e621(self, ctx, *args):
        args = list(args)
        limit = 1

        try:
            await ctx.trigger_typing()
            # Checks for, defines, and removes limit from args
            for arg in args:
                if len(arg) == 1:
                    try:
                        if int(arg) <= 6 and int(arg) >= 1:
                            limit = int(arg)
                            args.remove(arg)
                        else:
                            raise exc.BoundsError(arg)

                    except ValueError:
                        pass
            posts = await self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit)
            for ident, post in posts.items():
                embed = d.Embed(title=post['author'], url='https://e621.net/post/show/{}'.format(ident),
                                color=ctx.me.color).set_image(url=post['url'])
                embed.set_author(name=formatter.tostring(args, random=True),
                                 url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=user.avatar_url)
                embed.set_footer(
                    text=str(ident), icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                await ctx.send(embed=embed)

        except exc.TagBlacklisted as e:
            await ctx.send('❌ `{}` **blacklisted.**'.format(e), delete_after=10)

        except exc.BoundsError as e:
            await ctx.send('❌ `{}` **out of bounds.**'.format(e), delete_after=10)

        except exc.TagBoundsError as e:
            await ctx.send('❌ `{}` **out of bounds.** Tags limited to 5, currently.'.format(e), delete_after=10)

        except exc.NotFound as e:
            await ctx.send('❌ `{}` **not found.**'.format(e), delete_after=10)

        except exc.Timeout:
            await ctx.send('❌ **Request timed out.**')

        tools.command_dict.setdefault(str(user.id), {}).update(
            {'command': ctx.command, 'args': ctx.args})

    @e621.error
    async def e621_error(self, ctx, error):
        if isinstance(error, errext.CheckFailure):
            return await ctx.send('❌ {} **is not an NSFW channel.**'.format(ctx.message.channel.mention), delete_after=10)

    # Searches for and returns images from e926.net given tags when not blacklisted
    @commands.command(aliases=['e9', '9'], brief='e926 | SFW', description='e926 | SFW\nTag-based search for e926.net\n\nYou can only search 5 tags and 6 images at once for now.\ne9 [tags...] ([# of images])')
    @checks.del_ctx()
    async def e926(self, ctx, *args):
        args = list(args)
        limit = 1

        try:
            await ctx.trigger_typing()
            # Checks for, defines, and removes limit from args
            for arg in args:
                if len(arg) == 1:
                    try:
                        if int(arg) <= 6 and int(arg) >= 1:
                            limit = int(arg)
                            args.remove(arg)
                        else:
                            raise exc.BoundsError(arg)

                    except ValueError:
                        pass
            posts = await self.check_return_posts(ctx=ctx, booru='e926', tags=args, limit=limit)
            for ident, post in posts.items():
                embed = d.Embed(title=post['author'], url='https://e926.net/post/show/{}'.format(ident),
                                color=ctx.me.color).set_image(url=post['url'])
                embed.set_author(name=formatter.tostring(args, random=True),
                                 url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=user.avatar_url)
                embed.set_footer(
                    text=str(ident), icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                await ctx.send(embed=embed)

        except exc.TagBlacklisted as e:
            await ctx.send('❌ `{}` **blacklisted.**'.format(e), delete_after=10)

        except exc.BoundsError as e:
            await ctx.send('❌ `{}` **out of bounds.**'.format(e), delete_after=10)

        except exc.TagBoundsError as e:
            await ctx.send('❌ `{}` **out of bounds.** Tags limited to 5, currently.'.format(e), delete_after=10)

        except exc.NotFound as e:
            await ctx.send('❌ `{}` **not found.**'.format(e), delete_after=10)

        except exc.Timeout:
            await ctx.send('❌ **Request timed out.**')

    @commands.group(name='favorites', aliases=['faves', 'f'])
    @checks.del_ctx()
    async def favorites(self, ctx):
        pass

    @favorites.error
    async def favorites_error(self, ctx, error):
        pass

    @favorites.command(name='get', aliases=['g'])
    async def _get_favorites(self, ctx):
        user = ctx.message.author

        await ctx.send('⭐ {}**\'s favorites:**\n```\n{}```'.format(user.mention, formatter.tostring(self.favorites.get(user.id, set()))))

    @favorites.command(name='add', aliases=['a'])
    async def _add_favorites(self, ctx, *tags):
        user = ctx.message.author

        self.favorites.setdefault(user.id, set()).update(tags)
        u.dump(self.favorites, 'cogs/favorites.pkl')

        await ctx.send('✅ {} **added:**\n```\n{}```'.format(user.mention, formatter.tostring(tags)))

    @favorites.command(name='remove', aliases=['r'])
    async def _remove_favorites(self, ctx, *tags):
        user = ctx.message.author

        try:
            for tag in tags:
                try:
                    self.favorites[user.id].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.favorites, 'cogs/favorites.pkl')

            await ctx.send('✅ {} **removed:**\n```\n{}```'.format(user.mention, formatter.tostring(tags)), delete_after=5)

        except exc.TagError as e:
            await ctx.send('❌ `{}` **not in favorites.**'.format(e), delete_after=10)

    @favorites.command(name='clear', aliases=['c'])
    async def _clear_favorites(self, ctx):
        user = ctx.message.author

        del self.favorites[user.id]

        await ctx.send('✅ {}**\'s favorites cleared.**'.format(user.mention))

    # Umbrella command structure to manage global, channel, and user blacklists
    @commands.group(aliases=['bl', 'b'], brief='Manage blacklists', description='Blacklist base command for managing blacklists\n\n`bl get [blacklist]` to show a blacklist\n`bl set [blacklist] [tags]` to replace a blacklist\n`bl clear [blacklist]` to clear a blacklist\n`bl add [blacklist] [tags]` to add tags to a blacklist\n`bl remove [blacklist] [tags]` to remove tags from a blacklist', usage='[flag] [blacklist] ([tags])')
    @checks.del_ctx()
    async def blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Use a flag to manage blacklists.**\n*Type* `{}help bl` *for more info.*'.format(ctx.prefix), delete_after=10)

    @blacklist.error
    async def blacklist_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            return await ctx.send('❌ **Insufficient permissions.**')
        # if isinstance(error, KeyError):
        #     return await ctx.send('❌ **Blacklist does not exist.**', delete_after=10)

    @blacklist.group(name='get', aliases=['g'])
    async def _get_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**', delete_after=10)

    @_get_blacklist.command(name='global', aliases=['gl', 'g'])
    async def __get_global_blacklist(self, ctx):
        await ctx.send('🚫 **Global blacklist:**\n```\n{}```'.format(formatter.tostring(self.blacklists['global_blacklist'])))

    @_get_blacklist.command(name='channel', aliases=['ch', 'c'])
    async def __get_channel_blacklist(self, ctx):
        guild = ctx.message.guild if isinstance(
            ctx.message.guild, d.Guild) else ctx.message.channel
        channel = ctx.message.channel

        await ctx.send('🚫 {} **blacklist:**\n```\n{}```'.format(channel.mention, formatter.tostring(self.blacklists['guild_blacklist'].get(guild.id, {}).get(channel.id, set()))))

    @_get_blacklist.command(name='me', aliases=['m'])
    async def __get_user_blacklist(self, ctx):
        user = ctx.message.author

        await ctx.send('🚫 {}**\'s blacklist:**\n```\n{}```'.format(user.mention, formatter.tostring(self.blacklists['user_blacklist'].get(user.id, set()))), delete_after=10)

    @_get_blacklist.command(name='here', aliases=['h'])
    async def __get_here_blacklists(self, ctx):
        guild = ctx.message.guild if isinstance(
            ctx.message.guild, d.Guild) else ctx.message.channel
        channel = ctx.message.channel

        await ctx.send('🚫 **__Blacklisted:__**\n\n**Global:**\n```\n{}```\n**{}:**\n```\n{}```'.format(formatter.tostring(self.blacklists['global_blacklist']), channel.mention, formatter.tostring(self.blacklists['guild_blacklist'].get(guild.id, {}).get(channel.id, set()))))

    @_get_blacklist.group(name='all', aliases=['a'])
    async def __get_all_blacklists(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')

    @__get_all_blacklists.command(name='guild', aliases=['g'])
    @commands.has_permissions(manage_channels=True)
    async def ___get_all_guild_blacklists(self, ctx):
        guild = ctx.message.guild if isinstance(
            ctx.message.guild, d.Guild) else ctx.message.channel

        await ctx.send('🚫 **__{} blacklists:__**\n\n{}'.format(guild.name, formatter.dict_tostring(self.blacklists['guild_blacklist'].get(guild.id, {}))))

    @__get_all_blacklists.command(name='user', aliases=['u', 'member', 'm'])
    @commands.is_owner()
    async def ___get_all_user_blacklists(self, ctx):
        await ctx.send('🚫 **__User blacklists:__**\n\n{}'.format(formatter.dict_tostring(self.blacklists['user_blacklist'])))

    @blacklist.group(name='add', aliases=['a'])
    async def _add_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**', delete_after=10)

    @_add_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __add_global_tags(self, ctx, *tags):
        self.blacklists['global_blacklist'].update(tags)
        for tag in tags:
            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            if alias_request:
                for dic in alias_request:
                    self.aliases.setdefault(tag, set()).add(dic['name'])
        u.dump(self.blacklists, 'cogs/blacklists.pkl')
        u.dump(self.aliases, 'cogs/aliases.pkl')

        await ctx.send('✅ **Added to global blacklist:**\n```\n{}```'.format(formatter.tostring(tags)), delete_after=5)

    @_add_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __add_channel_tags(self, ctx, *tags):
        guild = ctx.message.guild if isinstance(
            ctx.message.guild, d.Guild) else ctx.message.channel
        channel = ctx.message.channel

        self.blacklists['guild_blacklist'].setdefault(
            guild.id, {}).setdefault(channel.id, set()).update(tags)
        for tag in tags:
            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            if alias_request:
                for dic in alias_request:
                    self.aliases.setdefault(tag, set()).add(dic['name'])
        u.dump(self.blacklists, 'cogs/blacklists.pkl')
        u.dump(self.aliases, 'cogs/aliases.pkl')

        await ctx.send('✅ **Added to** {} **blacklist:**\n```\n{}```'.format(channel.mention, formatter.tostring(tags)), delete_after=5)

    @_add_tags.command(name='me', aliases=['m'])
    async def __add_user_tags(self, ctx, *tags):
        user = ctx.message.author

        self.blacklists['user_blacklist'].setdefault(user.id, set()).update(tags)
        for tag in tags:
            alias_request = await u.fetch('https://e621.net/tag_alias/index.json', params={'aliased_to': tag, 'approved': 'true'}, json=True)
            if alias_request:
                for dic in alias_request:
                    self.aliases.setdefault(tag, set()).add(dic['name'])
        u.dump(self.blacklists, 'cogs/blacklists.pkl')
        u.dump(self.aliases, 'cogs/aliases.pkl')

        await ctx.send('✅ {} **added:**\n```\n{}```'.format(user.mention, formatter.tostring(tags)), delete_after=5)

    @blacklist.group(name='remove', aliases=['rm', 'r'])
    async def _remove_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**', delete_after=10)

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

            await ctx.send('✅ **Removed from global blacklist:**\n```\n{}```'.format(formatter.tostring(tags)), delete_after=5)

        except exc.TagError as e:
            await ctx.send('❌ `{}` **not in blacklist.**'.format(e), delete_after=10)

    @_remove_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __remove_channel_tags(self, ctx, *tags):
        guild = ctx.message.guild if isinstance(
            ctx.message.guild, d.Guild) else ctx.message.channel
        channel = ctx.message.channel

        try:
            for tag in tags:
                try:
                    self.blacklists['guild_blacklist'][guild.id][channel.id].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await ctx.send('✅ **Removed from** {} **blacklist:**\n```\n{}```'.format(channel.mention, formatter.tostring(tags), delete_after=5))

        except exc.TagError as e:
            await ctx.send('❌ `{}` **not in blacklist.**'.format(e), delete_after=10)

    @_remove_tags.command(name='me', aliases=['m'])
    async def __remove_user_tags(self, ctx, *tags):
        user = ctx.message.author

        try:
            for tag in tags:
                try:
                    self.blacklists['user_blacklist'][user.id].remove(tag)

                except KeyError:
                    raise exc.TagError(tag)

            u.dump(self.blacklists, 'cogs/blacklists.pkl')

            await ctx.send('✅ {} **removed:**\n```\n{}```'.format(user.mention, formatter.tostring(tags)), delete_after=5)

        except exc.TagError as e:
            await ctx.send('❌ `{}` **not in blacklist.**'.format(e), delete_after=10)

    @blacklist.group(name='clear', aliases=['cl', 'c'])
    async def _clear_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**', delete_after=10)

    @_clear_blacklist.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __clear_global_blacklist(self, ctx):
        del self.blacklists['global_blacklist']
        u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('✅ **Global blacklist cleared.**', delete_after=5)

    @_clear_blacklist.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __clear_channel_blacklist(self, ctx):
        guild = ctx.message.guild if isinstance(
            ctx.message.guild, d.Guild) else ctx.message.channel
        channel = ctx.message.channel

        del self.blacklists['guild_blacklist'][str(guild.id)][channel.id]
        u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('✅ {} **blacklist cleared.**'.format(channel.mention), delete_after=5)

    @_clear_blacklist.command(name='me', aliases=['m'])
    async def __clear_user_blacklist(self, ctx):
        user = ctx.message.author

        del self.blacklists['user_blacklist'][user.id]
        u.dump(self.blacklists, 'cogs/blacklists.pkl')

        await ctx.send('✅ {}**\'s blacklist cleared.**'.format(user.mention), delete_after=5)
