from .radarrmeta import RadarrMeta


def setup(bot):
    bot.add_cog(RadarrMeta(bot))
