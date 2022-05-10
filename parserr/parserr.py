import asyncio
import aiohttp
import logging
import os
import json
from urllib.parse import urlparse, quote

import discord
from redbot.core import checks, commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

log = logging.getLogger("red.servarr.parserr")

__version__ = "1.1.7"


class Parserr(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._headers = {'User-Agent': 'Python/3.8'}
        self._apikey = os.getenv("ARR_API_KEY")
        self._url_fmt = os.getenv("ARR_URL_FMT", "https://dev.servarr.com/{arr}/{branch}")
        self._user = os.getenv("ARR_USER")
        self._password = os.getenv("ARR_PASSWORD")

    @commands.group(invoke_without_command=True)
    async def parse(self, ctx, *, release: str):
        """Parse release names from Arrs.

        If a program and branch are not specified, the server default will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        server = self._valid_server(ctx.message.guild.name)

        if server == "Sonarr":
            await ctx.invoke(self._sonarr_parse, release=release)
        elif server == "Lidarr":
            await ctx.invoke(self._lidarr_parse, release=release)
        elif server == "Readarr":
            await ctx.invoke(self._readarr_parse, release=release)
        else:
            await ctx.invoke(self._nightly_radarr_parse, release=release)

    @parse.group(name="radarr", invoke_without_command=True)
    async def _radarr_parse(self, ctx: commands.Context, *, release: str):
        """Make a Radarr parse call

        If a branch is not specified, the nightly branch will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        await ctx.invoke(self._nightly_radarr_parse, release=release)

    @_radarr_parse.command(name="nightly")
    async def _nightly_radarr_parse(self, ctx: commands.Context, *, release: str):
        """Make a Radarr nightly parse call

        **Arguments:**

        - `<release>` The release title to parse.
        """
        async with ctx.typing():
            base_url = self._url_fmt.format(arr="radarr", branch="nightly")
            url = f"{base_url}/api/v3/parse?apikey={self._apikey}&title={quote(release)}"
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    parse_dict = json.loads(text)
                    version = await self._get_arr_version("radarr", "V3", "nightly")
                    embed = self._get_radarr_embed(parse_dict)
                    embed.set_footer(text=f"Radarr Version {version} | Branch Nightly")

                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Parse error")
            else:
                return

    @_radarr_parse.command(name="develop")
    async def _develop_radarr_parse(self, ctx: commands.Context, *, release: str):
        """Make a Radarr develop branch parse call

        **Arguments:**

        - `<release>` The release title to parse.
        """
        async with ctx.typing():
            base_url = self._url_fmt.format(arr="radarr", branch="testing")
            url = f"{base_url}/api/v3/parse?apikey={self._apikey}&title={quote(release)}"
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    parse_dict = json.loads(text)
                    version = await self._get_arr_version("radarr", "V3", "testing")
                    embed = self._get_radarr_embed(parse_dict)
                    embed.set_footer(text=f"Radarr Version {version} | Branch Develop")

                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Parse error")
            else:
                return

    @_radarr_parse.command(name="master")
    async def _master_radarr_parse(self, ctx: commands.Context, *, release: str):
        """Make a Radarr master branch parse call

        **Arguments:**

        - `<release>` The release title to parse.
        """
        async with ctx.typing():
            base_url = self._url_fmt.format(arr="radarr", branch="release")
            url = f"{base_url}/api/v3/parse?apikey={self._apikey}&title={quote(release)}"
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    parse_dict = json.loads(text)
                    version = await self._get_arr_version("radarr", "V3", "release")
                    embed = self._get_radarr_embed(parse_dict)
                    embed.set_footer(text=f"Radarr Version {version} | Branch Master")

                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Parse error")
            else:
                return

    @parse.command(name="sonarr")
    async def _sonarr_parse(self, ctx: commands.Context, *, release: str):
        """Make a Sonarr parse call

        If a branch is not specified, the nightly branch will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        async with ctx.typing():
            base_url = self._url_fmt.format(arr="sonarr", branch="nightly")
            url = f"{base_url}/api/v3/parse?apikey={self._apikey}&title={quote(release)}"
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    parse_dict = json.loads(text)
                    version = await self._get_arr_version("sonarr", "V3", "nightly")
                    embed = self._get_sonarr_embed(parse_dict)
                    embed.set_footer(text=f"Sonarr Version {version} | Branch Nightly")

                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Parse error")
            else:
                return

    @parse.command(name="lidarr")
    async def _lidarr_parse(self, ctx: commands.Context, *, release: str):
        """Make a Lidarr parse call

        If a branch is not specified, the nightly branch will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        async with ctx.typing():
            base_url = self._url_fmt.format(arr="lidarr", branch="nightly")
            url = f"{base_url}/api/v1/parse?apikey={self._apikey}&title={quote(release)}"
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    parse_dict = json.loads(text)
                    version = await self._get_arr_version("lidarr", "V1", "nightly")
                    embed = self._get_lidarr_embed(parse_dict)
                    embed.set_footer(text=f"Lidarr Version {version} | Branch Nightly")

                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Parse error")
            else:
                return

    @parse.command(name="readarr")
    async def _readarr_parse(self, ctx: commands.Context, *, release: str):
        """Make a Readarr parse call

        If a branch is not specified, the nightly branch will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        async with ctx.typing():
            base_url = self._url_fmt.format(arr="readarr", branch="nightly")
            url = f"{base_url}/api/v1/parse?apikey={self._apikey}&title={quote(release)}"
            valid_url = await self._valid_url(ctx, url)
            if valid_url:
                text = await self._get_url_content(url)
                if text:
                    parse_dict = json.loads(text)
                    version = await self._get_arr_version("readarr", "V1", "nightly")
                    embed = self._get_readarr_embed(parse_dict)
                    embed.set_footer(text=f"Readarr Version {version} | Branch Nightly")

                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Parse error")
            else:
                return

    async def _get_url_content(self, url: str):
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(headers=self._headers, timeout=timeout, auth=aiohttp.BasicAuth(self._user, self._password)) as session:
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

    async def _get_arr_version(self, arr: str, api: str, branch: str):
        base_url = self._url_fmt.format(arr=arr, branch=branch)
        url = f"{base_url}/api/{api}/system/status?apikey={self._apikey}"
        text = await self._get_url_content(url)
        if text:
            parse_dict = json.loads(text)
            return parse_dict["version"] or ""
        else:
            return ""

    @staticmethod
    def _get_radarr_embed(response):
        embed = discord.Embed(title=f"Radarr Parse Result", description="", colour=0xb3a447)
        embed.add_field(name="Attempted Release Title", value=f"```{response['title']  or '-'}```", inline=False)
        parsed_obj = response["parsedMovieInfo"]
        language_string = ", ".join((o["name"] for o in parsed_obj["languages"])) or "-"
        quality = parsed_obj["quality"]["quality"]["name"] or "-"
        quality_real = "True" if parsed_obj["quality"]["revision"]["real"] > 0 else "-" or "-"
        quality_proper = "True" if parsed_obj["quality"]["revision"]["version"] > 1 else "-" or "-"
        quality_repack = "True" if parsed_obj["quality"]["revision"]["isRepack"] is True else "-" or "-"

        embed.add_field(name="Movie Title", value=parsed_obj["movieTitle"] or "-", inline=True)
        embed.add_field(name="Year", value=parsed_obj["year"] or "-", inline=True)
        embed.add_field(name="Edition", value=parsed_obj["edition"] or "-", inline=True)
        embed.add_field(name="TMDBId", value=parsed_obj["tmdbId"] or "-", inline=False)
        embed.add_field(name="IMDbId", value=parsed_obj["imdbId"] or "-", inline=False)
        embed.add_field(name="Quality", value=quality, inline=False)
        embed.add_field(name="Proper", value=quality_proper, inline=True)
        embed.add_field(name="Real", value=quality_real, inline=True)
        embed.add_field(name="Repack", value=quality_repack, inline=True)
        embed.add_field(name="Languages", value=language_string, inline=False)
        embed.add_field(name="Release Group", value=parsed_obj.get("releaseGroup", "-"), inline=False)
        return embed

    @staticmethod
    def _get_sonarr_embed(response):
        embed = discord.Embed(title=f"Sonarr Parse Result", description="", colour=0x0084ff)
        embed.add_field(name="Attempted Release Title", value=f"```{response['title']  or '-'}```", inline=False)
        parsed_obj = response["parsedEpisodeInfo"]
        series_title_obj = parsed_obj["seriesTitleInfo"]
        all_titles_string = ", ".join((str(o) for o in series_title_obj.get("allTitles", []))) or "-"
        language = parsed_obj["language"]["name"] or "-"
        quality = parsed_obj["quality"]["quality"]["name"] or "-"
        quality_real = "True" if parsed_obj["quality"]["revision"]["real"] > 0 else "-" or "-"
        quality_proper = "True" if parsed_obj["quality"]["revision"]["version"] > 1 else "-" or "-"
        quality_repack = "True" if parsed_obj["quality"]["revision"]["isRepack"] is True else "-" or "-"
        episode_string = ", ".join((str(o) for o in parsed_obj["episodeNumbers"])) or \
                         ", ".join((str(o) for o in parsed_obj["absoluteEpisodeNumbers"])) or \
                         ", ".join((str(o) for o in parsed_obj["specialAbsoluteEpisodeNumbers"])) or \
                         "-"

        embed.add_field(name="Series Title", value=parsed_obj["seriesTitle"] or "-", inline=True)
        embed.add_field(name="Year", value=series_title_obj["year"] or "-", inline=True)
        embed.add_field(name="All Titles", value=all_titles_string, inline=True)
        embed.add_field(name="Season", value=parsed_obj["seasonNumber"] or "-", inline=True)
        embed.add_field(name="Episode(s)", value=episode_string, inline=True)
        embed.add_field(name="Special", value=parsed_obj.get("special", "-"), inline=True)
        embed.add_field(name="Full Season", value=parsed_obj.get("fullSeason", "-"), inline=True)
        embed.add_field(name="Partial Season", value=parsed_obj.get("isPartialSeason", "-"), inline=True)
        embed.add_field(name="Multi Season", value=parsed_obj.get("isMultiSeason ", "-"), inline=True)
        embed.add_field(name="Daily", value=parsed_obj.get("isDaily", "-"), inline=True)
        embed.add_field(name="AirDate", value=parsed_obj.get("airDate", "-"), inline=True)
        embed.add_field(name="Quality", value=quality, inline=False)
        embed.add_field(name="Proper", value=quality_proper, inline=True)
        embed.add_field(name="Real", value=quality_real, inline=True)
        embed.add_field(name="Repack", value=quality_repack, inline=True)
        embed.add_field(name="Language", value=language, inline=False)
        embed.add_field(name="Release Group", value=parsed_obj.get("releaseGroup", "-"), inline=True)
        embed.add_field(name="Release Hash", value=parsed_obj["releaseHash"] or "-", inline=True)
        return embed

    @staticmethod
    def _get_readarr_embed(response):
        embed = discord.Embed(title=f"Readarr Parse Result", description="", colour=0xff0000)
        embed.add_field(name="Attempted Release Title", value=f"```{response['title']  or '-'}```", inline=False)
        parsed_obj = response["parsedBookInfo"]
        quality = parsed_obj["quality"]["quality"]["name"] or "-"
        quality_real = "True" if parsed_obj["quality"]["revision"]["real"] > 0 else "-" or "-"
        quality_proper = "True" if parsed_obj["quality"]["revision"]["version"] > 1 else "-" or "-"
        quality_repack = "True" if parsed_obj["quality"]["revision"]["isRepack"] is True else "-" or "-"

        embed.add_field(name="Author Name", value=parsed_obj.get("authorName", "-"), inline=True)
        embed.add_field(name="Book Title", value=parsed_obj.get("bookTitle", "-"), inline=True)
        embed.add_field(name="Release Date", value=parsed_obj["releaseDate"] or "-", inline=True)
        embed.add_field(name="Quality", value=quality, inline=False)
        embed.add_field(name="Proper", value=quality_proper, inline=True)
        embed.add_field(name="Real", value=quality_real, inline=True)
        embed.add_field(name="Repack", value=quality_repack, inline=True)
        embed.add_field(name="Release Group", value=parsed_obj.get("releaseGroup", "-"), inline=False)
        return embed

    @staticmethod
    def _get_lidarr_embed(response):
        embed = discord.Embed(title=f"Lidarr Parse Result", description="", colour=0x40a333)
        embed.add_field(name="Attempted Release Title", value=f"```{response['title']  or '-'}```", inline=False)
        parsed_obj = response["parsedAlbumInfo"]
        quality = parsed_obj["quality"]["quality"]["name"] or "-"
        quality_real = "True" if parsed_obj["quality"]["revision"]["real"] > 0 else "-" or "-"
        quality_proper = "True" if parsed_obj["quality"]["revision"]["version"] > 1 else "-" or "-"
        quality_repack = "True" if parsed_obj["quality"]["revision"]["isRepack"] is True else "-" or "-"

        embed.add_field(name="Artist Name", value=parsed_obj.get("artistName", "-"), inline=True)
        embed.add_field(name="Album Title", value=parsed_obj.get("albumTitle", "-"), inline=True)
        embed.add_field(name="Release Date", value=parsed_obj["releaseDate"] or "-", inline=True)
        embed.add_field(name="Discography", value=parsed_obj.get("discography", "-"), inline=True)
        embed.add_field(name="Quality", value=quality, inline=False)
        embed.add_field(name="Proper", value=quality_proper, inline=True)
        embed.add_field(name="Real", value=quality_real, inline=True)
        embed.add_field(name="Repack", value=quality_repack, inline=True)
        embed.add_field(name="Release Group", value=parsed_obj.get("releaseGroup", "-"), inline=False)
        return embed

    @staticmethod
    def _valid_server(server: str):
        servers = ["radarr", "lidarr", "sonarr", "readarr"]
        if not server:
            return "Radarr"

        if server.lower() in servers:
            return server
        else:
            return "Radarr"

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
