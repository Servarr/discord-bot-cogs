import asyncio
import aiohttp
import logging
import json
from urllib.parse import urlparse

import discord
#from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

log = logging.getLogger("red.servarr.radarrmeta")


__version__ = "1.1.23"


class RadarrMeta(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._headers = {'User-Agent': 'Python/3.8'}

    @commands.group(invoke_without_command=True)
    async def movie(self, ctx, *, movie: str):
        """
        Base command for movie lookup.

        **Arguments:**

        - `<movie>` The title to lookup, may include year.
        """
        async with ctx.typing():
            url = "https://api.radarr.video/v1/search?q=" + movie
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    movie_dict = json.loads(text)
                    if len(movie_dict) > 0:
                        await ctx.send(embed=self._get_movie_embed(movie_dict[0]))
                    else:
                        await ctx.send("Movie not found.")
                else:
                    await ctx.send("Movie not found")
            else:
                return

    @commands.group(invoke_without_command=True)
    async def tv(self, ctx, *, show: str):
        """
        Base command for tv show lookup.

        **Arguments:**

        - `<show>` The title to lookup.
        """
        async with ctx.typing():
            url = "https://skyhook.sonarr.tv/v1/tvdb/search/en/?term=" + show
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    show_dict = json.loads(text)
                    if len(show_dict) > 0:
                        await ctx.send(embed=self._get_tv_embed(show_dict[0]))
                    else:
                        await ctx.send("Show not found.")
                else:
                    await ctx.send("Show not found")
            else:
                return

    @commands.group(invoke_without_command=True)
    async def music(self, ctx, *, artist: str):
        """
        Base command for music lookup.

        **Arguments:**

        - `<artist>` The title to lookup.
        """
        async with ctx.typing():
            url = "https://api.lidarr.audio/api/v0.4/search?type=artist&query=" + artist
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    show_dict = json.loads(text)
                    if len(show_dict) > 0:
                        await ctx.send(embed=self._get_artist_embed(show_dict[0]))
                    else:
                        await ctx.send("Music not found.")
                else:
                    await ctx.send("Music not found")
            else:
                return

    @movie.command(invoke_without_command=True)
    async def tmdb(self, ctx, tmdb_id: str):
        """
        Input a TMDbId to lookup.
        """
        async with ctx.typing():
            url = "https://api.radarr.video/v1/movie/" + tmdb_id
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    movie_dict = json.loads(text)
                    await ctx.send(embed=self._get_movie_embed(movie_dict))
                else:
                    await ctx.send("TmdbId not found")
            else:
                return

    @movie.command(invoke_without_command=True)
    async def imdb(self, ctx, imdb_id: str):
        """
        Input a IMDb Id to lookup.
        """
        async with ctx.typing():
            url = "https://api.radarr.video/v1/movie/imdb/" + imdb_id
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    movie_dict = json.loads(text)
                    if len(movie_dict) > 0:
                        await ctx.send(embed=self._get_movie_embed(movie_dict[0]))
                    else:
                        await ctx.send("ImdbId doesn't exist or isn't on TMDb")
                else:
                    await ctx.send("ImdbId doesn't exist or isn't on TMDb")
            else:
                return
    
    @tv.command(invoke_without_command=True)
    async def tvdb(self, ctx, tvdb_id: str):
        """
        Input a TVDbId to lookup.
        """
        async with ctx.typing():
            url = "https://skyhook.sonarr.tv/v1/tvdb/shows/en/" + tvdb_id
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    show_dict = json.loads(text)
                    await ctx.send(embed=self._get_tv_embed(show_dict))
                else:
                    await ctx.send("TvdbId not found")
            else:
                return

    @staticmethod
    def _get_movie_embed(movie):
        poster = ""
        fanart = ""
        certification = ""

        if "Images" in movie:
            for dest in movie["Images"]:
                if dest["CoverType"] == "Poster":
                    poster = dest["Url"]
                elif dest["CoverType"] == "Fanart":
                    fanart = dest["Url"]

        for dest in movie["Certifications"]:
            if dest["Country"] == "US":
                certification = dest["Certification"]

        ratingString = ""
        if movie["MovieRatings"]["Imdb"]["Value"] != 0:
            ratingString = f"{movie['MovieRatings']['Imdb']['Value']} ({movie['MovieRatings']['Imdb']['Count']} Votes)"
        else:
            ratingString = f"{movie['MovieRatings']['Tmdb']['Value']} ({movie['MovieRatings']['Tmdb']['Count']} Votes)"

        embed = discord.Embed(title=f"{movie['Title']} [{movie['OriginalLanguage']}]", description=movie["Overview"] or "-", colour=0xb3a447)
        embed.add_field(name="Year", value=movie["Year"] or "-", inline=True)
        embed.add_field(name="Certification", value=certification or "-", inline=True)
        embed.add_field(name="Rating", value=ratingString or "-", inline=True)
        embed.add_field(name="Runtime", value=movie["Runtime"] or "-", inline=True)
        embed.add_field(name="Genre", value=', '.join(movie["Genres"] or []), inline=True)
        embed.add_field(name="Studio", value=movie["Studio"] or "-", inline=True)
        embed.set_thumbnail(url=poster)
        embed.set_image(url=fanart)
        return embed

    @staticmethod
    def _get_tv_embed(show):
        poster = ""
        fanart = ""

        if "images" in show:
            for dest in show["images"]:
                if dest["coverType"] == "Poster":
                    poster = dest["url"]
                elif dest["coverType"] == "Fanart":
                    fanart = dest["url"]

        ratingString = ""
        if "rating" in show:
            if show["rating"]["value"] != 0:
                ratingString = f"{show['rating']['value']} ({show['rating']['count']} Votes)"

        embed = discord.Embed(title=f"{show['title']} [{show['originalLanguage']}]", description=show.get("overview", "-"), colour=0x0084ff)
        embed.add_field(name="First Air", value=show["firstAired"] or "-", inline=True)
        embed.add_field(name="Certification", value=show.get("contentRating", "-"), inline=True)
        embed.add_field(name="Rating", value=ratingString or "-", inline=True)
        embed.add_field(name="Runtime", value=show["runtime"] or "-", inline=True)
        embed.add_field(name="Genre", value=', '.join(show["genres"] or []), inline=True)
        embed.add_field(name="Network", value=show.get("network", "-"), inline=True)
        embed.set_thumbnail(url=poster)
        embed.set_image(url=fanart)
        return embed

    @staticmethod
    def _get_artist_embed(artist):
        poster = ""
        fanart = ""

        if "images" in artist:
            for dest in artist["images"]:
                if dest["coverType"] == "Poster":
                    poster = dest["url"]
                elif dest["coverType"] == "Fanart":
                    fanart = dest["url"]

        ratingString = ""
        if "rating" in artist:
            if artist["rating"]["value"] != 0:
                ratingString = f"{artist['rating']['value']} ({artist['rating']['count']} Votes)"

        embed = discord.Embed(title=f"{artist['artistname']}", description=artist.get("overview", "-"), colour=0x0084ff)
        embed.add_field(name="Disambiguation", value=artist["disambiguation"] or "-", inline=True)
        embed.add_field(name="Rating", value=ratingString or "-", inline=True)
        embed.add_field(name="Status", value=artist["status"] or "-", inline=True)
        embed.add_field(name="Genre", value=', '.join(artist["genres"] or []), inline=True)
        embed.add_field(name="Type", value=artist.get("type", "-"), inline=True)
        embed.set_thumbnail(url=poster)
        embed.set_image(url=fanart)
        return embed

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
