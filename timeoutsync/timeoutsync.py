import asyncio
import aiohttp
import logging
import os
import datetime
import json
from urllib.parse import urlparse

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

log = logging.getLogger("red.servarr.timeoutsync")


__version__ = "1.0.10"


class TimeoutSync(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._token = os.getenv("TOKEN")
        self._headers = {"Authorization": f"Bot {self._token}"}

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def timeout(self, ctx, user_id: str, time_in_mins: int):
        """
        Timeout User

        **Arguments:**

        - `<user>` The user to timeout.
        - `<timout>` The time in minutes.
        """

        async with ctx.typing():
            base = "https://discord.com/api/v9/"

            endpoint = f'guilds/{ctx.guild.id}/members/{user_id}'
            url = base + endpoint

            timeout = (datetime.datetime.utcnow() + datetime.timedelta(minutes=time_in_mins)).isoformat()
            json = {'communication_disabled_until': timeout}

            ctx.send(json.dumps(self.bot))

            text = await self._get_url_content(url, json)
            if text:
                await ctx.send(text)
            else:
                await ctx.send(text)

    async def _get_url_content(self, url: str, json: str):
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(headers=self._headers, timeout=timeout) as session:
                async with session.patch(url, json=json) as resp:
                    text = await resp.text()
            return text
        except aiohttp.client_exceptions.ClientConnectorError:
            log.error(f"aiohttp failure accessing site at url:\n\t{url}", exc_info=True)
            return None
        except asyncio.exceptions.TimeoutError:
            log.error(f"asyncio timeout while accessing feed at url:\n\t{url}")
            return None
        except Exception:
            log.error(f"General failure accessing site at url:\n\t{url}", exc_info=True)
            return None
