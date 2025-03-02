from .servarr import Servarr
from redbot.core.bot import Red

async def setup(bot: Red) -> None:
    await bot.add_cog(Servarr(bot))
