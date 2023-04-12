import asyncio
import aiohttp
import logging
import json
import os
from collections import defaultdict
from functools import reduce
from typing import Dict, List
from urllib.parse import urlparse

import discord
# from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

log = logging.getLogger("red.servarr.radarrmeta")


__version__ = "1.1.30"

HEADERS = {"User-Agent": f"radarrmeta-cog/{__version__}"}
RADARR_META_BASE = "https://api.radarr.video/v1"
LIDARR_META_BASE = "https://api.lidarr.audio/api/v0.4"
RADARR_META_APIKEY = os.getenv("RADARR_META_API_KEY")


async def refresh_movies(ids: List[int]):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        # TODO: apikey header
        async with session.post(
                f"{RADARR_META_BASE}/movie/bulk/refresh",
                json=ids,
                headers={"apikey": RADARR_META_APIKEY, **HEADERS}
        ) as resp:
            return resp.status


async def refresh_artist(mbid: str):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.post(f"{LIDARR_META_BASE}/artist/{mbid}/refresh") as resp:
            return resp.status


async def refresh_album(mbid: str):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.post(f"{LIDARR_META_BASE}/album/{mbid}/refresh") as resp:
            return resp.status


def collect_resources(indvidual_resources: List[str]) -> Dict[str, str]:
    output = {"album": [], "artist": [], "movie": []}
    for resource in indvidual_resources:
        key, value = resource.split("/")
        output[key].append(value)
    return output


async def process_refresh_resources(resources: str):
    individual_resources = resources.split()
    per_resource_type = collect_resources(individual_resources)
    log.info(f"Refreshing {per_resource_type}")
    futures = []
    for mbid in per_resource_type["album"]:
        futures.append(refresh_album(mbid))
    for mbid in per_resource_type["artist"]:
        futures.append(refresh_artist(mbid))
    if per_resource_type["movie"]:
        futures.append(refresh_movies(per_resource_type["movie"]))
    responses = await asyncio.gather(*futures)
    log.info(f"Refresh statuses: {responses}")
    return responses


class RadarrMeta(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._headers = {'User-Agent': 'Python/3.8'}

    @commands.group(invoke_without_command=True)
    @commands.mod_or_permissions(admin=True)
    async def refresh(self, ctx, *, resources: str):
        """
        Refreshes cached items

        **Arguments:**
        - `<resources>` Resource ids as album/mbid, artist/mbid, or movie/id
        """
        async with ctx.typing():
            statuses = await process_refresh_resources(resources)
            await ctx.send(f"Refresh statuses: {statuses}")


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
    async def artist(self, ctx, *, artist: str):
        """
        Base command for artist lookup.

        **Arguments:**

        - `<artist>` The name to lookup.
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
                        await ctx.send("Artist not found.")
                else:
                    await ctx.send("Artist not found")
            else:
                return

    @commands.group(invoke_without_command=True)
    async def album(self, ctx, *, artist: str):
        """
        Base command for album lookup.

        **Arguments:**

        - `<album>` The title to lookup.
        """
        async with ctx.typing():
            url = "https://api.lidarr.audio/api/v0.4/search?type=album&query=" + artist
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    show_dict = json.loads(text)
                    if len(show_dict) > 0:
                        await ctx.send(embed=self._get_album_embed(show_dict[0]))
                    else:
                        await ctx.send("Album not found.")
                else:
                    await ctx.send("Album not found")
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

        embed = discord.Embed(title=f"{movie['Title']} [{movie['OriginalLanguage']}]", description=movie["Overview"][0:250] or "-", colour=0xb3a447)
        embed.add_field(name="Year", value=movie["Year"] or "-", inline=True)
        embed.add_field(name="Certification", value=certification or "-", inline=True)
        embed.add_field(name="Rating", value=ratingString or "-", inline=True)
        embed.add_field(name="Runtime", value=movie["Runtime"] or "-", inline=True)
        embed.add_field(name="Genre", value=', '.join(movie["Genres"][0:3] or []), inline=True)
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

        embed = discord.Embed(title=f"{show['title']} [{show['originalLanguage']}]", description=show.get("overview", "-")[0:250], colour=0x0084ff)
        embed.add_field(name="First Air", value=show["firstAired"] or "-", inline=True)
        embed.add_field(name="Certification", value=show.get("contentRating", "-"), inline=True)
        embed.add_field(name="Rating", value=ratingString or "-", inline=True)
        embed.add_field(name="Runtime", value=show["runtime"] or "-", inline=True)
        embed.add_field(name="Genre", value=', '.join(show["genres"][0:3] or []), inline=True)
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
                if dest["CoverType"] == "Poster":
                    poster = dest["Url"]
                elif dest["CoverType"] == "Fanart":
                    fanart = dest["Url"]

        ratingString = ""
        if "rating" in artist:
            if artist["rating"]["Value"] != 0:
                ratingString = f"{artist['rating']['Value']} ({artist['rating']['Count']} Votes)"

        embed = discord.Embed(title=f"{artist['artistname']}", description=artist.get("overview", "-")[0:250], colour=0x40a333)
        embed.add_field(name="Disambiguation", value=artist["disambiguation"] or "-", inline=True)
        embed.add_field(name="Rating", value=ratingString or "-", inline=True)
        embed.add_field(name="Status", value=artist["status"] or "-", inline=True)
        embed.add_field(name="Genre", value=', '.join(artist["genres"][0:3] or []), inline=True)
        embed.add_field(name="Type", value=artist.get("type", "-"), inline=True)
        embed.set_thumbnail(url=poster)
        embed.set_image(url=fanart)
        return embed

    @staticmethod
    def _get_album_embed(album):
        poster = ""
        fanart = ""

        if "images" in album:
            for dest in album["images"]:
                if dest["CoverType"] == "Cover":
                    poster = dest["Url"]

        if "images" in album["artists"][0]:
            for dest in album["artists"][0]["images"]:
                if dest["CoverType"] == "Banner":
                    fanart = dest["Url"]

        ratingString = "-"
        if "rating" in album:
            if album["rating"]["Value"] != 0:
                ratingString = f"{album['rating']['Value']} ({album['rating']['Count']} Votes)"

        embed = discord.Embed(title=f"{album['title']}", description=album.get("overview", "-")[0:250], colour=0x40a333)
        embed.add_field(name="Release Date", value=album["releasedate"] or "-", inline=True)
        embed.add_field(name="Artist", value=album["artists"][0]["artistname"] or "-", inline=True)
        embed.add_field(name="Rating", value=ratingString or "-", inline=True)
        embed.add_field(name="Genre", value=', '.join(album["genres"][0:3] or []) or "-", inline=True)
        embed.add_field(name="Type", value=album.get("type", "-"), inline=True)
        embed.add_field(name="Sec Types", value=', '.join(album["secondarytypes"][0:3] or []) or "-", inline=True)
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
