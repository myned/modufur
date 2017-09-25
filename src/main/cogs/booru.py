import json

try:
    with open('global_blacklist.json') as infile:
        global_blacklist = json.load(infile)
        print('\"global_blacklist.json\" loaded.')
except FileNotFoundError:
    with open('global_blacklist.json', 'w+') as iofile:
        print('Blacklist file not found: \"global_blacklist.json\" created.')
        json.dump([], iofile, indent=4, sort_keys=True)
        iofile.seek(0)
        global_blacklist = json.load(iofile)
try:
    with open('guild_blacklist.json') as infile:
        guild_blacklist = json.load(infile)
        print('\"guild_blacklist.json\" loaded.')
except FileNotFoundError:
    with open('guild_blacklist.json', 'w+') as iofile:
        print('Blacklist file not found: \"guild_blacklist.json\" created.')
        json.dump({}, iofile, indent=4, sort_keys=True)
        iofile.seek(0)
        guild_blacklist = json.load(iofile)
try:
    with open('user_blacklist.json') as infile:
        user_blacklist = json.load(infile)
        print('\"user_blacklist.json\" loaded.')
except FileNotFoundError:
    with open('user_blacklist.json', 'w+') as iofile:
        print('Blacklist file not found: \"user_blacklist.json\" created.')
        json.dump({}, iofile, indent=4, sort_keys=True)
        iofile.seek(0)
        user_blacklist = json.load(iofile)

import asyncio
import discord
import requests
import traceback
from discord import reaction
from discord.ext import commands
from discord.ext.commands import errors
from misc import checks
from misc import exceptions as exc
from utils import formatter, scraper

