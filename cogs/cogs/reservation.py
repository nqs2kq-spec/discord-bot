from discord.ext import commands

class Reservation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        await ctx.send("Cog動いてる")

async def setup(bot):
    await bot.add_cog(Reservation(bot))
