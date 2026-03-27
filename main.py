import discord
from discord.ext import commands
import requests
import os

# ---------------- CONFIG ---------------- #
TOKEN = os.getenv("TOKEN")

LTC_ADDRESS = "LYQA3NYHDaX5dW81EC5141SqqZKPdZR5dJ"
STAFF_ROLE_ID = 1486962183878479972
TICKET_CATEGORY_NAME = "📩 Tickets"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="$", intents=intents)

active_deals = {}
role_data = {}

# ---------------- PRICE ---------------- #
def get_ltc_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd"
        return requests.get(url).json()["litecoin"]["usd"]
    except:
        return None

# ---------------- CATEGORY ---------------- #
async def get_category(guild):
    cat = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not cat:
        cat = await guild.create_category(TICKET_CATEGORY_NAME)
    return cat

# ---------------- MODAL ---------------- #
class DealModal(discord.ui.Modal, title="Fill Deal Details"):

    trader = discord.ui.TextInput(label="Trader Username or ID", required=True)
    giving = discord.ui.TextInput(label="What are you giving?", style=discord.TextStyle.paragraph)
    receiving = discord.ui.TextInput(label="What is your trader giving?", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):

        category = await get_category(interaction.guild)

        channel = await interaction.guild.create_text_channel(
            name=f"ltc-{interaction.user.name}",
            category=category
        )

        role_data[channel.id] = {"sender": None, "receiver": None}

        embed = discord.Embed(title="📄 Deal Information", color=0x00ff00)
        embed.add_field(name="Trader", value=self.trader.value, inline=False)
        embed.add_field(name="You Give", value=self.giving.value, inline=False)
        embed.add_field(name="You Receive", value=self.receiving.value, inline=False)

        embed2 = discord.Embed(title="👤 Select Roles", color=0x00ff00)
        embed2.add_field(name="Sender", value="Not selected", inline=True)
        embed2.add_field(name="Receiver", value="Not selected", inline=True)

        await channel.send(embed=embed)
        await channel.send(embed=embed2, view=RoleView())

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# ---------------- ROLE UPDATE ---------------- #
async def update_roles(interaction):
    data = role_data.get(interaction.channel.id)

    embed = discord.Embed(title="👤 Select your role", color=0x00ff00)
    embed.add_field(name="Sender", value=data["sender"] or "Not selected", inline=True)
    embed.add_field(name="Receiver", value=data["receiver"] or "Not selected", inline=True)

    await interaction.response.edit_message(embed=embed, view=ConfirmView())

# ---------------- ROLE VIEW ---------------- #
class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Sender", style=discord.ButtonStyle.primary)
    async def sender(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_data[interaction.channel.id]["sender"] = interaction.user.mention
        await update_roles(interaction)

    @discord.ui.button(label="Receiver", style=discord.ButtonStyle.secondary)
    async def receiver(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_data[interaction.channel.id]["receiver"] = interaction.user.mention
        await update_roles(interaction)

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.danger)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_data[interaction.channel.id] = {"sender": None, "receiver": None}
        await update_roles(interaction)

    @discord.ui.button(label="Delete Ticket", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# ---------------- CONFIRM VIEW ---------------- #
class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Correct", style=discord.ButtonStyle.success)
    async def correct(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Roles confirmed. Now send deal:\nBuyer / Seller / Amount / Seller Wallet")

    @discord.ui.button(label="Incorrect", style=discord.ButtonStyle.danger)
    async def incorrect(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_data[interaction.channel.id] = {"sender": None, "receiver": None}
        await interaction.response.send_message("❌ Reset roles.", ephemeral=True)

# ---------------- DEAL VIEW ---------------- #
class DealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = active_deals.get(interaction.channel.id)

        if not data:
            return await interaction.response.send_message("No active deal.", ephemeral=True)

        if data["paid"]:
            await interaction.response.send_message("✅ Payment confirmed", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Payment not detected", ephemeral=True)

    @discord.ui.button(label="Release", style=discord.ButtonStyle.success)
    async def release(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = active_deals.get(interaction.channel.id)

        if not data or not data["paid"]:
            return await interaction.response.send_message("❌ Payment not done", ephemeral=True)

        embed = discord.Embed(
            title="✅ Release Payment",
            description=f"Send **{data['ltc']} LTC** to:\n`{data['seller_wallet']}`",
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# ---------------- PANEL ---------------- #
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request LTC", style=discord.ButtonStyle.success, emoji="💰")
    async def request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DealModal())

# ---------------- PANEL COMMAND ---------------- #
@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):

    embed = discord.Embed(
        title="💰 Litecoin Auto Middleman",
        description="Click below to start deal",
        color=0x00ff00
    )

    embed.add_field(
        name="Fees",
        value="Under $50 → Free\nUnder $250 → $0.5\n250+ → $1.5",
        inline=False
    )

    await ctx.send(embed=embed, view=PanelView())

# ---------------- DEAL HANDLER ---------------- #
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if message.channel.id in active_deals:
        return

    if not message.channel.name.startswith("ltc-"):
        return

    try:
        parts = message.content.split("/")
        if len(parts) < 4:
            return await message.channel.send("❌ Use: Buyer/Seller/Amount/Wallet")

        buyer = parts[0].strip()
        seller = parts[1].strip()
        usd = float(parts[2].strip())
        seller_wallet = parts[3].strip()

        price = get_ltc_price()
        if not price:
            return await message.channel.send("❌ Error fetching LTC price")

        fee = 0 if usd < 50 else (0.5 if usd < 250 else 1.5)
        total = usd + fee
        ltc_amount = round(total / price, 6)

        active_deals[message.channel.id] = {
            "buyer": buyer,
            "seller": seller,
            "ltc": ltc_amount,
            "seller_wallet": seller_wallet,
            "paid": False
        }

        embed = discord.Embed(
            title="💰 Payment Info",
            description=f"Send **{ltc_amount} LTC** to:\n`{LTC_ADDRESS}`",
            color=0x00ff00
        )

        await message.channel.send(embed=embed, view=DealView())

    except Exception as e:
        print(e)

# ---------------- FORCE PAID ---------------- #
@bot.command()
@commands.has_role(STAFF_ROLE_ID)
async def forcepaid(ctx):
    if ctx.channel.id in active_deals:
        active_deals[ctx.channel.id]["paid"] = True
        await ctx.send("✅ Marked as paid")

# ---------------- READY ---------------- #
@bot.event
async def on_ready():
    bot.add_view(PanelView())
    bot.add_view(RoleView())
    bot.add_view(ConfirmView())
    bot.add_view(DealView())
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)