from .customcomarr import CustomCommandarr
from redbot.core.bot import Red


async def setup(bot: Red):
    cog = CustomCommandarr(bot)
    await bot.add_cog(cog)
