import os
import json
import discord
from discord.ext import commands
import logging

# =========================
# ログ
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# =========================
# Intents
# =========================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# データ保存
# =========================
DATA_FILE = "reservations.json"

TYPES = ["建築", "訓練", "研究"]

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
# UI: type選択
# =========================
class TypeView(discord.ui.View):

    @discord.ui.button(label="建築", style=discord.ButtonStyle.primary)
    async def b1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "時間・同盟・名前を入力してください",
            view=ReservationModalView("建築"),
            ephemeral=True
        )

    @discord.ui.button(label="訓練", style=discord.ButtonStyle.danger)
    async def b2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "時間・同盟・名前を入力してください",
            view=ReservationModalView("訓練"),
            ephemeral=True
        )

    @discord.ui.button(label="研究", style=discord.ButtonStyle.success)
    async def b3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "時間・同盟・名前を入力してください",
            view=ReservationModalView("研究"),
            ephemeral=True
        )

# =========================
# モーダル
# =========================
class ReservationModalView(discord.ui.View):
    def __init__(self, type_name):
        super().__init__(timeout=None)
        self.type_name = type_name

        self.add_item(TimeInput(type_name))

class TimeInput(discord.ui.Modal, title="予約入力"):

    def __init__(self, type_name):
        super().__init__()
        self.type_name = type_name

    time = discord.ui.TextInput(label="時間 (例 09:30)")
    tag = discord.ui.TextInput(label="同盟タグ")
    name = discord.ui.TextInput(label="名前")

    async def on_submit(self, interaction: discord.Interaction):

        t = self.time.value
        tag = self.tag.value
        name = self.name.value

        if t in reservations[self.type_name]:
            await interaction.response.send_message("その時間は予約済みです", ephemeral=True)
            return

        reservations[self.type_name][t] = {
            "tag": tag,
            "name": name,
            "discord_id": interaction.user.id
        }

        save_data(reservations)

        await interaction.response.send_message(
            f"✅ {t} - [{tag}] {name} 予約完了",
            ephemeral=True
        )

# =========================
# /yoyaku
# =========================
@bot.tree.command(name="yoyaku")
async def yoyaku(interaction: discord.Interaction):
    await interaction.response.send_message(
        "タイプを選んでください",
        view=TypeView(),
        ephemeral=True
    )

# =========================
# /list
# =========================
class ListView(discord.ui.View):

    @discord.ui.button(label="建築")
    async def b1(self, interaction, button):
        await show_list(interaction, "建築")

    @discord.ui.button(label="訓練")
    async def b2(self, interaction, button):
        await show_list(interaction, "訓練")

    @discord.ui.button(label="研究")
    async def b3(self, interaction, button):
        await show_list(interaction, "研究")

async def show_list(interaction, type_name):

    text = f"【{type_name}】\n\n"

    for slot, data in reservations[type_name].items():
        text += f"{slot} - [{data['tag']}] {data['name']}\n"

    await interaction.response.send_message(text, ephemeral=True)

@bot.tree.command(name="list")
async def list_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("タイプ選択", view=ListView(), ephemeral=True)

# =========================
# /mylist
# =========================
@bot.tree.command(name="mylist")
async def mylist(interaction: discord.Interaction):

    text = "【あなたの予約】\n\n"

    for t in TYPES:
        for slot, data in reservations[t].items():
            if data["discord_id"] == interaction.user.id:
                text += f"{slot} - [{data['tag']}] {data['name']}\n"

    await interaction.response.send_message(text, ephemeral=True)

# =========================
# /cancel（簡易版）
# =========================
@bot.tree.command(name="cancel")
async def cancel(interaction: discord.Interaction):

    user_id = interaction.user.id

    for t in TYPES:
        for slot, data in list(reservations[t].items()):
            if data["discord_id"] == user_id:
                del reservations[t][slot]
                save_data(reservations)

                await interaction.response.send_message(
                    f"❌ {slot} - [{data['tag']}] {data['name']} 削除",
                    ephemeral=True
                )
                return

    await interaction.response.send_message("予約なし", ephemeral=True)

# =========================
# /reset（管理者）
# =========================
class ResetView(discord.ui.View):

    @discord.ui.button(label="建築", style=discord.ButtonStyle.primary)
    async def b1(self, interaction, button):
        reservations["建築"] = {}
        save_data(reservations)
        await interaction.response.send_message("建築リセット", ephemeral=True)

    @discord.ui.button(label="訓練", style=discord.ButtonStyle.danger)
    async def b2(self, interaction, button):
        reservations["訓練"] = {}
        save_data(reservations)
        await interaction.response.send_message("訓練リセット", ephemeral=True)

    @discord.ui.button(label="研究", style=discord.ButtonStyle.success)
    async def b3(self, interaction, button):
        reservations["研究"] = {}
        save_data(reservations)
        await interaction.response.send_message("研究リセット", ephemeral=True)

@bot.tree.command(name="reset")
async def reset(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("権限なし", ephemeral=True)
        return

    await interaction.response.send_message("リセット対象選択", view=ResetView(), ephemeral=True)

# =========================
# 起動
# =========================
@bot.event
async def on_ready():
    await bot.tree.sync()
    logger.info(f"Logged in as {bot.user}")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
