import json

try:
    with open('blacklists.json') as infile:
        blacklists = json.load(infile)
        print('\"blacklists.json\" loaded.')
except FileNotFoundError:
    with open('blacklists.json', 'w+') as iofile:
        print('Blacklists file not found: \"blacklists.json\" created and loaded.')
        json.dump({'global_blacklist': [], 'guild_blacklist': {}, 'user_blacklist': {}}, iofile, indent=4, sort_keys=True)
        iofile.seek(0)
        blacklists = json.load(iofile)
try:
    with open('aliases.json') as infile:
        aliases = json.load(infile)
        print('\"aliases.json\" loaded.')
except FileNotFoundError:
    with open('aliases.json', 'w+') as iofile:
        print('Aliases file not found: \"aliases.json\" created and loaded.')
        json.dump({'global_blacklist': {}, 'guild_blacklist': {}, 'user_blacklist': {}}, iofile, indent=4, sort_keys=True)
        iofile.seek(0)
        aliases = json.load(iofile)

import asyncio
import discord as d
import requests
import traceback as tb
import discord as d
from discord import reaction
from discord.ext import commands
from discord.ext.commands import errors as errext
from discord import errors as err
from cogs import tools
from misc import checks
from misc import exceptions as exc
from utils import formatter, scraper
from utils import utils as u

HEADERS = {'user-agent': 'Modumind/0.0.1 (Myned)'}

# temp_urls = {}

