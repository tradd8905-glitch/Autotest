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


# ---------------- PANEL VIEW ---------------- #
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request Litecoin", style=discord.ButtonStyle.success, emoji="💸")
    async def request(self, interaction: discord.Interaction, button: discord.ui.Button):

        category = await get_category(interaction.guild)

        channel = await interaction.guild.create_text_channel(
            name=f"ltc-{interaction.user.name}",
            category=category
        )

        await channel.send(
            f"📩 {interaction.user.mention}\n\n"
            "**Fill this format:**\n"
            "`Buyer / Seller / Amount USD / Seller LTC Address`"
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )


# ---------------- PANEL COMMAND ---------------- #
@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):

    embed = discord.Embed(
        title="Jace's Auto Middleman",
        description="• Paid Service\n• Read ToS before using: #tos-crypto",
        color=0x00ff00  # GREEN
    )

    embed.add_field(
        name="📊 Fees",
        value=(
            "• Deals $250+: $1.50\n"
            "• Deals under $250: $0.50\n"
            "• Deals under $50 are **FREE**"
        ),
        inline=False
    )

    embed.set_footer(text="Click below to start a deal")

    await ctx.send(embed=embed, view=PanelView())


# ---------------- MESSAGE HANDLER ---------------- #
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
            return await message.channel.send(
                "❌ Format:\nBuyer / Seller / Amount / Seller Wallet"
            )

        buyer = parts[0].strip()
        seller = parts[1].strip()
        usd = float(parts[2].strip())
        seller_wallet = parts[3].strip()

        price = get_ltc_price()
        if not price:
            return await message.channel.send("❌ Failed to fetch LTC price")

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
            title="💰 Payment Information",
            description=(
                f"Send **{ltc_amount} LTC** to:\n"
                f"`{LTC_ADDRESS}`"
            ),
            color=0x00ff00
        )

        await message.channel.send(embed=embed, view=DealView())

    except Exception as e:
        print(e)
        await message.channel.send("❌ Error processing deal")


# ---------------- DEAL BUTTONS ---------------- #
class DealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Refresh Payment", style=discord.ButtonStyle.secondary)
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
        if not data:
            return await interaction.response.send_message("No active deal.", ephemeral=True)

        if not data["paid"]:
            return await interaction.response.send_message("❌ Payment not done", ephemeral=True)

        embed = discord.Embed(
            title="✅ Release Payment",
            description=(
                f"Send **{data['ltc']} LTC** to:\n"
                f"`{data['seller_wallet']}`"
            ),
            color=0x00ff00
        )

        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()


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
    bot.add_view(DealView())
    print(f"✅ Logged in as {bot.user}")


bot.run(TOKEN)
