import os
import discord
from discord.ext import commands
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== テストコマンド =====
@bot.command()
async def test(ctx):
    await ctx.send("Botは正常に動いています")

# ===== 予約コマンド（ここに直書き）=====
@bot.command()
async def reservation(ctx):
    await ctx.send("予約コマンド動作OK")

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")

async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("TOKEN missing")

    await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
