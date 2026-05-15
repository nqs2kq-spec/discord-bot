import os
import json
import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timedelta

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

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# データ
# =========================
DATA_FILE = "reservations.json"

TYPES = ["建築", "訓練", "研究"]

TIME_SLOTS = []

start = datetime.strptime("09:00", "%H:%M")
end = start + timedelta(days=1)

while start < end:
    TIME_SLOTS.append(start.strftime("%H:%M"))
    start += timedelta(minutes=30)


def load_data():

    if not os.path.exists(DATA_FILE):
        data = {t: {} for t in TYPES}

        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return data

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

    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(e)

    logger.info(f"Logged in as {bot.user}")


# =========================
# /yoyaku
# =========================
@app_commands.describe(
    type="建築 / 訓練 / 研究",
    game_account_name="ゲーム内名前",
    alliance_tag="同盟タグ",
    reserve_time="予約時間（例 09:30）"
)
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
@bot.tree.command(name="yoyaku", description="官職予約")
async def yoyaku(
    interaction: discord.Interaction,
    type: app_commands.Choice[str],
    game_account_name: str,
    alliance_tag: str,
    reserve_time: str
):

    reserve_type = type.value

    # 時間チェック
    if reserve_time not in TIME_SLOTS:

        await interaction.response.send_message(
            "30分刻み・09:00〜翌08:30 で入力してください",
            ephemeral=True
        )
        return

    # 同タイプ重複防止
    for slot, d in reservations[reserve_type].items():

        if d["discord_id"] == interaction.user.id:

            await interaction.response.send_message(
                f"あなたは既に {reserve_type} を予約しています",
                ephemeral=True
            )
            return

    # 時間重複防止
    if reserve_time in reservations[reserve_type]:

        d = reservations[reserve_type][reserve_time]

        await interaction.response.send_message(
            f"その時間は予約済みです\n"
            f"[{d['tag']}] {d['name']}",
            ephemeral=True
        )
        return

    # 登録
    reservations[reserve_type][reserve_time] = {
        "name": game_account_name,
        "tag": alliance_tag,
        "discord_id": interaction.user.id
    }

    save_data(reservations)

    await interaction.response.send_message(
        f"✅ 予約完了\n"
        f"{reserve_type} {reserve_time}\n"
        f"[{alliance_tag}] {game_account_name}",
        ephemeral=True
    )


# =========================
# /list
# =========================
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
@bot.tree.command(name="list", description="予約一覧")
async def list_cmd(
    interaction: discord.Interaction,
    type: app_commands.Choice[str]
):

    reserve_type = type.value

    text = f"【{reserve_type} 予約一覧】\n\n"

    for slot in TIME_SLOTS:

        if slot in reservations[reserve_type]:

            d = reservations[reserve_type][slot]

            text += (
                f"❌ {slot} - "
                f"[{d['tag']}] {d['name']}\n"
            )

        else:
            text += f"🟢 {slot}\n"

    await interaction.response.send_message(
        text,
        ephemeral=False
    )


# =========================
# /mylist
# =========================
@bot.tree.command(name="mylist", description="自分の予約一覧")
async def mylist(interaction: discord.Interaction):

    uid = interaction.user.id

    icons = {
        "建築": "🏗",
        "訓練": "⚔",
        "研究": "🧪"
    }

    text = "【あなたの予約】\n\n"

    found = False

    for t in TYPES:

        for slot, d in reservations[t].items():

            if d["discord_id"] == uid:

                text += (
                    f"{icons[t]} "
                    f"{t} {slot} - "
                    f"[{d['tag']}] {d['name']}\n"
                )

                found = True

    if not found:
        text = "現在予約はありません"

    await interaction.response.send_message(
        text,
        ephemeral=True
    )


# =========================
# /cancel
# =========================
class CancelSelect(discord.ui.Select):

    def __init__(self, user_id):

        self.user_id = user_id

        options = []

        for t in TYPES:

            for slot, d in reservations[t].items():

                if d["discord_id"] == user_id:

                    options.append(
                        discord.SelectOption(
                            label=f"{t} {slot}",
                            description=f"[{d['tag']}] {d['name']}",
                            value=f"{t}|{slot}"
                        )
                    )

        if not options:

            options.append(
                discord.SelectOption(
                    label="予約なし",
                    value="none"
                )
            )

        super().__init__(
            placeholder="削除する予約を選択",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        if self.values[0] == "none":

            await interaction.response.send_message(
                "削除できる予約がありません",
                ephemeral=True
            )
            return

        reserve_type, slot = self.values[0].split("|")

        if slot in reservations[reserve_type]:

            d = reservations[reserve_type][slot]

            del reservations[reserve_type][slot]

            save_data(reservations)

            await interaction.response.send_message(
                f"❌ 削除完了\n"
                f"{reserve_type} {slot}\n"
                f"[{d['tag']}] {d['name']}",
                ephemeral=True
            )


class CancelView(discord.ui.View):

    def __init__(self, user_id):

        super().__init__(timeout=60)

        self.add_item(CancelSelect(user_id))


@bot.tree.command(name="cancel", description="予約削除")
async def cancel(interaction: discord.Interaction):

    await interaction.response.send_message(
        "削除する予約を選択してください",
        view=CancelView(interaction.user.id),
        ephemeral=True
    )


# =========================
# /reset
# =========================
@app_commands.choices(type=[
    app_commands.Choice(name="建築", value="建築"),
    app_commands.Choice(name="訓練", value="訓練"),
    app_commands.Choice(name="研究", value="研究"),
])
@bot.tree.command(name="reset", description="予約全削除（管理者専用）")
async def reset(
    interaction: discord.Interaction,
    type: app_commands.Choice[str]
):

    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "管理者のみ使用可能",
            ephemeral=True
        )
        return

    reserve_type = type.value

    reservations[reserve_type] = {}

    save_data(reservations)

    await interaction.response.send_message(
        f"🔥 {reserve_type} を全リセットしました",
        ephemeral=True
    )


# =========================
# 起動
# =========================
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
