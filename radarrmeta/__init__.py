from .radarrmeta import RadarrMeta
from redbot.core.bot import Red


async def setup(bot: Red):
    cog = RadarrMeta(bot)
    await bot.add_cog(cog)
