from redbot.core.bot import Red

from .customcomarr import CustomCommandarr


async def setup(bot: Red) -> None:
    await bot.add_cog(CustomCommandarr(bot))