class MsG:

    def __init__(self, bot):
        self.bot = bot

    # Creates reaction-based paginator for linked pools
    @commands.command(brief='e621/e926 Pool selector', description='e621/e926 | NSFW/SFW\nShow pools in a page format', hidden=True)
    @checks.del_ctx()
    async def pool(self, ctx, url):
        pool_urls = []

        def check_right(reaction, user):
            return user == ctx.message.author and str(reaction.emoji) == '➡️'
        def check_left(reaction, user):
            return user == ctx.message.author and str(reaction.emoji) == '⬅️'

        try:
            pool = scraper.find_pool(url)
            for link in pool:
                pool_urls.append(scraper.find_image_url('https://e621.net' + link))
        except exc.PostError:
            await ctx.send('❌ ' + ctx.message.author.mention + ' **No pool found.**')
        except exc.ImageError:
            await ctx.send('❌ ' + ctx.message.author.mention + ' **No image found.**')
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()

    # Tag aliases
    @commands.command(aliases=['alias', 'a'], brief='e621 Tag aliases', description='e621 | NSFW\nSearch aliases for given tag')
    @checks.del_ctx()
    async def aliases(self, ctx, tag):
        global HEADERS
        aliases = []
        try:
            alias_request = requests.get('https://e621.net/tag_alias/index.json?aliased_to=' + tag + '&approved=true', headers=HEADERS).json()
            for dic in alias_request:
                aliases.append(dic['name'])
            await ctx.send('✅ `' + tag + '` **aliases:**\n```' + formatter.tostring(aliases) + '```')
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()

    # Reverse image searches a linked image using the public iqdb
    @commands.command(name='reverse', aliases=['rev', 'ris'], brief='e621 Reverse image search', description='e621 | NSFW\nReverse-search an image with given URL')
    @checks.del_ctx()
    async def reverse_image_search(self, ctx, url):
        try:
            await ctx.trigger_typing()
            await ctx.send('✅ ' + ctx.message.author.mention + ' **Probable match:**\n' + scraper.check_match('http://iqdb.harry.lu/?url={}'.format(url)))
        except exc.MatchError:
            await ctx.send('❌ ' + ctx.message.author.mention + ' **No probable match.**', delete_after=10)
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()

    @commands.command(name='e621p', aliases=['e6p', '6p'])
    @checks.del_ctx()
    @checks.is_nsfw()
    async def e621_paginator(self, ctx, *args):
        def react(reaction, user):
            if reaction.emoji == '⬅' and reaction.message.content == paginator.content and user is ctx.message.author: raise exc.Left
            elif reaction.emoji == '🚫' and reaction.message.content == paginator.content and user is ctx.message.author: raise exc.Abort
            elif reaction.emoji == '📁' and reaction.message.content == paginator.content and user is ctx.message.author: raise exc.Save
            elif reaction.emoji == '➡' and reaction.message.content == paginator.content and user is ctx.message.author: raise exc.Right
            else: return False

        user = ctx.message.author
        args = list(args)
        limit = 100

        try:
            await ctx.trigger_typing()

            c = 1
            posts = self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit)
            starred = []

            embed = d.Embed(title='/post/{}'.format(list(posts.keys())[c-1]), url='https://e621.net/post/show/{}'.format(list(posts.keys())[c-1]), color=ctx.me.color).set_image(url=list(posts.values())[c-1])
            embed.set_author(name=formatter.tostring(args, random=True), url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=user.avatar_url)
            embed.set_footer(text='e621', icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
            paginator = await ctx.send(embed=embed)

            await paginator.add_reaction('⬅')
            await paginator.add_reaction('🚫')
            await paginator.add_reaction('📁')
            await paginator.add_reaction('➡')
            await asyncio.sleep(1)

            while True:
                try:
                    await self.bot.wait_for('reaction_add', check=react, timeout=5*60)
                except exc.Left:
                    if c > 1:
                        c -= 1
                        embed.title = '/post/{}'.format(list(posts.keys())[c-1])
                        embed.url = 'https://e621.net/post/show/{}'.format(list(posts.keys())[c-1])
                        embed.set_image(url=list(posts.values())[c-1])
                        await paginator.edit(embed=embed)
                except exc.Save:
                    if list(posts.values())[c-1] not in starred:
                        starred.append(list(posts.values())[c-1])
                except exc.Right:
                    if c % limit == 0:
                        await ctx.trigger_typing()
                        try: posts.update(self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit, previous=posts))
                        except exc.NotFound:
                            await paginator.edit(content='❌ **No more images found.**')

                    c += 1
                    embed.title = '/post/{}'.format(list(posts.keys())[c-1])
                    embed.url = 'https://e621.net/post/show/{}'.format(list(posts.keys())[c-1])
                    embed.set_image(url=list(posts.values())[c-1])
                    await paginator.edit(embed=embed)
        except exc.Abort: await paginator.edit(content='🚫 **Exited paginator.**')
        except exc.TagBlacklisted as e: await ctx.send('❌ `{}` **blacklisted.**'.format(e), delete_after=10)
        except exc.TagBoundsError as e: await ctx.send('❌ `{}` **out of bounds.** Tags limited to 5, currently.'.format(e), delete_after=10)
        except exc.Timeout: await ctx.send('❌ **Request timed out.**')
        except asyncio.TimeoutError: await paginator.edit(content='❌ **Paginator timed out.**')
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()
        finally:
            if starred:
                for url in starred: await user.send(url)

    @e621_paginator.error
    async def e621_paginator_error(self, ctx, error):
        if isinstance(error, errext.CheckFailure):
            return await ctx.send('❌ <#' + str(ctx.message.channel.id) + '> **is not an NSFW channel.**', delete_after=10)

    # Searches for and returns images from e621.net given tags when not blacklisted
    @commands.command(aliases=['e6', '6'], brief='e621 | NSFW', description='e621 | NSFW\nTag-based search for e621.net\n\nYou can only search 5 tags and 6 images at once for now.\ne6 [tags...] ([# of images])')
    @checks.del_ctx()
    @checks.is_nsfw()
    async def e621(self, ctx, *args):
        # global temp_urls

        args = list(args)
        limit = 1

        try:
            await ctx.trigger_typing()
            # Checks for, defines, and removes limit from args
            for arg in args:
                if len(arg) == 1:
                    if int(arg) <= 6 and int(arg) >= 1:
                        limit = int(arg)
                        args.remove(arg)
                    else: raise exc.BoundsError(arg)
            posts = self.check_return_posts(ctx=ctx, booru='e621', tags=args, limit=limit)#, previous=temp_urls.get(ctx.message.author.id, []))
            for ident, url in posts.items():
                embed = d.Embed(title='/post/{}'.format(ident), url='https://e621.net/post/show/{}'.format(ident), color=ctx.me.color).set_image(url=url)
                embed.set_author(name=formatter.tostring(args, random=True), url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=ctx.message.author.avatar_url)
                embed.set_footer(text='e621', icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                await ctx.send(embed=embed)
            # temp_urls.setdefault(ctx.message.author.id, []).extend(posts.values())
        except exc.TagBlacklisted as e: await ctx.send('❌ `' + str(e) + '` **blacklisted.**', delete_after=10)
        except exc.BoundsError as e: await ctx.send('❌ `' + str(e) + '` **out of bounds.**', delete_after=10)
        except exc.TagBoundsError as e: await ctx.send('❌ `' + str(e) + '` **out of bounds.** Tags limited to 5, currently.', delete_after=10)
        except exc.NotFound as e: await ctx.send('❌ `' + str(e) + '` **not found.**', delete_after=10)
        except exc.Timeout: await ctx.send('❌ **Request timed out.**')
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()
        tools.command_dict.setdefault(str(ctx.message.author.id), {}).update({'command': ctx.command, 'args': ctx.args})

    @e621.error
    async def e621_error(self, ctx, error):
        if isinstance(error, errext.CheckFailure):
            return await ctx.send('❌ <#' + str(ctx.message.channel.id) + '> **is not an NSFW channel.**', delete_after=10)

    # Searches for and returns images from e926.net given tags when not blacklisted
    @commands.command(aliases=['e9', '9'], brief='e926 | SFW', description='e926 | SFW\nTag-based search for e926.net\n\nYou can only search 5 tags and 6 images at once for now.\ne9 [tags...] ([# of images])')
    @checks.del_ctx()
    async def e926(self, ctx, *args):
        # global temp_urls

        args = list(args)
        limit = 1

        try:
            await ctx.trigger_typing()
            # Checks for, defines, and removes limit from args
            for arg in args:
                if len(arg) == 1:
                    if int(arg) <= 6 and int(arg) >= 1:
                        limit = int(arg)
                        args.remove(arg)
                    else: raise exc.BoundsError(arg)
            posts = self.check_return_posts(ctx=ctx, booru='e926', tags=args, limit=limit)#, previous=temp_urls.get(ctx.message.author.id, []))
            for ident, url in posts.items():
                embed = d.Embed(title='/post/{}'.format(ident), url='https://e926.net/post/show/{}'.format(ident), color=ctx.me.color).set_image(url=url)
                embed.set_author(name=formatter.tostring(args, random=True), url='https://e621.net/post?tags={}'.format(','.join(args)), icon_url=ctx.message.author.avatar_url)
                embed.set_footer(text='e926', icon_url='http://ndl.mgccw.com/mu3/app/20141013/18/1413204353554/icon/icon_xl.png')
                await ctx.send(embed=embed)
            # temp_urls.setdefault(ctx.message.author.id, []).extend(posts.values())
        except exc.TagBlacklisted as e: await ctx.send('❌ `' + str(e) + '` **blacklisted.**', delete_after=10)
        except exc.BoundsError as e: await ctx.send('❌ `' + str(e) + '` **out of bounds.**', delete_after=10)
        except exc.TagBoundsError as e: await ctx.send('❌ `' + str(e) + '` **out of bounds.** Tags limited to 5, currently.', delete_after=10)
        except exc.NotFound as e: await ctx.send('❌ `' + str(e) + '` **not found.**', delete_after=10)
        except exc.Timeout: await ctx.send('❌ **Request timed out.**')
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()

    # Messy code that checks image limit and tags in blacklists
    def check_return_posts(self, *, ctx, booru='e621', tags=[], limit=1, previous=[]):
        global blacklists, aliases, HEADERS

        if isinstance(ctx.message.guild, d.Guild): guild = ctx.message.guild
        else: guild = ctx.message.channel
        channel = ctx.message.channel
        user = ctx.message.author
        blacklist = []

        # Creates temp blacklist based on context
        for k, v in aliases['global_blacklist'].items(): blacklist.extend([k] + v)
        for k, v in aliases['guild_blacklist'].get(str(guild.id), {}).get(str(channel.id), {}).items(): blacklist.extend([k] + v)
        for k, v in aliases['user_blacklist'].get(str(user.id), {}).items(): blacklist.extend([k] + v)
        # Checks if tags are in local blacklists
        if tags:
            if len(tags) > 5: raise exc.TagBoundsError(formatter.tostring(tags[5:]))
            for tag in tags:
                if tag == 'swf' or tag == 'webm' or tag in blacklist: raise exc.TagBlacklisted(tag)

        # Checks for blacklisted tags in endpoint blacklists - try/except is for continuing the parent loop
        posts = {}
        c = 0
        while len(posts) < limit:
            if c == 50 + limit: raise exc.Timeout
            request = requests.get('https://{}.net/post/index.json?tags={}'.format(booru, ','.join(['order:random'] + tags)), headers=HEADERS).json()
            if len(request) == 0: raise exc.NotFound(formatter.tostring(tags))
            if len(request) < limit: limit = len(request)
            for post in request:
                if 'swf' in post['file_ext'] or 'webm' in post['file_ext']: continue
                try:
                    for tag in blacklist:
                        if tag in post['tags']: raise exc.Continue
                except exc.Continue: continue
                if post['file_url'] not in posts.values() and post['file_url'] not in previous: posts[post['id']] = post['file_url']
                if len(posts) == limit: break
            c += 1
        return posts

    # Umbrella command structure to manage global, channel, and user blacklists
    @commands.group(aliases=['bl', 'b'], brief='Manage blacklists', description='Blacklist base command for managing blacklists\n\n`bl get [blacklist]` to show a blacklist\n`bl set [blacklist] [tags]` to replace a blacklist\n`bl clear [blacklist]` to clear a blacklist\n`bl add [blacklist] [tags]` to add tags to a blacklist\n`bl remove [blacklist] [tags]` to remove tags from a blacklist', usage='[flag] [blacklist] ([tags])')
    @checks.del_ctx()
    async def blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Use a flag to manage blacklists.**\n*Type* `' + ctx.prefix + 'help bl` *for more info.*', delete_after=10)
    @blacklist.error
    async def blacklist_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            return await ctx.send('❌ **Insufficient permissions.**')
        if isinstance(error, KeyError):
            return await ctx.send('❌ **Blacklist does not exist.**', delete_after=10)

    @blacklist.group(name='get', aliases=['g'])
    async def _get_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')
    @_get_blacklist.command(name='global', aliases=['gl', 'g'])
    async def __get_global_blacklist(self, ctx):
        global blacklists
        await ctx.send('🚫 **Global blacklist:**\n```' + formatter.tostring(blacklists['global_blacklist']) + '```')
    @_get_blacklist.command(name='channel', aliases=['ch', 'c'])
    async def __get_channel_blacklist(self, ctx):
        global blacklists
        if isinstance(ctx.message.guild, d.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        await ctx.send('🚫 <#' + str(channel.id) + '> **blacklist:**\n```' + formatter.tostring(blacklists['guild_blacklist'].get(str(guild.id), {}).get(str(channel.id), [])) + '```')
    @_get_blacklist.command(name='me', aliases=['m'])
    async def __get_user_blacklist(self, ctx):
        global blacklists
        user = ctx.message.author
        await ctx.send('🚫 ' + user.mention + '**\'s blacklist:**\n```' + formatter.tostring(blacklists['user_blacklist'].get(str(user.id), [])) + '```', delete_after=10)
    @_get_blacklist.command(name='here', aliases=['h'])
    async def __get_here_blacklists(self, ctx):
        global blacklists
        if isinstance(ctx.message.guild, d.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        await ctx.send('🚫 **__Blacklisted:__**\n\n**Global:**\n```' + formatter.tostring(blacklists['global_blacklist']) + '```\n**<#' + str(channel.id) + '>:**\n```' + formatter.tostring(blacklists['guild_blacklist'].get(str(guild.id), {}).get(str(channel.id), [])) + '```')
    @_get_blacklist.group(name='all', aliases=['a'])
    async def __get_all_blacklists(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')
    @__get_all_blacklists.command(name='guild', aliases=['g'])
    @commands.has_permissions(manage_channels=True)
    async def ___get_all_guild_blacklists(self, ctx):
        global blacklists
        if isinstance(ctx.message.guild, d.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        await ctx.send('🚫 **__' + guild.name + ' blacklists:__**\n\n' + formatter.dict_tostring(blacklists['guild_blacklist'].get(str(guild.id), {})))
    @__get_all_blacklists.command(name='user', aliases=['u', 'member', 'm'])
    @commands.is_owner()
    async def ___get_all_user_blacklists(self, ctx):
        global blacklists
        await ctx.send('🚫 **__User blacklists:__**\n\n' + formatter.dict_tostring(blacklists['user_blacklist']))

    @blacklist.group(name='add', aliases=['a'])
    async def _add_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')
    @_add_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __add_global_tags(self, ctx, *tags):
        global blacklists, aliases, HEADERS
        try:
            for tag in tags:
                if tag in blacklists['global_blacklist']:
                    raise exc.TagExists(tag)
            blacklists['global_blacklist'].extend(tags)
            for tag in tags:
                alias_request = requests.get('https://e621.net/tag_alias/index.json?aliased_to=' + tag + '&approved=true', headers=HEADERS).json()
                for dic in alias_request:
                    aliases['global_blacklist'].setdefault(tag, []).append(dic['name'])
            with open('blacklists.json', 'w') as outfile:
                json.dump(blacklists, outfile, indent=4, sort_keys=True)
            with open('aliases.json', 'w') as outfile:
                json.dump(aliases, outfile, indent=4, sort_keys=True)
            await ctx.send('✅ **Added to global blacklist:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
        except exc.TagExists as e:
            await ctx.send('❌ `' + str(e) + '` **already in blacklist.**', delete_after=10)
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()
    @_add_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __add_channel_tags(self, ctx, *tags):
        global blacklists, aliases, HEADERS
        if isinstance(ctx.message.guild, d.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        try:
            for tag in tags:
                if tag in blacklists['guild_blacklist'].get(str(guild.id), {}).get(str(channel.id), []):
                    raise exc.TagExists(tag)
            blacklists['guild_blacklist'].setdefault(str(guild.id), {}).setdefault(str(channel.id), []).extend(tags)
            for tag in tags:
                alias_request = requests.get('https://e621.net/tag_alias/index.json?aliased_to=' + tag + '&approved=true', headers=HEADERS).json()
                for dic in alias_request:
                    aliases['guild_blacklist'].setdefault(str(guild.id), {}).setdefault(str(channel.id), {}).setdefault(tag, []).append(dic['name'])
            with open('blacklists.json', 'w') as outfile:
                json.dump(blacklists, outfile, indent=4, sort_keys=True)
            with open('aliases.json', 'w') as outfile:
                json.dump(aliases, outfile, indent=4, sort_keys=True)
            await ctx.send('✅ **Added to** <#' + str(channel.id) + '> **blacklist:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
        except exc.TagExists as e:
            await ctx.send('❌ `' + str(e) + '` **already in blacklist.**', delete_after=10)
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()
    @_add_tags.command(name='me', aliases=['m'])
    async def __add_user_tags(self, ctx, *tags):
        global blacklists, aliases, HEADERS
        user = ctx.message.author
        try:
            for tag in tags:
                if tag in blacklists['user_blacklist'].get(str(user.id), []):
                    raise exc.TagExists(tag)
            blacklists['user_blacklist'].setdefault(str(user.id), []).extend(tags)
            for tag in tags:
                alias_request = requests.get('https://e621.net/tag_alias/index.json?aliased_to=' + tag + '&approved=true', headers=HEADERS).json()
                for dic in alias_request:
                    aliases['user_blacklist'].setdefault(str(user.id), {}).setdefault(tag, []).append(dic['name'])
            with open('blacklists.json', 'w') as outfile:
                json.dump(blacklists, outfile, indent=4, sort_keys=True)
            with open('aliases.json', 'w') as outfile:
                json.dump(aliases, outfile, indent=4, sort_keys=True)
            await ctx.send('✅ ' + user.mention + ' **added:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
        except exc.TagExists as e:
            await ctx.send('❌ `' + str(e) + '` **already in blacklist.**', delete_after=10)
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()

    @blacklist.group(name='remove', aliases=['rm', 'r'])
    async def _remove_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')
    @_remove_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __remove_global_tags(self, ctx, *tags):
        global blacklists, aliases
        try:
            for tag in tags:
                if tag in blacklists['global_blacklist']:
                    blacklists['global_blacklist'].remove(tag)
                    del aliases['global_blacklist'][tag]
                else:
                    raise exc.TagError(tag)
            with open('blacklists.json', 'w') as outfile:
                json.dump(blacklists, outfile, indent=4, sort_keys=True)
            with open('aliases.json', 'w') as outfile:
                json.dump(aliases, outfile, indent=4, sort_keys=True)
            await ctx.send('✅ **Removed from global blacklist:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
        except exc.TagError as e:
            await ctx.send('❌ `' + str(e) + '` **not in blacklist.**', delete_after=10)
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()
    @_remove_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __remove_channel_tags(self, ctx, *tags):
        global blacklists, aliases
        if isinstance(ctx.message.guild, d.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        try:
            for tag in tags:
                if tag in blacklists['guild_blacklist'][str(guild.id)][str(channel.id)]:
                    blacklists['guild_blacklist'][str(guild.id)][str(channel.id)].remove(tag)
                    del aliases['guild_blacklist'][str(guild.id)][str(channel.id)][tag]
                else:
                    raise exc.TagError(tag)
            with open('blacklists.json', 'w') as outfile:
                json.dump(blacklists, outfile, indent=4, sort_keys=True)
            with open('aliases.json', 'w') as outfile:
                json.dump(aliases, outfile, indent=4, sort_keys=True)
            await ctx.send('✅ **Removed from** <#' + str(channel.id) + '> **blacklist:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
        except exc.TagError as e:
            await ctx.send('❌ `' + str(e) + '` **not in blacklist.**', delete_after=10)
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()
    @_remove_tags.command(name='me', aliases=['m'])
    async def __remove_user_tags(self, ctx, *tags):
        global blacklists, aliases
        user = ctx.message.author
        try:
            for tag in tags:
                if tag in blacklists['user_blacklist'][str(user.id)]:
                    blacklists['user_blacklist'][str(user.id)].remove(tag)
                    del aliases['user_blacklist'][str(user.id)][tag]
                else:
                    raise exc.TagError(tag)
            with open('blacklists.json', 'w') as outfile:
                json.dump(blacklists, outfile, indent=4, sort_keys=True)
            with open('aliases.json', 'w') as outfile:
                json.dump(aliases, outfile, indent=4, sort_keys=True)
            await ctx.send('✅ ' + user.mention + ' **removed:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
        except exc.TagError as e:
            await ctx.send('❌ `' + str(e) + '` **not in blacklist.**', delete_after=10)
        except Exception:
            await ctx.send('{}\n```{}```'.format(exc.base, tb.format_exc(limit=1)))
            tb.print_exc()

    @blacklist.group(name='clear', aliases=['cl', 'c'])
    async def _clear_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')
    @_clear_blacklist.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __clear_global_blacklist(self, ctx):
        global blacklists, aliases
        del blacklists['global_blacklist']
        del aliases['global_blacklist']
        with open('blacklists.json', 'w') as outfile:
            json.dump(blacklists, outfile, indent=4, sort_keys=True)
        with open('aliases.json', 'w') as outfile:
            json.dump(aliases, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ **Global blacklist cleared.**', delete_after=5)
    @_clear_blacklist.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __clear_channel_blacklist(self, ctx):
        global blacklists, aliases
        if isinstance(ctx.message.guild, d.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        del blacklists['guild_blacklist'][str(guild.id)][str(channel.id)]
        del aliases['guild_blacklist'][str(guild.id)][str(channel.id)]
        with open('blacklists.json', 'w') as outfile:
            json.dump(blacklists, outfile, indent=4, sort_keys=True)
        with open('aliases.json', 'w') as outfile:
            json.dump(aliases, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ <#' + str(channel.id) + '> **blacklist cleared.**', delete_after=5)
    @_clear_blacklist.command(name='me', aliases=['m'])
    async def __clear_user_blacklist(self, ctx):
        global blacklists, aliases
        user = ctx.message.author
        del blacklists['user_blacklist'][str(user.id)]
        del aliases['user_blacklist'][str(user.id)]
        with open('blacklists.json', 'w') as outfile:
            json.dump(blacklists, outfile, indent=4, sort_keys=True)
        with open('aliases.json', 'w') as outfile:
            json.dump(aliases, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ ' + user.mention + '**\'s blacklist cleared.**', delete_after=5)
