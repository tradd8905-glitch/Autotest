import discord
from discord.ext import commands
import requests
import os

# ---------------- CONFIG ---------------- #
TOKEN = os.getenv("TOKEN")

LTC_ADDRESS = "LYQA3NYHDaX5dW81EC5141SqqZKPdZR5dJ"
STAFF_ROLE_ID = 1486962183878479972
OWNER_ROLE_ID = 1487032896249397308
TICKET_CATEGORY_NAME = "📩 Tickets"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="$", intents=intents)

active_deals = {}
role_data = {}

# ---------------- OWNER CHECK ---------------- #
def is_owner():
    async def predicate(ctx):
        return any(role.id == OWNER_ROLE_ID for role in ctx.author.roles)
    return commands.check(predicate)

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

    trader = discord.ui.TextInput(
        label="Trader User ID",
        placeholder="Enter Discord ID only",
        required=True
    )

    giving = discord.ui.TextInput(
        label="What are you giving?",
        style=discord.TextStyle.paragraph
    )

    receiving = discord.ui.TextInput(
        label="What is your trader giving?",
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):

        # VALIDATION
        if not self.trader.value.isdigit():
            return await interaction.response.send_message(
                "❌ Enter valid Discord User ID (numbers only)",
                ephemeral=True
            )

        # CHECK USER EXISTS
        try:
            user = await interaction.client.fetch_user(int(self.trader.value))
        except:
            return await interaction.response.send_message(
                "❌ Invalid user ID",
                ephemeral=True
            )

        category = await get_category(interaction.guild)

        channel = await interaction.guild.create_text_channel(
            name=f"ltc-{interaction.user.name}",
            category=category
        )

        role_data[channel.id] = {"sender": None, "receiver": None}

        trader_mention = f"<@{self.trader.value}>"
        content = f"{interaction.user.mention} {trader_mention}"

        embed = discord.Embed(
            description=(
                "👋 **Jace's Auto Middleman Service**\n\n"
                "Make sure to follow the steps and read carefully.\n"
                "By using this bot, you agree to ToS.\n\n"
                f"**{interaction.user.mention}'s side:**\n"
                f"```{self.giving.value}```\n\n"
                f"**{trader_mention}'s side:**\n"
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

        async def delete_callback(i):
            if i.user.id != interaction.user.id:
                return await i.response.send_message("❌ Not allowed", ephemeral=True)
            await i.channel.delete()

        delete_btn.callback = delete_callback
        view.add_item(delete_btn)

        await channel.send(content=content, embed=embed, view=view)

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

# ---------------- CONFIRM VIEW ---------------- #
class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Correct", style=discord.ButtonStyle.success)
    async def correct(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Roles confirmed. Send: Buyer/Seller/Amount/Wallet")

    @discord.ui.button(label="Incorrect", style=discord.ButtonStyle.danger)
    async def incorrect(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_data[interaction.channel.id] = {"sender": None, "receiver": None}
        await interaction.response.send_message("❌ Reset roles", ephemeral=True)

# ---------------- PANEL ---------------- #
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Request LTC", style=discord.ButtonStyle.success, emoji="💰")
    async def request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(DealModal())

# ---------------- PANEL COMMAND ---------------- #
@bot.command()
@commands.has_role(OWNER_ROLE_ID)
async def panel(ctx):

    color = 0x2b2d31  # SAME color for both embeds

    # -------- FIRST EMBED -------- #
    embed1 = discord.Embed(
        description=(
            "# Hatake Auto Middleman\n"
            "> - **Paid Service**\n"
            "> - Read our ToS before using the bot: <#1487042262377693316>\n\n"
            "## Fees:\n"
            "> - Deals $250+: $1.50\n"
            "> - Deals under $250: $0.50\n"
            "> - __Deals under $50 are **FREE**__"
        ),
        color=color
    )

    await ctx.send(embed=embed1)

    # -------- SECOND EMBED -------- #
    embed2 = discord.Embed(
        description="## <:Ltc:1487040906568663040>・Request Litecoin・<:Ltc:1487040906568663040>",
        color=color
    )

    view = discord.ui.View()

    request_btn = discord.ui.Button(
        label="Request LTC",
        style=discord.ButtonStyle.primary,
        emoji="<:Ltc:1468581658084245637>"
    )

    async def callback(interaction: discord.Interaction):
        await interaction.response.send_modal(DealModal())

    request_btn.callback = callback
    view.add_item(request_btn)

    await ctx.send(embed=embed2, view=view)


# ---------------- READY ---------------- #
@bot.event
async def on_ready():
    bot.add_view(PanelView())
    bot.add_view(RoleView())
    bot.add_view(ConfirmView())
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)