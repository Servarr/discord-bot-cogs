import asyncio
import json
import logging
import os
from typing import Dict, List
from urllib.parse import urlparse

import aiohttp
import discord
from redbot.core import app_commands, commands

log = logging.getLogger("red.servarr.radarrmeta")


__version__ = "1.3.0"

HEADERS = {"User-Agent": f"radarrmeta-cog/{__version__}"}
RADARR_META_BASE = "https://api.radarr.video/v1"
LIDARR_META_BASE = "https://api.lidarr.audio/api/v0.4"
WHISPARR_META_BASE = "https://api.whisparr.com/v3"
READARR_META_BASE = "https://api.bookinfo.club/v1"
RADARR_META_APIKEY = os.getenv("RADARR_META_API_KEY")
READARR_META_APIKEY = os.getenv("READARR_META_API_KEY")
WHISPARR_META_APIKEY = os.getenv("WHISPARR_META_API_KEY")
REFRESH_ALLOW_ROLES = os.getenv("REFRESH_ALLOW_ROLES", "").split(",") or [
    "Admin",
    "Servarr Team",
    "Moderatarr",
    "Bot Whisperer",
    "VIP",
    "Support Slayarr",
    "Donatarr",
]


class InvalidURL(Exception):
    pass


async def refresh_movies(ids: List[int]):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.post(
                f"{RADARR_META_BASE}/movie/bulk/refresh",
                json=ids,
                headers={"apikey": RADARR_META_APIKEY, **HEADERS}
        ) as resp:
            return resp.status


async def refresh_collections(ids: List[int]):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.post(
                f"{RADARR_META_BASE}/movie/collection/bulk/refresh",
                json=ids,
                headers={"apikey": RADARR_META_APIKEY, **HEADERS}
        ) as resp:
            return resp.status

