from .timeoutsync import TimeoutSync
from redbot.core.bot import Red


async def setup(bot: Red) -> None:
    await bot.add_cog(TimeoutSync(bot))
