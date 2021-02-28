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

__version__ = "1.0.2"


class Parserr(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._headers = {'User-Agent': 'Python/3.8'}
        self._apikey = os.getenv("ARR_API_KEY")

    @commands.command()
    async def parse(self, ctx, release: str):
        """Parse release names from Arrs.

        If a program and branch are not specified, the server default will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        async with ctx.typing():
            url = f"https://dev.servarr.com/{ctx.guild}/nightly/api/parse?apikey={self._apikey}&title={release}"
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    parse_dict = json.loads(text)
                    version = "3.0"
                    embed = discord.Embed(title=f"{ctx.guild.name} Parse Result", description="", colour=await ctx.embed_colour())
                    embed.add_field(name="Attempted Release Title", value=parse_dict["title"] or "-", inline=False)

                    parsed_obj = parse_dict["parsedMovieInfo"]
                    language_string = ", ".join((o["name"] for o in parsed_obj["languages"])) or "-"
                    quality = parsed_obj["quality"]["quality"]["name"] or "-"
                    embed.add_field(name="Movie Title", value=parsed_obj["movieTitle"] or "-", inline=True)
                    embed.add_field(name="Year", value=parsed_obj["year"] or "-", inline=True)
                    embed.add_field(name="Edition", value=parsed_obj["edition"] or "-", inline=True)
                    embed.add_field(name="TMDBId", value=parsed_obj["tmdbId"] or "-", inline=True)
                    embed.add_field(name="IMDbId", value=parsed_obj["imdbId"] or "-", inline=True)
                    embed.add_field(name="Quality", value=quality, inline=True)
                    embed.add_field(name="Languages", value=language_string, inline=True)
                    embed.add_field(name="Group", value=parsed_obj["releaseGroup"] or "-", inline=True)

                    embed.set_footer(text=f"{ctx.guild} Version {version} | Branch Nightly")
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Parse error")
            else:
                return

    async def _get_url_content(self, url: str):
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(headers=self._headers, timeout=timeout) as session:
                async with session.get(url) as resp:
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

    async def _valid_url(self, ctx, url: str):
        try:
            result = urlparse(url)
        except Exception as e:
            log.exception(e, exc_info=e)
            await ctx.send("There was an issue trying to fetch that site. Please check your console for the error.")
            return None

        if all([result.scheme, result.netloc]):
            text = await self._get_url_content(url)
            if not text:
                await ctx.send("No text present at the given url.")
                return None
            else:
                return text
        else:
            await ctx.send(f"That url seems to be incomplete.")
            return None
