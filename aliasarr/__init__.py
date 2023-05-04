from .aliasarr import Aliasarr
from redbot.core.bot import Red


async def setup(bot: Red):
    cog = Aliasarr(bot)
    await bot.add_cog(cog)
    cog.sync_init()
