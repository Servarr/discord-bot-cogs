from .customcomarr import CustomCommandarr


def setup(bot):
    bot.add_cog(CustomCommandarr(bot))
