import asyncio
import discord
import httplib2
import mimetypes
import os
import requests_oauthlib as ro
import tempfile
import traceback
import webbrowser
from discord.ext import commands
from cogs import booru
from misc import checks
from misc import exceptions as exc
from utils import formatter

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets

# flow = flow_from_clientsecrets('../client_secrets.json', scope='https://www.googleapis.com/auth/youtube.upload', login_hint='botmyned@gmail.com', redirect_uri='urn:ietf:wg:oauth:2.0:oob')
# flow.params['access_type'] = 'offline'
# webbrowser.open_new(flow.step1_get_authorize_url())
# credentials = flow.step2_exchange(input('Authorization code: '))
# youtube = build('youtube', 'v3', http=credentials.authorize(httplib2.Http()))

tempfile.tempdir = '../temp'

command_dict = {}

class Utils:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='last', aliases=['l', ','], brief='Reinvokes last command', description='Reinvokes previous command executed', hidden=True)
    async def last_command(self, ctx):
        global command_dict
        try:
            if command_dict.get(str(ctx.message.author.id), {}).get('args', None) is not None:
                args = command_dict.get(str(ctx.message.author.id), {})['args']
            print(command_dict)
            await ctx.invoke(command_dict.get(str(ctx.message.author.id), {}).get('command', None), args)
        except Exception:
            await ctx.send(exc.base + '\n```python' + traceback.format_exc(limit=1) + '```')
            traceback.print_exc(limit=1)

    # [prefix]ping -> Pong!
    @commands.command(aliases=['p'], brief='Pong!', description='Returns latency from bot to Discord servers, not to user')
    @checks.del_ctx()
    async def ping(self, ctx):
        global command_dict
        try:
            await ctx.send(ctx.message.author.mention + '  🏓  `' + str(int(self.bot.latency * 1000)) + 'ms`', delete_after=5)
        except Exception:
            await ctx.send(exc.base + '\n```python' + traceback.format_exc(limit=1) + '```')
            traceback.print_exc(limit=1)
        command_dict.setdefault(str(ctx.message.author.id), {}).update({'command': ctx.command})

    @commands.command(aliases=['pre'], brief='List bot prefixes', description='Shows all used prefixes')
    @checks.del_ctx()
    async def prefix(self, ctx):
        try:
            await ctx.send('**Prefix:** `,` or ' + ctx.me.mention)
        except Exception:
            await ctx.send(exc.base + '\n```python' + traceback.format_exc(limit=1) + '```')
            traceback.print_exc(limit=1)

    @commands.group(name=',send', aliases=[',s'], hidden=True)
    @commands.is_owner()
    @checks.del_ctx()
    async def send(self, ctx):
        pass

    @send.command(name='guild', aliases=['g', 'server', 's'])
    async def send_guild(self, ctx, guild, channel, *message):
        await discord.utils.get(self.bot.get_all_channels(), guild__name=guild, name=channel).send(formatter.tostring(message))
    @send.command(name='user', aliases=['u', 'member', 'm'])
    async def send_user(self, ctx, user, *message):
        await discord.utils.get(self.bot.get_all_members(), id=int(user)).send(formatter.tostring(message))

    @commands.command(aliases=['up', 'u', 'vid', 'v'])
    @checks.is_listed()
    async def upload(self, ctx):
        global youtube
        try:
            print(mimetypes.guess_type(ctx.message.attachments[0].filename))
            with tempfile.TemporaryFile() as temp:
                await ctx.message.attachments[0].save(temp)
                print(os.path.basename('../temp/*'))
                print(mimetypes.guess_type(os.path.basename('../temp/*')))
            # print('https://www.youtube.com/watch?v=' + youtube.videos().insert(part='snippet', body={'categoryId': '24', 'title': 'Test'}, media_body=MediaFileUpload('../temp/*', chunksize=-1))
        except Exception:
            await ctx.send(exc.base + '\n```python' + traceback.format_exc(limit=1) + '```')
            traceback.print_exc(limit=1)
