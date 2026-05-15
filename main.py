import os
import json
import discord
from discord.ext import commands
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

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# データ
# =========================
DATA_FILE = "reservations.json"
TYPES = ["建築", "訓練", "研究"]

# 9:00〜翌8:30（30分刻み）
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
# モーダル（予約入力）
# =========================
class YoyakuModal(discord.ui.Modal):

    def __init__(self, type_name: str):
        super().__init__(title=f"{type_name} 予約")
        self.type_name = type_name

    time = discord.ui.TextInput(label="時間（例 09:30）")
    tag = discord.ui.TextInput(label="同盟タグ")
    name = discord.ui.TextInput(label="名前")

    async def on_submit(self, interaction: discord.Interaction):

        t = self.time.value

        if t in reservations[self.type_name]:
            await interaction.response.send_message("その時間は予約済みです", ephemeral=True)
            return

        reservations[self.type_name][t] = {
            "tag": self.tag.value,
            "name": self.name.value,
            "discord_id": interaction.user.id
        }

        save_data(reservations)

        await interaction.response.send_message(
            f"✅ {self.type_name} {t} 予約完了\n[{self.tag.value}] {self.name.value}",
            ephemeral=True
        )

# =========================
# /yoyaku（UI）
# =========================
class TypeView(discord.ui.View):

    @discord.ui.button(label="建築", style=discord.ButtonStyle.primary)
    async def b1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(YoyakuModal("建築"))

    @discord.ui.button(label="訓練", style=discord.ButtonStyle.danger)
    async def b2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(YoyakuModal("訓練"))

    @discord.ui.button(label="研究", style=discord.ButtonStyle.success)
    async def b3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(YoyakuModal("研究"))

@bot.tree.command(name="yoyaku", description="予約作成")
async def yoyaku(interaction: discord.Interaction):
    await interaction.response.send_message(
        "タイプを選んでください",
        view=TypeView(),
        ephemeral=True
    )

# =========================
# /list（全時間表示）
# =========================
@bot.tree.command(name="list", description="予約一覧")
async def list_cmd(interaction: discord.Interaction, type: str):

    if type not in TYPES:
        await interaction.response.send_message("建築/訓練/研究のみ", ephemeral=True)
        return

    data = reservations[type]
    text = f"【{type} 予約一覧】\n\n"

    for slot in TIME_SLOTS:
        if slot in data:
            d = data[slot]
            text += f"❌ {slot} - [{d['tag']}] {d['name']}\n"
        else:
            text += f"🟢 {slot}\n"

    await interaction.response.send_message(text, ephemeral=False)

# =========================
# /mylist（自分強調）
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
# /cancel（簡易削除）
# =========================
@bot.tree.command(name="cancel", description="予約削除")
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

@bot.tree.command(name="reset", description="管理者用リセット")
async def reset(interaction: discord.Interaction):

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("権限なし", ephemeral=True)
        return

    await interaction.response.send_message("リセット対象選択", view=ResetView(), ephemeral=True)

# =========================
# 起動
# =========================
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
