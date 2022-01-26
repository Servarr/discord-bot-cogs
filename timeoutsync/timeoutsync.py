import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timezone, timedelta
import discord

from redbot.core import checks, commands, modlog

log = logging.getLogger("red.servarr.timeoutsync")


__version__ = "1.0.14"


class TimeoutSync(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, **kwargs):
        self.bot = kwargs.get("bot")
        self.config = kwargs.get("config")

        self._token = os.getenv("DISCORD_TOKEN")
        self._headers = {"Authorization": f"Bot {self._token}"}
        self._base = "https://discord.com/api/v9/"

    @commands.command()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def timeout(self, ctx, member: discord.Member, time_in_mins: int, *, reason: str = None):
        """
        Timeout User

        **Arguments:**

        - `<user>` The user to timeout.
        - `<timout>` The time in minutes.
        - `<reason>` Why was the user timed out (Optional).
        """
        author = ctx.author
        guild = ctx.guild

        all_guilds = await self.config.all_guilds()

        if author == member:
            await ctx.send("I cannot let you do that. Self-harm is bad")
            return
        elif ctx.guild.me.top_role <= member.top_role or member == ctx.guild.owner:
            await ctx.send("I cannot do that due to Discord hierarchy rules.")
            return

        async with ctx.typing():
            endpoint = f'guilds/{guild.id}/members/{member.id}'
            url = self._base + endpoint

            timeout = (datetime.utcnow() + timedelta(minutes=time_in_mins)).isoformat()
            json = {'communication_disabled_until': timeout}

            text = await self._get_url_content(url, json)
            if text:
                await modlog.create_case(
                    self.bot,
                    guild,
                    ctx.message.created_at.replace(tzinfo=timezone.utc),
                    "timeout",
                    member,
                    author,
                    reason,
                    until=None,
                    channel=None,
                )

                await ctx.send(f'Done, user {member.name} has been put to sleep for {time_in_mins} minutes')
            else:
                await ctx.send(f'Unable to timout user {member.name}')

    async def _get_url_content(self, url: str, json: str):
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(headers=self._headers, timeout=timeout) as session:
                async with session.patch(url, json=json) as resp:
                    if resp.status in range(200, 300):
                        return await resp.text()
                    else:
                        log.error(f"aiohttp unexpected response from url:\n\t{url}", exc_info=True)
                        return None
        except aiohttp.client_exceptions.ClientConnectorError:
            log.error(f"aiohttp failure accessing site at url:\n\t{url}", exc_info=True)
            return None
        except asyncio.exceptions.TimeoutError:
            log.error(f"asyncio timeout while accessing feed at url:\n\t{url}")
            return None
        except Exception:
            log.error(f"General failure accessing site at url:\n\t{url}", exc_info=True)
            return None
