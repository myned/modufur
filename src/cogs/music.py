# import asyncio
# import json
# from datetime import datetime as dt
# from urllib import parse
# import re
# from pprint import pprint
#
# import discord as d
# from discord import errors as err
# from discord.ext import commands as cmds
# from discord.ext.commands import errors as errext
# import gmusicapi as gpm
# import googleapiclient as gapic
# import apiclient as apic
#
# from misc import exceptions as exc
# from misc import checks
# from utils import utils as u
#
#
# class Music:
#
#     def __init__(self, bot):
#         self.bot = bot
#
#         self.yt_service = apic.discovery.build('youtube', 'v3', developerKey=u.secrets['client_secrets']['client_secret'])
#
#     @cmds.group(aliases=['pl'], brief='(G) Play music', description='Play music from YouTube, Soundcloud, or Google Play Music')
#     async def play(self, ctx):
#         print(ctx.invoked_subcommand)
#
#     @play.command(name='youtube', aliases=['you', 'tube', 'yt', 'y'])
#     async def _play_youtube(self, ctx, *videos):
#         try:
#             if not videos:
#                 raise exc.MissingArgument
#
#             vids = []
#
#             for video in videos:
#                 if 'http' in video and 'youtube' in video:
#                     vids.append(parse.parse_qs(parse.urlparse(video).query)['v'][0])
#                 else:
#                     vids.append(video)
#
#             print(vids)
#
#             response = self.yt_service.videos().list(part='snippet', id=','.join(vids)).execute()
#             pprint(response)
#
#         except exc.MissingArgument:
#             await ctx.send('**Invalid youtube url or ID**', delete_after=7)
#             await ctx.message.add_reaction('\N{CROSS MARK}')
#
#     @play.command(name='googleplaymusic', aliases=['googleplay', 'googlemusic', 'playmusic', 'play', 'gpm'])
#     async def _play_googleplaymusic(self, ctx, query):
#         pass

import discord as d
from discord import errors as err
from discord.ext import commands as cmds
from discord.ext.commands import errors as errext
# import gmusicapi as gpm
# import googleapiclient as gapic
# import apiclient as apic

from misc import exceptions as exc
from misc import checks
from utils import utils as u


class Music:

    # def __init__(self, bot):
    #     self.bot = bot
    #
    #     self.yt_service = apic.discovery.build('youtube', 'v3', developerKey=u.secrets['client_secrets']['client_secret'])
    #
    # @cmds.group(aliases=['pl'], brief='(G) Play music', description='Play music from YouTube, Soundcloud, or Google Play Music')
    # async def play(self, ctx):
    #     print(ctx.invoked_subcommand)
    #
    # @play.command(name='youtube', aliases=['you', 'tube', 'yt', 'y'])
    # async def _play_youtube(self, ctx, *videos):
    #     try:
    #         if not videos:
    #             raise exc.MissingArgument
    #
    #         vids = []
    #
    #         for video in videos:
    #             if 'http' in video and 'youtube' in video:
    #                 vids.append(parse.parse_qs(parse.urlparse(video).query)['v'][0])
    #             else:
    #                 vids.append(video)
    #
    #         print(vids)
    #
    #         response = self.yt_service.videos().list(part='snippet', id=','.join(vids)).execute()
    #         pprint(response)
    #
    #     except exc.MissingArgument:
    #         await ctx.send('**Invalid youtube url or ID**', delete_after=7)
    #         await ctx.message.add_reaction('\N{CROSS MARK}')

    @play.command(name='googleplaymusic', aliases=['googleplay', 'googlemusic', 'playmusic', 'play', 'gpm'])
    async def _play_googleplaymusic(self, ctx, query):
        pass
