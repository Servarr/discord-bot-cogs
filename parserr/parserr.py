import asyncio
import aiohttp
import logging
import os
import json
from urllib.parse import urlparse

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

log = logging.getLogger("red.servarr.parserr")

__version__ = "1.0.1"


class Parserr(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.admin_or_permissions(administrator=True)
    async def envtest(self, ctx, envstr: str):
        """
        Input a Env variable to Read
        """
        async with ctx.typing():
            if os.getenv(envstr):
                await ctx.send(os.getenv(envstr))
            else:
                await ctx.send(f"{envstr} does not exist")