last_command = {}

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
            await ctx.send(exc.base)
            traceback.print_exc(limit=1)

    # Reverse image searches a linked image using the public iqdb
    @commands.command(name='reverse', aliases=['rev', 'ris'], brief='e621 Reverse image search', description='e621 | NSFW\nReverse-search an image with given URL')
    @checks.del_ctx()
    async def reverse_image_search(self, ctx, url):
        try:
            await ctx.trigger_typing()
            await ctx.send('✅ ' + ctx.message.author.mention + ' **Probable match:**\n' + scraper.check_match('http://iqdb.harry.lu/?url=' + url))
        except exc.MatchError:
            await ctx.send('❌ ' + ctx.message.author.mention + ' **No probable match.**', delete_after=10)
        except Exception:
            await ctx.send(exc.base)
            traceback.print_exc(limit=1)

    # Searches for and returns images from e621.net given tags when not blacklisted
    @commands.command(aliases=['e6', '6'], brief='e621 | NSFW', description='e621 | NSFW\nTag-based search for e621.net\n\nYou can only search 5 tags and 6 images at once for now.\ne6 [tags...] ([# of images])')
    @checks.del_ctx()
    @checks.is_nsfw()
    async def e621(self, ctx, *args):
        global global_blacklist, guild_blacklist, user_blacklist
        args = list(args)
        try:
            await ctx.trigger_typing()
            await self.check_send_urls(ctx, 'e621', args)
        except exc.TagBlacklisted as e:
            await ctx.send('❌ `' + str(e) + '` **blacklisted.**', delete_after=10)
        except exc.BoundsError as e:
            await ctx.send('❌ `' + str(e) + '` **out of bounds.**', delete_after=10)
        except exc.TagBoundsError as e:
            await ctx.send('❌ `' + str(e) + '` **out of bounds.** Tags limited to 5, currently.', delete_after=10)
        except Exception:
            await ctx.send(exc.base)
            traceback.print_exc()

    @e621.error
    async def e621_error(self, ctx, error):
        if isinstance(error, errors.CheckFailure):
            return await ctx.send('❌ <#' + str(ctx.message.channel.id) + '> **is not an NSFW channel.**', delete_after=10)

    # Searches for and returns images from e926.net given tags when not blacklisted
    @commands.command(aliases=['e9', '9'], brief='e926 | SFW', description='e926 | SFW\nTag-based search for e926.net\n\nYou can only search 5 tags and 6 images at once for now.\ne9 [tags...] ([# of images])')
    @checks.del_ctx()
    async def e926(self, ctx, *args):
        global global_blacklist, guild_blacklist, user_blacklist
        args = list(args)
        try:
            await ctx.trigger_typing()
            await self.check_send_urls(ctx, 'e926', args)
        except exc.TagBlacklisted as e:
            await ctx.send('❌ `' + str(e) + '` **blacklisted.**', delete_after=10)
        except exc.BoundsError as e:
            await ctx.send('❌ `' + str(e) + '` **out of bounds.**', delete_after=10)
        except exc.TagBoundsError as e:
            await ctx.send('❌ `' + str(e) + '` **out of bounds.** Tags limited to 5, currently.', delete_after=10)
        except Exception:
            await ctx.send(exc.base)
            traceback.print_exc(limit=1)

    # Messy code that checks image limit and tags in blacklists
    async def check_send_urls(self, ctx, booru, args):
        global global_blacklist, guild_blacklist, user_blacklist
        if isinstance(ctx.message.guild, discord.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        user = ctx.message.author
        urls = []
        limit = 1
        # Checks if tags are in the file blacklists
        if args:
            for tag in args:
                if tag == 'swf' or tag == 'webm' or tag in global_blacklist or tag in guild_blacklist.get(str(guild.id), {}).get(str(channel.id), []) or tag in user_blacklist.get(str(user.id), []):
                    raise exc.TagBlacklisted(tag)
        if len(args) > 5:
            raise exc.TagBoundsError(formatter.tostring(args[5:]))
        # Checks for, defines, and removes limit from end of args
        if args and len(args[-1]) == 1:
            if int(args[-1]) <= 6 and int(args[-1]) >= 1:
                limit = int(args[-1])
                args.pop()
            else:
                raise exc.BoundsError(args[-1])
        # Checks for blacklisted tags in endpoint blacklists - try/except is for continuing the parent loop
        while len(urls) < limit:
            request = requests.get('https://' + booru + '.net/post/index.json?limit=6&tags=order:random' + formatter.tostring_commas(args)).json()
            for post in request:
                if 'swf' in post['file_ext'] or 'webm' in post['file_ext']:
                    continue
                try:
                    for tag in global_blacklist:
                        if tag in post['tags']:
                            raise exc.Continue
                    for tag in guild_blacklist.get(str(guild.id), {}).get(str(channel.id), []):
                        if tag in post['tags']:
                            raise exc.Continue
                    for tag in user_blacklist.get(str(user.id), []):
                        if tag in post['tags']:
                            raise exc.Continue
                except exc.Continue:
                    continue
                if post['file_url'] not in urls:
                    urls.append(post['file_url'])
                if len(urls) == limit:
                    break
        for url in urls:
            await ctx.send('`' + formatter.tostring(args) + '`\n' + url)

    # Umbrella command structure to manage global, channel, and user blacklists
    @commands.group(aliases=['bl', 'b'], brief='Manage blacklists', description='Blacklist base command for managing blacklists\n\n`bl get [blacklist]` to show a blacklist\n`bl set [blacklist] [tags]` to replace a blacklist\n`bl clear [blacklist]` to clear a blacklist\n`bl add [blacklist] [tags]` to add tags to a blacklist\n`bl remove [blacklist] [tags]` to remove tags from a blacklist', usage='[flag] [blacklist] ([tags])')
    @checks.del_ctx()
    async def blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Use a flag to manage blacklists.**\n*Type* `' + ctx.prefix + 'help bl` *for more info.*', delete_after=10)

    @blacklist.error
    async def blacklist_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            return await ctx.send('❌ **Insufficient permissions.**', delete_after=10)
        if isinstance(error, exc.TagExists):
            return await ctx.send('❌ `' + str(exc.TagExists) + '` **already in blacklist.**', delete_after=10)
        if isinstance(error, exc.TagError):
            return await ctx.send('❌ `' + str(exc.TagError) + '` **not in blacklist.**', delete_after=10)
        if isinstance(error, KeyError):
            return await ctx.send('❌ **Blacklist does not exist.**', delete_after=10)

    @blacklist.command(name='update', aliases=['upd', 'up'])
    async def _update_blacklists(self, ctx):
        global global_blacklist, guild_blacklist, user_blacklist
        with open('global_blacklist.json', 'w') as outfile:
            json.dump(global_blacklist, outfile, indent=4, sort_keys=True)
        with open('guild_blacklist.json', 'w') as outfile:
            json.dump(guild_blacklist, outfile, indent=4, sort_keys=True)
        with open('user_blacklist.json', 'w') as outfile:
            json.dump(user_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ **Blacklists updated.**')

    @blacklist.group(name='get', aliases=['g'])
    async def _get_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')

    @_get_blacklist.command(name='global', aliases=['gl', 'g'])
    async def __get_global_blacklist(self, ctx):
        global global_blacklist
        await ctx.send('🚫 **Global blacklist:**\n```' + formatter.tostring(global_blacklist) + '```')
    @_get_blacklist.command(name='channel', aliases=['ch', 'c'])
    async def __get_channel_blacklist(self, ctx):
        global guild_blacklist
        if isinstance(ctx.message.guild, discord.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        await ctx.send('🚫 <#' + str(channel.id) + '> **blacklist:**\n```' + formatter.tostring(guild_blacklist.get(str(guild.id), {}).get(str(channel.id), [])) + '```')
    @_get_blacklist.command(name='me', aliases=['m'])
    async def __get_user_blacklist(self, ctx):
        global user_blacklist
        user = ctx.message.author
        await ctx.send('🚫 ' + user.mention + '**\'s blacklist:**\n```' + formatter.tostring(user_blacklist.get(str(user.id), [])) + '```', delete_after=10)
    @_get_blacklist.command(name='here', aliases=['h'])
    async def __get_here_blacklists(self, ctx):
        global global_blacklist, guild_blacklist
        if isinstance(ctx.message.guild, discord.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        await ctx.send('🚫 **__Blacklisted:__**\n\n**Global:**\n```' + formatter.tostring(global_blacklist) + '```\n**<#' + str(channel.id) + '>:**\n```' + formatter.tostring(guild_blacklist.get(str(guild.id), {}).get(str(channel.id), [])) + '```')
    @_get_blacklist.group(name='all', aliases=['a'])
    async def __get_all_blacklists(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')

    @__get_all_blacklists.command(name='guild', aliases=['g'])
    @commands.has_permissions(manage_channels=True)
    async def ___get_all_guild_blacklists(self, ctx):
        global guild_blacklist
        if isinstance(ctx.message.guild, discord.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        await ctx.send('🚫 **__' + guild.name + ' blacklists:__**\n\n' + formatter.dict_tostring(guild_blacklist.get(str(guild.id), {})))
    @__get_all_blacklists.command(name='user', aliases=['u', 'member', 'm'])
    @commands.is_owner()
    async def ___get_all_user_blacklists(self, ctx):
        global user_blacklist
        await ctx.send('🚫 **__User blacklists:__**\n\n' + formatter.dict_tostring(user_blacklist))

    @blacklist.group(name='add', aliases=['a'])
    async def _add_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')

    @_add_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __add_global_tags(self, ctx, *tags):
        global global_blacklist
        for tag in tags:
            if tag in global_blacklist:
                raise exc.TagExists(tag)
        global_blacklist.extend(tags)
        with open('global_blacklist.json', 'w') as outfile:
            json.dump(global_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ **Added to global blacklist:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
    @_add_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __add_channel_tags(self, ctx, *tags):
        global guild_blacklist
        if isinstance(ctx.message.guild, discord.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        for tag in tags:
            if tag in guild_blacklist.get(str(guild.id), {}).get(str(channel.id), []):
                raise exc.TagExists(tag)
        guild_blacklist.setdefault(str(guild.id), {}).setdefault(str(channel.id), []).extend(tags)
        with open('guild_blacklist.json', 'w') as outfile:
            json.dump(guild_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ **Added to** <#' + str(channel.id) + '> **blacklist:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
    @_add_tags.command(name='me', aliases=['m'])
    async def __add_user_tags(self, ctx, *tags):
        global user_blacklist
        user = ctx.message.author
        for tag in tags:
            if tag in user_blacklist.get(str(user.id), []):
                raise exc.TagExists(tag)
        user_blacklist.setdefault(str(user.id), []).extend(tags)
        with open('user_blacklist.json', 'w') as outfile:
            json.dump(user_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ ' + user.mention + ' **added:**\n```' + formatter.tostring(tags) + '```', delete_after=5)

    @blacklist.group(name='remove', aliases=['rm', 'r'])
    async def _remove_tags(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')

    @_remove_tags.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __remove_global_tags(self, ctx, *tags):
        global global_blacklist
        for tag in tags:
            if tag in global_blacklist:
                global_blacklist.remove(tag)
            else:
                raise exc.TagError(tag)
        with open('global_blacklist.json', 'w') as outfile:
            json.dump(global_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ **Removed from global blacklist:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
    @_remove_tags.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __remove_channel_tags(self, ctx, *tags):
        global guild_blacklist
        if isinstance(ctx.message.guild, discord.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        for tag in tags:
            if tag in guild_blacklist.get(str(guild.id), {}).get(str(channel.id), []):
                guild_blacklist.get(str(guild.id), {})[str(channel.id)].remove(tag)
            else:
                raise exc.TagError(tag)
        with open('guild_blacklist.json', 'w') as outfile:
            json.dump(guild_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ **Removed from** <#' + str(channel.id) + '> **blacklist:**\n```' + formatter.tostring(tags) + '```', delete_after=5)
    @_remove_tags.command(name='me', aliases=['m'])
    async def __remove_user_tags(self, ctx, *tags):
        global user_blacklist
        user = ctx.message.author
        for tag in tags:
            if tag in user_blacklist.get(str(user.id), []):
                user_blacklist.get[str(user.id)].remove(tag)
            else:
                raise exc.TagError(tag)
        with open('user_blacklist.json', 'w') as outfile:
            json.dump(user_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ ' + user.mention + ' **removed:**\n```' + formatter.tostring(tags) + '```', delete_after=5)

    @blacklist.group(name='set', aliases=['s'])
    async def _set_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')

    @_set_blacklist.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __set_global_blacklist(self, ctx, *tags):
        global global_blacklist
        global_blacklist = tags[:]
        with open('global_blacklist.json', 'w') as outfile:
            json.dump(global_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ **Global blacklist set to:**\n```' + formatter.tostring(global_blacklist) + '```', delete_after=10)
    @_set_blacklist.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __set_channel_blacklist(self, ctx, *tags):
        global guild_blacklist
        if isinstance(ctx.message.guild, discord.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        guild_blacklist.setdefault(str(guild.id), {})[str(channel.id)] = tags[:]
        with open('guild_blacklist.json', 'w') as outfile:
            json.dump(guild_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ <#' + str(channel.id) + '> **blacklist set to:**\n```' + formatter.tostring(guild_blacklist.get(str(guild.id), {}).get(str(channel.id), [])) + '```', delete_after=10)
    @_set_blacklist.command(name='me', aliases=['m'])
    async def __set_user_blacklist(self, ctx, *tags):
        global user_blacklist
        user = ctx.message.author
        user_blacklist[str(user.id)] = tags[:]
        with open('user_blacklist.json', 'w') as outfile:
            json.dump(user_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ ' + user.mention + '**\'s blacklist set to:**\n```' + formatter.tostring(user_blacklist.get(str(user.id), [])) + '```', delete_after=10)

    @blacklist.group(name='clear', aliases=['cl', 'c'])
    async def _clear_blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('❌ **Invalid blacklist.**')

    @_clear_blacklist.command(name='global', aliases=['gl', 'g'])
    @commands.is_owner()
    async def __clear_global_blacklist(self, ctx):
        global global_blacklist
        del global_blacklist
        with open('global_blacklist.json', 'w') as outfile:
            json.dump(global_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ **Global blacklist cleared.**', delete_after=5)
    @_clear_blacklist.command(name='channel', aliases=['ch', 'c'])
    @commands.has_permissions(manage_channels=True)
    async def __clear_channel_blacklist(self, ctx):
        global guild_blacklist
        if isinstance(ctx.message.guild, discord.Guild):
            guild = ctx.message.guild
        else:
            guild = ctx.message.channel
        channel = ctx.message.channel
        del guild_blacklist.get(str(guild.id), {})[str(channel.id)]
        with open('guild_blacklist.json', 'w') as outfile:
            json.dump(guild_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ <#' + str(channel.id) + '> **blacklist cleared.**', delete_after=5)
    @_clear_blacklist.command(name='me', aliases=['m'])
    async def __clear_user_blacklist(self, ctx):
        global user_blacklist
        user = ctx.message.author
        del user_blacklist[str(user.id)]
        with open('user_blacklist.json', 'w') as outfile:
            json.dump(user_blacklist, outfile, indent=4, sort_keys=True)
        await ctx.send('✅ ' + user.mention + '**\'s blacklist cleared.**', delete_after=5)
