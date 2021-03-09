import asyncio
import aiohttp
import logging
import json
from urllib.parse import urlparse

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

log = logging.getLogger("red.servarr.radarrmeta")


__version__ = "1.1.2"


class RadarrMeta(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._headers = {'User-Agent': 'Python/3.8'}

    @commands.command()
    async def tmdb(self, ctx, tmdb_id: str):
        """
        Input a TMDbId to lookup.
        """
        async with ctx.typing():
            url = "https://radarrapi.servarr.com/v1/movie/" + tmdb_id
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    movie_dict = json.loads(text)
                    poster = ""
                    for dest in movie_dict["Images"]:
                        if dest["CoverType"] == "Poster":
                            poster = dest["Url"]
                    embed = discord.Embed(title=movie_dict["Title"], description="", colour=await ctx.embed_colour())
                    embed.add_field(name="Overview", value=movie_dict["Overview"] or "-")
                    embed.add_field(name="Year", value=movie_dict["Year"] or "-", inline=False)
                    embed.add_field(name="Studio", value=movie_dict["Studio"] or "-", inline=False)
                    embed.set_thumbnail(url=poster)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("TmdbId not found")
            else:
                return

    @commands.command()
    async def imdb(self, ctx, imdb_id: str):
        """
        Input a IMDb Id to lookup.
        """
        async with ctx.typing():
            url = "https://radarrapi.servarr.com/v1/movie/imdb/" + imdb_id
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    movie_dict = json.loads(text)
                    if len(movie_dict) > 0:
                        poster = ""
                        for dest in movie_dict[0]["Images"]:
                            if dest["CoverType"] == "Poster":
                                poster = dest["Url"]
                        embed = discord.Embed(title=movie_dict[0]["Title"], description="", colour=await ctx.embed_colour())
                        embed.add_field(name="Overview", value=movie_dict[0]["Overview"] or "-")
                        embed.add_field(name="Year", value=movie_dict[0]["Year"] or "-", inline=False)
                        embed.add_field(name="Studio", value=movie_dict[0]["Studio"] or "-", inline=False)
                        embed.set_thumbnail(url=poster)
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("ImdbId doesn't exist or isn't on TMDb")
                else:
                    await ctx.send("ImdbId doesn't exist or isn't on TMDb")
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
