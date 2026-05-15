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
# データ管理
# =========================
DATA_FILE = "reservations.json"

TYPES = ["建築", "訓練", "研究"]

# 9:00〜翌8:30（30分刻み）
from datetime import datetime, timedelta

TIME_SLOTS = []
start = datetime.strptime("09:00", "%H:%M")
end = start + timedelta(days=1)

while start < end:
    TIME_SLOTS.append(start.strftime("%H:%M"))
    start += timedelta(minutes=30)


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
# /yoyaku（安定入力型）
# =========================
@app_commands.describe(
    type="建築 / 訓練 / 研究",
    game_account_name="ゲーム名",
    alliance_tag="同盟タグ",
    reserve_time="時間（例 09:30）"
)
@bot.tree.command(name="yoyaku", description="官職予約")
async def yoyaku(
    interaction: discord.Interaction,
    type: str,
    game_account_name: str,
    alliance_tag: str,
    reserve_time: str
):

    if type not in TYPES:
        await interaction.response.send_message("タイプエラー", ephemeral=True)
        return

    if reserve_time not in TIME_SLOTS:
        await interaction.response.send_message("時間が不正です", ephemeral=True)
        return

    if reserve_time in reservations[type]:
        await interaction.response.send_message("その時間は予約済みです", ephemeral=True)
        return

    reservations[type][reserve_time] = {
        "name": game_account_name,
        "tag": alliance_tag,
        "discord_id": interaction.user.id
    }

    save_data(reservations)

    await interaction.response.send_message(
        f"✅ {type} {reserve_time} 予約完了\n[{alliance_tag}] {game_account_name}",
        ephemeral=True
    )

# =========================
# /list（全時間表示）
# =========================
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
@bot.tree.command(name="list", description="予約一覧")
async def list_cmd(interaction: discord.Interaction, type: app_commands.Choice[str]):

    data = reservations[type.value]
    text = f"【{type.value} 予約一覧】\n\n"

    for slot in TIME_SLOTS:
        if slot in data:
            d = data[slot]
            text += f"❌ {slot} - [{d['tag']}] {d['name']}\n"
        else:
            text += f"🟢 {slot}\n"

    await interaction.response.send_message(text, ephemeral=False)

# =========================
# /mylist（自分だけ）
# =========================
@bot.tree.command(name="mylist", description="自分の予約")
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
# /cancel（自分削除）
# =========================
@bot.tree.command(name="cancel", description="自分の予約削除")
async def cancel(interaction: discord.Interaction):

    uid = interaction.user.id

    for t in TYPES:
        for slot, d in list(reservations[t].items()):

            if d["discord_id"] == uid:

                del reservations[t][slot]
                save_data(reservations)

                await interaction.response.send_message(
                    f"❌ {slot} - [{d['tag']}] {d['name']} 削除",
                    ephemeral=True
                )
                return

    await interaction.response.send_message("予約なし", ephemeral=True)

# =========================
# /reset（管理者）
# =========================
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
@bot.tree.command(name="reset", description="管理者用リセット")
async def reset(interaction: discord.Interaction, type: app_commands.Choice[str]):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("権限なし", ephemeral=True)
        return

    reservations[type.value] = {}
    save_data(reservations)

    await interaction.response.send_message(
        f"🔥 {type.value} リセット完了",
        ephemeral=True
    )

# =========================
# 起動
# =========================
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
