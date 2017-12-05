import asyncio
import json
from datetime import datetime as dt

import discord as d
from discord import errors as err
from discord.ext import commands as cmds
from discord.ext.commands import errors as errext
import gmusicapi as gpm

from misc import exceptions as exc
from misc import checks
from utils import utils as u


class Post:

    def __init__(self, bot):
        self.bot = bot
