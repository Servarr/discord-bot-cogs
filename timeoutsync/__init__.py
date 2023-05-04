from .timeoutsync import TimeoutSync
from redbot.core.bot import Red


async def setup(bot: Red):
    cog = TimeoutSync(bot)
    await bot.add_cog(cog)
