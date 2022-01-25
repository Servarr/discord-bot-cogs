from .timeoutsync import TimeoutSync


def setup(bot):
    bot.add_cog(TimeoutSync(bot))
