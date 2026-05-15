import os
import discord
from discord.ext import commands
import logging
from flask import Flask
from threading import Thread

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("discord_bot")
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_web():
    app.run(host='0.0.0.0', port=3000, debug=False)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN environment variable is not set.")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

COGS = [
    "cogs.moderation",
    "cogs.utility",
    "cogs.fun",
    "cogs.help",
    "cogs.reservations",
]


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    synced = await bot.tree.sync()
    logger.info(f"Synced {len(synced)} slash command(s)")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, name="!help for commands"
        )
    )


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: `{error.param.name}`. Use `!help {ctx.command}` for usage.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("I don't have the required permissions to do that.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Could not find that member.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument. Use `!help {ctx.command}` for usage.")
    else:
        logger.error(f"Unhandled error in {ctx.command}: {error}")
        await ctx.send("An unexpected error occurred.")


async def main():
    async with bot:
        for cog in COGS:
            try:
                await bot.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}")
        await bot.start(TOKEN)


if __name__ == "__main__":
    keep_alive()
    import asyncio
    asyncio.run(main())
