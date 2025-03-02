import logging

from redbot.core import commands

log = logging.getLogger("red.servarr.servarr")

__version__ = "1.0.0"

TR_OUTSIDE = "/mnt/user/data"
TR_INSIDE = "/data"
TR_LIBRARY = "media"
TR_SERIES = "tv"
TR_MOVIES = "movies"

class Servarr(commands.Cog):
    """Commands for the servarr server."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="folder", aliases=["path"],
        usage=f"[outside base path={TR_OUTSIDE}] [inside base path={TR_INSIDE}]" \
            f"[library folder name={TR_LIBRARY}] [series folder name={TR_SERIES}]" \
            f"[movies folder name={TR_MOVIES}]"
        )
    async def folderr(self, ctx,
        outside: str = TR_OUTSIDE,
        inside: str = TR_INSIDE,
        library: str = TR_LIBRARY,
        series: str = TR_SERIES,
        movies: str = TR_MOVIES,
        ):
        """Returns a customized folder tree for docker users"""

        tree = f"""# Customized Docker Example for You!
The key aspects of this setup: base folder is one file system, paths are consistent between *all* containers and Sonarr/Radarr import from download folder to library folder on the same volume. You'll need to setup the Docker environment correctly and then each software with the correct paths, fixing movies and shows with incorrect paths.

## Folder structure
```
{outside}
├── {library}
│   ├── {movies}
│   └── {series}
├── torrents
│   ├── .incomplete
│   ├── {movies.lower()}
│   └── {series.lower()}
└── usenet
    ├── .incomplete
    ├── {movies.lower()}
    └── {series.lower()}
```
## Docker volume & software setup

* Sonarr and Radarr volume: `{outside}:{inside}`, for access to library and download folders. Sonarr root folder: `{inside}/{library}/{series}`, Radarr root folder: `{inside}/{library}/{movies}`. If you like, divide your library into more root folders such as `{library}/Kids TV` or `{library}/Anime Movies`.
* Torrent volume: `{outside}/torrents:{inside}/torrents`, for access only to the torrents folder. Torrent client default folder: `{inside}/torrents`, incomplete folder: `{inside}/torrents/.incomplete`, category `{series.lower()}` folder: `{inside}/torrents/{series.lower()}` and category `{movies.lower()}` folder: `{inside}/torrents/{movies.lower()}`.
* Usenet volume: `{outside}/usenet:{inside}/usenet`, for access only to the usenet folder. Usenet client default folder: `{inside}/usenet`, incomplete folder: `{inside}/usenet/.incomplete`, category `{series.lower()}` folder: `{inside}/usenet/{series.lower()}` and category `{movies.lower()}` folder: `{inside}/usenet/{movies.lower()}`.
* Media server and Bazarr volume: `{outside}/{library}:{inside}/{library}`, for access only to the library. Media server {series} library path: `{inside}/{library}/{series}` and {movies} library path: `{inside}/{library}/{movies}`.
"""

        await ctx.send(tree)