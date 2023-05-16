import asyncio
import json
import logging
import os
from urllib.parse import quote, urlparse

import aiohttp
import discord
from redbot.core import app_commands, commands

log = logging.getLogger("red.servarr.parserr")

__version__ = "1.2.0"

class InvalidURL(Exception):
    pass

class Parserr(commands.Cog):
    """Grab stuff from a text API."""

    def __init__(self, bot):
        self.bot = bot

        self._headers = {'User-Agent': 'Python/3.8'}
        self._apikey = os.getenv("ARR_API_KEY")
        self._url_fmt = os.getenv("ARR_URL_FMT", "https://dev.servarr.com/{arr}/{branch}")
        self._user = os.getenv("ARR_USER")
        self._password = os.getenv("ARR_PASSWORD")

    parse = app_commands.Group(name="parser", description="Parses release names for arrs.")

    @parse.command()
    @app_commands.describe(branch="Branch to run the release against.")
    @app_commands.describe(release="Release name to parse.")
    @app_commands.choices(branch=[
        app_commands.Choice(name="Nightly", value="nightly"),
        app_commands.Choice(name="Develop", value="develop"),
        app_commands.Choice(name="Master", value="master"),
    ])
    async def radarr(self, interaction: discord.Interaction, release: str, branch: app_commands.Choice[str] = "nightly"):
        """Make a Radarr parse call

        If a branch is not specified, the nightly branch will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        await self._response_builder(interaction=interaction, release=release, app="radarr", branch=branch, api=3)

    @parse.command()
    @app_commands.describe(release="Release name to parse.")
    async def sonarr(self, interaction: discord.Interaction, release: str):
        """Make a Sonarr parse call

        If a branch is not specified, the nightly branch will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        await self._response_builder(interaction=interaction, release=release, app="sonarr", branch="v4", api=3)

    @parse.command()
    @app_commands.describe(release="Release name to parse.")
    async def lidarr(self, interaction: discord.Interaction, release: str):
        """Make a Lidarr parse call

        If a branch is not specified, the nightly branch will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        await self._response_builder(interaction=interaction, release=release, app="lidarr", branch="nightly", api=1)

    @parse.command()
    @app_commands.describe(release="Release name to parse.")
    async def readarr(self, interaction: discord.Interaction, release: str):
        """Make a Readarr parse call

        If a branch is not specified, the nightly branch will be used.

        **Arguments:**

        - `<release>` The release title to parse.
        """
        await self._response_builder(interaction=interaction, release=release, app="readarr", branch="nightly", api=1)

    async def _response_builder(self, interaction: discord.Interaction, release: str, app: str, branch: str = "nightly", api: int = 3):
        branch = branch.value if isinstance(branch, app_commands.Choice) else branch
        api_branch = branch
        if app == "radarr":
            api_branch = "testing" if branch != "develop" else branch

        base_url = self._url_fmt.format(arr=app, branch=api_branch)
        url = f"{base_url}/api/v{api}/parse?apikey={self._apikey}&title={quote(release)}"
        try:
            await self._valid_url(url)
        except InvalidURL as err:
            await interaction.response.send_message(f"Parse error:\n```{err}```", ephemeral=False)
        text = await self._get_url_content(url)
        if text:
            parse_dict = json.loads(text)
            version = await self._get_arr_version(app, f"V{api}", api_branch)

            if app == "radarr":
                embed = self._get_radarr_embed(parse_dict)
            elif app == "sonarr":
                embed = self._get_sonarr_embed(parse_dict)
            elif app == "lidarr":
                embed = self._get_lidarr_embed(parse_dict)
            elif app == "readarr":
                embed = self._get_readarr_embed(parse_dict)

            embed.set_footer(text=f"{app.title()} Version {version} | Branch {branch.title()}")

            await interaction.response.send_message(embed=embed, ephemeral=False)


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
        parsed_obj = response.get("parsedMovieInfo")
        if not parsed_obj:
            embed.description = f"Failed to parse `{response['title']}`"
            embed.colour = 0xff0000
            return embed
        language_string = ", ".join((o["name"] for o in parsed_obj["languages"])) or "-"
        titles_string = ", ".join((o for o in parsed_obj["movieTitles"])) or "-"
        quality = parsed_obj["quality"]["quality"]["name"] or "-"
        quality_real = "True" if parsed_obj["quality"]["revision"]["real"] > 0 else "-" or "-"
        quality_proper = "True" if parsed_obj["quality"]["revision"]["version"] > 1 else "-" or "-"
        quality_repack = "True" if parsed_obj["quality"]["revision"]["isRepack"] is True else "-" or "-"

        embed.add_field(name="Movie Title(s)", value=titles_string, inline=True)
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
        parsed_obj = response.get("parsedEpisodeInfo")
        if not parsed_obj:
            embed.description = f"Failed to parse `{response['title']}`"
            embed.colour = 0xff0000
            return embed
        series_title_obj = parsed_obj["seriesTitleInfo"]
        all_titles_string = ", ".join((str(o) for o in series_title_obj.get("allTitles", []))) or "-"
        language = parsed_obj.get("language", {}).get("name", "-")
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
        embed.add_field(name="Quality", value=quality, inline=True)
        embed.add_field(name="Proper", value=quality_proper, inline=True)
        embed.add_field(name="Real", value=quality_real, inline=True)
        embed.add_field(name="Repack", value=quality_repack, inline=True)
        embed.add_field(name="Language", value=language, inline=True)
        embed.add_field(name="Release Group", value=parsed_obj.get("releaseGroup", "-"), inline=True)
        embed.add_field(name="Release Hash", value=parsed_obj["releaseHash"] or "-", inline=True)
        return embed

    @staticmethod
    def _get_readarr_embed(response):
        embed = discord.Embed(title=f"Readarr Parse Result", description="", colour=0xff0000)
        embed.add_field(name="Attempted Release Title", value=f"```{response['title']  or '-'}```", inline=False)
        parsed_obj = response.get("parsedBookInfo")
        if not parsed_obj:
            embed.description = f"Failed to parse `{response['title']}`"
            embed.colour = 0xff0000
            return embed
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
        parsed_obj = response.get("parsedAlbumInfo")
        if not parsed_obj:
            embed.description = f"Failed to parse `{response['title']}`"
            embed.colour = 0xff0000
            return embed
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
