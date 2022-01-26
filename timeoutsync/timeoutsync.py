import asyncio
import aiohttp
import logging
import os
from datetime import datetime, timezone, timedelta
import discord

from redbot.core import checks, commands, modlog, Config

log = logging.getLogger("red.servarr.timeoutsync")


__version__ = "1.0.16"


class TimeoutSync(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._token = os.getenv("DISCORD_TOKEN")
        self._headers = {"Authorization": f"Bot {self._token}"}
        self._base = "https://discord.com/api/v9/"
        self.config = Config.get_conf(self, 23481236)
        self.config.register_global(sync_list=[], ban_queue=[])
        self.sync_list = ConfigLock(self.config.sync_list)

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

    @timeout.command(name="synctoggle", help="Toggle whether or not a server is synced given its ID")
    @checks.admin()
    @checks.bot_in_a_guild()
    async def syncserver(self, ctx, guild_id: int = None, *, dont_collect: bool = False):
        if guild_id is not None:
            guild = self.bot.get_guild(guild_id)
        else:
            guild = ctx.guild
        if guild is not None:
            id = guild.id
        else:
            return await ctx.send("Unknown id {0}".format(guild_id))

        key, sync_list = await self.sync_list.lock()
        in_list = id in sync_list
        if in_list:
            sync_list.remove(id)
            message = "Removed `{0}` from the sync list".format(guild.name)
        else:
            sync_list.append(id)
            message = "Added `{0}` to the sync list".format(guild.name)
        await self.sync_list.unlock(key, sync_list)
        if not in_list:
            await self.enact_bans(guild)
            if not dont_collect:
                await self.collect_guild_bans(guild)
        await ctx.send(message)

    @timeout.command(name="synclist", help="Print list of server set to be synced")
    @checks.admin()
    async def synclist(self, ctx):
        sync_list = await self.config.sync_list()
        message = "Synced servers: "
        for id in sync_list:
            guild = self.bot.get_guild(id)
            message += "**{0}** [{1}], ".format(guild.name, id)
        await ctx.send(message[:-2])

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

class AsyncLock:
    def __init__(self):
        self.lock_i = 0
        self.lock_active = None
    async def lock(self):
        i = self.lock_i + 1
        self.lock_i = i
        while self.lock_active is not None:
            await asyncio.sleep(0.1)
        self.lock_active = i
        value = await self._get()
        return (i, value)
    async def unlock(self, key, value=None):
        if key == self.lock_active:
            if value is not None:
                await self._set(value)
            self.lock_active = None
        else:
            raise RuntimeError('{0} is not active lock key'.format(key))

class ConfigLock(AsyncLock):
    def __init__(self, configItem):
        super().__init__()
        self._item = configItem
    async def _get(self):
        return await self._item()
    async def _set(self,value):
        return await self._item.set(value)