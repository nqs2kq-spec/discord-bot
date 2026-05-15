import os
import json
import discord
from discord.ext import commands
from discord import app_commands
import logging

# =========================
# ログ
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# =========================
# Bot設定
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# データ
# =========================
DATA_FILE = "reservations.json"
TYPES = ["建築", "訓練", "研究"]

TIME_SLOTS = []

from datetime import datetime, timedelta

current = datetime.strptime("09:00", "%H:%M")
end = current + timedelta(days=1)

while current < end:
    TIME_SLOTS.append(current.strftime("%H:%M"))
    current += timedelta(minutes=30)


def load_data():
    if not os.path.exists(DATA_FILE):
        return {t: {} for t in TYPES}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


reservations = load_data()

# =========================
# 起動
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    logger.info(f"Logged in as {bot.user}")

# =========================
# /list（Choice + 全時間表示）
# =========================
@app_commands.command(name="list", description="予約一覧")
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
async def list_cmd(interaction: discord.Interaction, type: app_commands.Choice[str]):

    data = reservations[type.value]

    text = f"【{type.value} 予約一覧】\n\n"

    for slot in TIME_SLOTS:
        if slot in data:
            d = data[slot]
            text += f"❌ {slot} - [{d['tag']}] {d['name']}\n"
        else:
            text += f"🟢 {slot}\n"

    await interaction.response.send_message(text, ephemeral=True)

bot.tree.add_command(list_cmd)

# =========================
# /mylist（自分強調）
# =========================
@bot.tree.command(name="mylist", description="自分の予約一覧")
async def mylist(interaction: discord.Interaction):

    uid = interaction.user.id
    text = "【あなたの予約】\n\n"

    for t in TYPES:
        for slot, d in reservations[t].items():

            if d["discord_id"] == uid:
                text += f"⭐ {slot} - [{d['tag']}] {d['name']}\n"
            else:
                text += f"{slot} - [{d['tag']}] {d['name']}\n"

    await interaction.response.send_message(text, ephemeral=True)

# =========================
# /yoyaku（Choice）
# =========================
@app_commands.command(name="yoyaku", description="予約作成")
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
async def yoyaku(interaction: discord.Interaction, type: app_commands.Choice[str]):

    await interaction.response.send_message(
        f"{type.value} を選択しました。\n"
        "※ここは次ステップでモーダル入力に拡張可能",
        ephemeral=True
    )

bot.tree.add_command(yoyaku)

# =========================
# /cancel（Choice削除）
# =========================
@app_commands.command(name="cancel", description="予約削除")
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
async def cancel(interaction: discord.Interaction, type: app_commands.Choice[str]):

    uid = interaction.user.id

    if type.value not in reservations:
        await interaction.response.send_message("データなし", ephemeral=True)
        return

    for slot, d in list(reservations[type.value].items()):

        if d["discord_id"] == uid:

            del reservations[type.value][slot]
            save_data(reservations)

            await interaction.response.send_message(
                f"❌ {slot} - [{d['tag']}] {d['name']} 削除しました",
                ephemeral=True
            )
            return

    await interaction.response.send_message("予約なし", ephemeral=True)

bot.tree.add_command(cancel)

# =========================
# /reset（管理者）
# =========================
@app_commands.command(name="reset", description="全削除（管理者）")
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
async def reset(interaction: discord.Interaction, type: app_commands.Choice[str]):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("権限なし", ephemeral=True)
        return

    reservations[type.value] = {}
    save_data(reservations)

    await interaction.response.send_message(
        f"🔥 {type.value} をリセットしました",
        ephemeral=True
    )

bot.tree.add_command(reset)

# =========================
# 起動
# =========================
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
