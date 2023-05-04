from .bansync import BanSync
from redbot.core.bot import Red


async def setup(bot: Red):
    cog = BanSync(bot)
    await bot.add_cog(cog)
