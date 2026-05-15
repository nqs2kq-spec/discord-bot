import os
import sys
import discord
from discord.ext import commands
import logging
import asyncio

# ===== デバッグ（重要）=====
print("CWD:", os.getcwd())
print("FILES:", os.listdir())

# cogsが見えるようにパス固定
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ===== ログ設定 =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("discord_bot")

# ===== Bot設定 =====
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ===== Cog一覧 =====
COGS = [
    "cogs.reservation",
]

# ===== 起動時 =====
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        logger.error(f"Slash sync failed: {e}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="!test で確認"
        )
    )

# ===== テストコマンド =====
@bot.command()
async def test(ctx):
    await ctx.send("Bot & Cog は正常に動作しています")

# ===== エラーハンドリング =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    await ctx.send(f"Error: {error}")
    logger.error(f"Command error: {error}")

# ===== Cogロード（ここが重要）=====
async def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN が設定されていません")

    async with bot:
        for cog in COGS:
            try:
                logger.info(f"TRY LOAD: {cog}")
                await bot.load_extension(cog)
                logger.info(f"SUCCESS: {cog}")
            except Exception as e:
                logger.error(f"FAILED: {cog}")
                logger.error(f"ERROR DETAIL: {e}")

        await bot.start(token)

# ===== 実行 =====
if __name__ == "__main__":
    asyncio.run(main())
