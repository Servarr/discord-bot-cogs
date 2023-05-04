from .parserr import Parserr
from redbot.core.bot import Red

async def setup(bot: Red):
    cog = Parserr(bot)
    await bot.add_cog(cog)
