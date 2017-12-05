import asyncio
from datetime import datetime as dt
import mimetypes
import os
import tempfile
import traceback as tb
import webbrowser

import discord as d
import httplib2
import requests_oauthlib as ro
from apiclient import http
from apiclient.discovery import build
from discord.ext import commands as cmds
from oauth2client.client import flow_from_clientsecrets

#from run import config
from cogs import booru
from misc import exceptions as exc
from misc import checks
from utils import utils as u
from utils import formatter

youtube = None

tempfile.tempdir = os.getcwd()


class Utils:

    def __init__(self, bot):
        self.bot = bot

    @cmds.command(name='lastcommand', aliases=['last', 'l', ','], brief='Reinvokes last successful command', description='Executes last successfully executed command')
    async def last_command(self, ctx, arg='None'):
        try:
            context = u.last_commands[ctx.author.id]

            if arg == 'show' or arg == 'sh' or arg == 's':
                await ctx.send(f'`{context.prefix}{context.invoked_with} {" ".join(context.args[2:])}`', delete_after=7)
            else:
                await ctx.invoke(context.command, *context.args[2:], **context.kwargs)

        except KeyError:
            await ctx.send('**No last command**', delete_after=7)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    # Displays latency
    @cmds.command(aliases=['p'], brief='Pong!', description='Returns latency from bot to Discord servers, not to user')
    async def ping(self, ctx):
        await ctx.message.add_reaction('\N{TABLE TENNIS PADDLE AND BALL}')
        await ctx.send(ctx.author.mention + '  \N{TABLE TENNIS PADDLE AND BALL}  `' + str(round(self.bot.latency * 1000)) + 'ms`', delete_after=5)

    @cmds.command(aliases=['pre'], brief='List bot prefixes', description='Shows all used prefixes')
    async def prefix(self, ctx):
        await ctx.send('**Prefix:** `{}`'.format('` or `'.join(u.settings['prefixes'][ctx.guild.id] if ctx.guild.id in u.settings['prefixes'] else u.config['prefix'])))

    @cmds.group(name=',send', aliases=[',s'], hidden=True)
    @cmds.is_owner()
    async def send(self, ctx):
        pass

    @send.command(name='guild', aliases=['g', 'server', 's'])
    async def send_guild(self, ctx, guild, channel, *, message):
        try:
            tempchannel = d.utils.find(lambda m: m.name == channel, d.utils.find(
                lambda m: m.name == guild, self.bot.guilds).channels)

            try:
                await tempchannel.send(message)

            except AttributeError:
                await ctx.send('**Invalid channel**', delete_after=7)
                await ctx.message.add_reaction('\N{CROSS MARK}')

        except AttributeError:
            await ctx.send('**Invalid guild**', delete_after=7)
            await ctx.message.add_reaction('\N{CROSS MARK}')

    @send.command(name='user', aliases=['u', 'member', 'm'])
    async def send_user(self, ctx, user, *, message):
        await d.utils.get(self.bot.get_all_members(), id=int(user)).send(message)

    @cmds.command(aliases=['authenticateupload', 'authupload', 'authup', 'auth'], hidden=True)
    async def authenticate_upload(self, ctx):
        global youtube
        flow = flow_from_clientsecrets('client_secrets.json', scope='https://www.googleapis.com/auth/youtube.upload',
                                       login_hint='botmyned@gmail.com', redirect_uri='urn:ietf:wg:oauth:2.0:oob')
        flow.params['access_type'] = 'offline'
        webbrowser.open_new_tab(flow.step1_get_authorize_url())
        credentials = flow.step2_exchange(input('Authorization code: '))
        youtube = build('youtube', 'v3', http=credentials.authorize(http.build_http()))
        print('Service built.')

    @cmds.command(aliases=['up', 'u', 'vid', 'v'], hidden=True)
    @cmds.has_permissions(administrator=True)
    async def upload(self, ctx):
        global youtube
        attachments = ctx.message.attachments
        try:
            if not attachments:
                raise exc.MissingAttachment
            if len(attachments) > 1:
                raise exc.TooManyAttachments(len(attachments))
            mime = mimetypes.guess_type(attachments[0].filename)[0]
            if 'video/' in mime:
                with tempfile.NamedTemporaryFile() as temp:
                    await attachments[0].save(temp)
            else:
                raise exc.InvalidVideoFile(mime)
            print('https://www.youtube.com/watch?v=' + youtube.videos().insert(part='snippet',
                                                                               body={'categoryId': '24', 'title': 'Test'}, media_body=http.MediaFileUpload(temp.name, chunksize=-1)))
        except exc.InvalidVideoFile as e:
            await ctx.send('`' + str(e) + '` **invalid video type**', delete_after=7)
        except exc.TooManyAttachments as e:
            await ctx.send('`' + str(e) + '` **too many attachments.** Only one attachment is permitted to upload.', delete_after=7)
        except exc.MissingAttachment:
            await ctx.send('**Missing attachment**', delete_after=7)

    @upload.error
    async def upload_error(self, ctx, error):
        pass
# http.
