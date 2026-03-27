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

        # FIXED UI PART (INDENTED CORRECTLY)
        trader = f"<@{self.trader.value}>" if self.trader.value.isdigit() else self.trader.value
        content = f"{interaction.user.mention} {trader}"

        embed = discord.Embed(
            description=(
                "👋 **Jace's Auto Middleman Service**\n\n"
                "Make sure to follow the steps and read the instructions carefully.\n"
                "By using this bot, you agree to ToS.\n\n"
                f"**{interaction.user.mention}'s side:**\n"
                f"```{self.giving.value}```\n\n"
                f"**{trader}'s side:**\n"
                f"```{self.receiving.value}```"
            ),
            color=0x2b2d31
        )

        view = discord.ui.View()

        delete_btn = discord.ui.Button(
            label="Delete Ticket",
            style=discord.ButtonStyle.danger,
            emoji="❌"
        )

        async def delete_callback(interaction2):
            await interaction2.channel.delete()

        delete_btn.callback = delete_callback
        view.add_item(delete_btn)

        await channel.send(content=content, embed=embed, view=view)

        # ROLE SELECTION (UNCHANGED)
        embed2 = discord.Embed(title="👤 Select your role", color=0x00ff00)
        embed2.add_field(name="Sender", value="Not selected", inline=True)
        embed2.add_field(name="Receiver", value="Not selected", inline=True)

        await channel.send(embed=embed2, view=RoleView())

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

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

# ---------------- READY ---------------- #
@bot.event
async def on_ready():
    bot.add_view(PanelView())
    bot.add_view(RoleView())
    bot.add_view(ConfirmView())
    bot.add_view(DealView())
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)