async def refresh_author(goodreadsid: str):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.post(
                f"{READARR_META_BASE}/author/{goodreadsid}/refresh",
                headers={"X-Api-Key": READARR_META_APIKEY, **HEADERS}
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
        
async def refresh_xxx_sites(ids: List[int]):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.post(
                f"{WHISPARR_META_BASE}/site/bulk/refresh",
                json=ids,
                headers={"apikey": WHISPARR_META_APIKEY, **HEADERS}
        ) as resp:
            return resp.status
        
async def refresh_xxx_scenes(ids: List[int]):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.post(
                f"{WHISPARR_META_BASE}/scene/bulk/refresh",
                json=ids,
                headers={"apikey": WHISPARR_META_APIKEY, **HEADERS}
        ) as resp:
            return resp.status
        
async def refresh_xxx_movies(ids: List[int]):
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(headers=HEADERS, timeout=timeout) as session:
        async with session.post(
                f"{WHISPARR_META_BASE}/movie/bulk/refresh",
                json=ids,
                headers={"apikey": WHISPARR_META_APIKEY, **HEADERS}
        ) as resp:
            return resp.status


def collect_resources(indvidual_resources: List[str]) -> Dict[str, str]:
    output = {"album": [], "artist": [], "author": [], "movie": [], "collection": [], "xxx_site": [], "xxx_scene": [], "xxx_movie": []}
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
    for goodreadsid in per_resource_type["author"]:
        futures.append(refresh_author(goodreadsid))
    if per_resource_type["movie"]:
        futures.append(refresh_movies(per_resource_type["movie"]))
    if per_resource_type["xxx_site"]:
        futures.append(refresh_xxx_sites(per_resource_type["xxx_site"]))
    if per_resource_type["xxx_scene"]:
        futures.append(refresh_xxx_scenes(per_resource_type["xxx_scene"]))
    if per_resource_type["xxx_movie"]:
        futures.append(refresh_xxx_movies(per_resource_type["xxx_movie"]))
    if ids := per_resource_type["collection"]:
        futures.append(refresh_collections(ids))
    responses = await asyncio.gather(*futures)
    log.info(f"Refresh statuses: {responses}")
    return responses


class RadarrMeta(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._headers = {'User-Agent': 'Python/3.8'}

    @commands.group(invoke_without_command=True)
    async def refresh(self, ctx, *, resources: str):
        """
        Refreshes cached items

        **Arguments:**
        - `<resources>` Resource ids as album/mbid, artist/mbid, or movie/id
        """
        allowed = (
            ctx.permissions.administrator
            or any(role.name in REFRESH_ALLOW_ROLES for role in ctx.author.roles),
        )

        if not allowed:
            return
        async with ctx.typing():
            try:
                statuses = await process_refresh_resources(resources)
                await ctx.send(f"Refresh statuses: {statuses}")
            except asyncio.TimeoutError:
                await ctx.send("Refresh timed out")

    movie = app_commands.Group(name="movie", description="Does lookups of movies.")

    @movie.command(name="radarr", description="Looks up movies against Radarrs metadata server.")
    @app_commands.describe(movie="The title to lookup, may include year.")
    async def radarr(self, interaction: discord.Interaction, movie: str):
        """
        Base command for movie lookup.

        **Arguments:**

        - `<movie>` The title to lookup, may include year.
        """
        url = "https://api.radarr.video/v1/search?q=" + movie
        try:
            await self._valid_url(url)
        except InvalidURL as err:
            await interaction.response.send_message(f"Parse error:\n```{err}```", ephemeral=True)
        text = await self._get_url_content(url)
        if text:
            movie_dict = json.loads(text)
            if len(movie_dict) > 0:
                await interaction.response.send_message(embed=self._get_movie_embed(movie_dict[0]))
            else:
                await interaction.response.send_message("Movie not found.")
        else:
            await interaction.response.send_message("Movie not found")

    @movie.command()
    @app_commands.describe(tmdb_id="TMDbId to lookup.")
    @app_commands.rename(tmdb_id="tmdb")
    async def tmdb(self, interaction: discord.Interaction, tmdb_id: str):
        """
        Input a TMDbId to lookup.
        """
        url = "https://api.radarr.video/v1/movie/" + tmdb_id
        try:
            await self._valid_url(url)
        except InvalidURL as err:
            await interaction.response.send_message(f"Parse error:\n```{err}```", ephemeral=True)
        text = await self._get_url_content(url)
        if text:
            movie_dict = json.loads(text)
            await interaction.response.send_message(embed=self._get_movie_embed(movie_dict))
        else:
            await interaction.response.send_message("TmdbId not found.")

    @movie.command()
    @app_commands.describe(imdb_id="IMDb to lookup.")
    @app_commands.rename(imdb_id="imdb")
    async def imdb(self, interaction: discord.Interaction, imdb_id: str):
        """
        Input an IMDb Id to lookup.
        """
        url = "https://api.radarr.video/v1/movie/imdb/" + imdb_id
        try:
            await self._valid_url(url)
        except InvalidURL as err:
            await interaction.response.send_message(f"Parse error:\n```{err}```", ephemeral=True)
        text = await self._get_url_content(url)
        if text:
            movie_dict = json.loads(text)
            if len(movie_dict) > 0:
                await interaction.response.send_message(embed=self._get_movie_embed(movie_dict[0]))
            else:
                await interaction.response.send_message("ImdbId doesn't exist or isn't on TMDb.")
        else:
            await interaction.response.send_message("ImdbId doesn't exist or isn't on TMDb")

    tv = app_commands.Group(name="tv", description="Does lookups of TV shows.")

    @tv.command(description="Looks up TV shows against Sonarrs metadata server.")
    @app_commands.describe(show="The title to lookup.")
    async def sonarr(self, interaction: discord.Interaction, show: str):
        """
        Base command for tv show lookup.

        **Arguments:**

        - `<show>` The title to lookup.
        """
        url = "https://skyhook.sonarr.tv/v1/tvdb/search/en/?term=" + show
        try:
            await self._valid_url(url)
        except InvalidURL as err:
            await interaction.response.send_message(f"Parse error:\n```{err}```", ephemeral=True)
        text = await self._get_url_content(url)
        if text:
            show_dict = json.loads(text)
            if len(show_dict) > 0:
                await interaction.response.send_message(embed=self._get_tv_embed(show_dict[0]))
            else:
                await interaction.response.send_message("Show not found.")
        else:
            await interaction.response.send_message("Show not found.")

    @tv.command()
    @app_commands.describe(tvdb_id="TVDbId to lookup.")
    @app_commands.rename(tvdb_id="tvdb")
    async def tvdb(self, interaction: discord.Interaction, tvdb_id: str):
        """
        Input a TVDbId to lookup.
        """
        url = "https://skyhook.sonarr.tv/v1/tvdb/shows/en/" + tvdb_id
        try:
            await self._valid_url(url)
        except InvalidURL as err:
            await interaction.response.send_message(f"Parse error:\n```{err}```", ephemeral=True)
        text = await self._get_url_content(url)
        if text:
            show_dict = json.loads(text)
            await interaction.response.send_message(embed=self._get_tv_embed(show_dict))
        else:
            await interaction.response.send_message("TvdbId not found")

    music = app_commands.Group(name="music", description="Does lookups of artists and albums.")

    @music.command()
    @app_commands.describe(artist="artist to lookup.")
    async def artist(self, interaction: discord.Interaction, artist: str):
        """
        Base command for artist lookup.

        **Arguments:**

        - `<artist>` The name to lookup.
        """
        url = "https://api.lidarr.audio/api/v0.4/search?type=artist&query=" + artist
        try:
            await self._valid_url(url)
        except InvalidURL as err:
            await interaction.response.send_message(f"Parse error:\n```{err}```", ephemeral=True)
        text = await self._get_url_content(url)
        if text:
            show_dict = json.loads(text)
            if len(show_dict) > 0:
                await interaction.response.send_message(embed=self._get_artist_embed(show_dict[0]))
            else:
                await interaction.response.send_message("Artist not found.")
        else:
            await interaction.response.send_message("Artist not found")

    @music.command()
    @app_commands.describe(album="album to lookup.")
    async def album(self, interaction: discord.Interaction, album: str):
        """
        Base command for album lookup.

        **Arguments:**

        - `<album>` The title to lookup.
        """
        url = "https://api.lidarr.audio/api/v0.4/search?type=album&query=" + album
        try:
            await self._valid_url(url)
        except InvalidURL as err:
            await interaction.response.send_message(f"Parse error:\n```{err}```", ephemeral=True)
        text = await self._get_url_content(url)
        if text:
            show_dict = json.loads(text)
            if len(show_dict) > 0:
                await interaction.response.send_message(embed=self._get_album_embed(show_dict[0]))
            else:
                await interaction.response.send_message("Album not found.")
        else:
            await interaction.response.send_message("Album not found")


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

    async def _valid_url(self, url: str):
        try:
            result = urlparse(url)
        except Exception as e:
            log.exception(e, exc_info=e)
            raise InvalidURL("There was an issue trying to fetch that site. Please check your console for the error.")

        if all([result.scheme, result.netloc]):
            text = await self._get_url_content(url)
            if not text:
                raise InvalidURL("No text present at the given url.")
            else:
                return text
        else:
            raise InvalidURL(f"That url seems to be incomplete.")
