import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
import json
import os
import math

# --- Configuration ---
TOKEN = 'MTQ1MzE4NTczNzU1NzI3ODc3Mw.G2ijrK.haZO5odUnY61ARM4z3bftcJeOZiQMhDeAv8GXM' # Your actual bot token
PREFIX = '!' # While not used for slash commands, kept for potential future prefix commands

# List of your cryptocurrencies - now only Campton Coin
CRYPTO_NAMES = ["Campton Coin"]

# File to store market and user data
DATA_FILE = 'stock_market_data.json'

# --- Price Range Configuration ---
MIN_PRICE = 50.00
MAX_PRICE = 230.00
INITIAL_PRICE = 120.00 # Starting price for Campton Coin

# --- Discord Channel IDs ---
ANNOUNCEMENT_CHANNEL_ID = 1453194843009585326 # YOUR CHANNEL ID for market updates
TICKET_CATEGORY_ID = 1453203314689708072 # Your Tickets Category ID
HELP_DESK_CHANNEL_ID = 1453208931034726410 # YOUR #help-desk channel ID

# --- Data Storage (Simple JSON file for persistence) ---
def load_data():
    data = {"coins": {}, "users": {}, "tickets": {}} # Default structure
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                loaded_data = json.load(f)
                # Safely update default structure with loaded data
                data.update(loaded_data)
                # Ensure all top-level keys exist if they were missing in an older file
                if "coins" not in data:
                    data["coins"] = {}
                if "users" not in data:
                    data["users"] = {}
                if "tickets" not in data: # <--- THIS IS THE KEY FIX
                    data["tickets"] = {}
            except json.JSONDecodeError:
                print(f"Warning: {DATA_FILE} is corrupted or empty. Starting with fresh data.")
    return data

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Bot Initialization ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

bot.owner_id = 357681843790675978 # Your Discord User ID

# Global data store
market_data = load_data()

# Initialize coin prices if not already set or if the coin list changed
if "Campton Coin" not in market_data["coins"] or len(market_data["coins"]) != len(CRYPTO_NAMES):
    market_data["coins"] = {}
    for name in CRYPTO_NAMES:
        market_data["coins"][name] = {"price": INITIAL_PRICE}
    save_data(market_data)
# --- Ensure loaded price is within bounds ---
elif market_data["coins"]["Campton Coin"]["price"] < MIN_PRICE or market_data["coins"]["Campton Coin"]["price"] > MAX_PRICE:
    print(f"Detected Campton Coin price outside bounds ({market_data['coins']['Campton Coin']['price']:.2f}). Resetting to INITIAL_PRICE.")
    market_data["coins"]["Campton Coin"]["price"] = INITIAL_PRICE
    save_data(market_data)


# --- Custom Check for Slash Commands (Owner Only) ---
async def is_bot_owner_slash(interaction: discord.Interaction) -> bool:
    return interaction.user.id == bot.owner_id

# --- Helper function to check decimal places ---
def has_more_than_three_decimals(number: float) -> bool:
    s = str(number)
    if '.' in s:
        decimal_part = s.split('.')[1]
        return len(decimal_part) > 3
    return False

# --- Stock Market Logic ---
def update_prices():
    """Simulates price fluctuations for all coins, keeping them within a range."""
    for coin_name in market_data["coins"]:
        current_price = market_data["coins"][coin_name]["price"]
        change_percent = random.uniform(-0.10, 0.10)
        new_price = current_price * (1 + change_percent)
        new_price = max(MIN_PRICE, min(MAX_PRICE, new_price))
        market_data["coins"][coin_name]["price"] = round(new_price, 2)
    save_data(market_data)

def get_user_data(user_id):
    """Retrieves or initializes a user's portfolio."""
    if str(user_id) not in market_data["users"]:
        market_data["users"][str(user_id)] = {"balance": 0.0, "portfolio": {}}
    return market_data["users"][str(user_id)]

def buy_coin(user_id, coin_name, quantity):
    """Handles buying a coin."""
    user = get_user_data(user_id)
    if coin_name not in market_data["coins"]:
        return "Coin not found."

    coin_price = market_data["coins"][coin_name]["price"]
    cost = coin_price * quantity

    if user["balance"] < cost:
        return f"Insufficient funds. You need {cost:.2f} dollars but only have {user['balance']:.2f} dollars."

    user["balance"] -= cost
    user["portfolio"][coin_name] = user["portfolio"].get(coin_name, 0.0) + quantity
    save_data(market_data)
    return f"Successfully bought {quantity} {coin_name}(s) for {cost:.2f} dollars."

def sell_coin(user_id, coin_name, quantity):
    """Handles selling a coin."""
    user = get_user_data(user_id)
    if coin_name not in market_data["coins"]:
        return "Coin not found."
    if coin_name not in user["portfolio"] or user["portfolio"][coin_name] < quantity:
        return f"You don't own {quantity} {coin_name}(s). You have {user['portfolio'].get(coin_name, 0.0):.3f}."

    coin_price = market_data["coins"][coin_name]["price"]
    revenue = coin_price * quantity

    user["balance"] += revenue
    user["portfolio"][coin_name] -= quantity
    if user["portfolio"][coin_name] <= 0.0001:
        del user["portfolio"][coin_name]
    save_data(market_data)
    return f"Successfully sold {quantity} {coin_name}(s) for {revenue:.2f} dollars."

# --- Scheduled Task ---
@tasks.loop(hours=72)
async def scheduled_price_update():
    print("Running scheduled price update...")
    update_prices()
    if ANNOUNCEMENT_CHANNEL_ID:
        channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            current_price = market_data["coins"]["Campton Coin"]["price"]
            embed = discord.Embed(
                title="📈 Market Update: Campton Coin 📉",
                description=f"The price of Campton Coin has updated to **{current_price:.2f} dollars**.",
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)
        else:
            print(f"Warning: Announcement channel with ID {ANNOUNCEMENT_CHANNEL_ID} not found.")

@scheduled_price_update.before_loop
async def before_scheduled_price_update():
    await bot.wait_until_ready()
    print("Scheduled price update task is waiting for bot to be ready...")

# --- Ticket System Classes ---
class OpenTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Open New Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        global market_data, TICKET_CATEGORY_ID, HELP_DESK_CHANNEL_ID

        if not TICKET_CATEGORY_ID:
            await interaction.followup.send("Ticket system is not fully configured. Please contact the bot owner.", ephemeral=True)
            return

        # Check if user already has an open ticket
        for ticket_id, ticket_info in market_data["tickets"].items():
            if ticket_info["user_id"] == interaction.user.id and ticket_info["status"] == "open":
                existing_channel = bot.get_channel(int(ticket_id))
                if existing_channel:
                    await interaction.followup.send(f"You already have an open ticket: {existing_channel.mention}. Please use that ticket or close it first.", ephemeral=True)
                    return

        category = bot.get_channel(TICKET_CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.followup.send("The ticket category could not be found or is misconfigured. Please contact the bot owner.", ephemeral=True)
            return

        # Permissions for the new ticket channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        owner = await bot.fetch_user(bot.owner_id)
        if owner:
            overwrites[owner] = discord.PermissionOverwrite(view_channel=True, send_messages=True)


        ticket_channel_name = f"ticket-{interaction.user.name.lower().replace(' ', '-')}-{interaction.user.discriminator or interaction.user.id}"
        try:
            new_channel = await category.create_text_channel(ticket_channel_name, overwrites=overwrites)
            
            market_data["tickets"][str(new_channel.id)] = {
                "user_id": interaction.user.id,
                "issue": "No specific issue provided via button.",
                "status": "open",
                "created_at": discord.utils.utcnow().isoformat()
            }
            save_data(market_data)

            ticket_embed = discord.Embed(
                title=f"New Ticket for {interaction.user.display_name}",
                description="A new ticket has been opened. Please describe your issue here.",
                color=discord.Color.orange()
            )
            ticket_embed.add_field(name="User", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            ticket_embed.set_footer(text="A staff member will be with you shortly.")

            await new_channel.send(f"{interaction.user.mention}", embed=ticket_embed)
            await interaction.followup.send(f"Your ticket has been created! Please go to {new_channel.mention} to discuss your issue.", ephemeral=True)

            if owner:
                try:
                    await owner.send(f"A new ticket has been opened by {interaction.user.display_name} in {new_channel.mention}.")
                except discord.Forbidden:
                    print(f"Could not DM owner about new ticket. DMs might be disabled.")

        except discord.Forbidden:
            await interaction.followup.send("I don't have the necessary permissions to create channels. Please check my role permissions.", ephemeral=True)
        except Exception as e:
            print(f"Error creating ticket: {e}")
            await interaction.followup.send(f"An error occurred while creating your ticket: {e}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(OpenTicketButton())

# --- Discord Bot Events and Slash Commands ---

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    bot.add_view(TicketView())
    await bot.tree.sync()
    print("Slash commands synced!")
    scheduled_price_update.start()
    print("Scheduled price update task started.")

@bot.tree.command(name='prices', description='Displays the current price of Campton Coin.')
@app_commands.check(is_bot_owner_slash)
async def prices(interaction: discord.Interaction):
    """Displays the current prices of all cryptocurrencies."""
    await interaction.response.defer()
    update_prices()
    embed = discord.Embed(title="Current Crypto Market Prices", color=0x00ff00)
    for coin_name, data in market_data["coins"].items():
        embed.add_field(name=coin_name, value=f"{data['price']:.2f} dollars", inline=True)
    await interaction.followup.send(embed=embed)

@prices.error
async def prices_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You must be the bot owner to use this command.", ephemeral=True)
    else:
        if interaction.response.is_done():
            await interaction.followup.send(f"An unexpected error occurred: {error}", ephemeral=True)
        else:
            await interaction.response.send_message(f"An unexpected error occurred: {error}", ephemeral=True)


@bot.tree.command(name='balance', description='Shows your current balance and portfolio.')
async def balance(interaction: discord.Interaction):
    """Shows your current balance and portfolio."""
    await interaction.response.defer()
    user = get_user_data(interaction.user.id)
    embed = discord.Embed(title=f"{interaction.user.display_name}'s Portfolio", color=0x0099ff)
    embed.add_field(name="Cash Balance", value=f"{user['balance']:.2f} dollars", inline=False)

    if user["portfolio"]:
        portfolio_str = ""
        total_value = 0
        for coin_name, quantity in user["portfolio"].items():
            current_price = market_data["coins"].get(coin_name, {}).get("price", 0)
            coin_value = current_price * quantity
            total_value += coin_value
            portfolio_str += f"- {coin_name}: **{quantity:.3f}** units (Value: {coin_value:.2f} dollars)\n"
        embed.add_field(name="Holdings", value=portfolio_str, inline=False)
        embed.add_field(name="Total Portfolio Value", value=f"{total_value:.2f} dollars", inline=False)
    else:
        embed.add_field(name="Holdings", value="You own no cryptocurrencies.", inline=False)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name='buy', description='Buys a specified quantity of Campton Coin (up to 3 decimal places).')
@app_commands.describe(quantity='The number of Campton Coins to buy (e.g., 0.324).')
async def buy(interaction: discord.Interaction, quantity: float):
    """Buys a specified quantity of Campton Coin."""
    await interaction.response.defer(ephemeral=True)
    coin_name = "Campton Coin"

    if quantity <= 0:
        await interaction.followup.send("You must buy a positive amount.", ephemeral=True)
        return

    if has_more_than_three_decimals(quantity):
        await interaction.followup.send("You can only buy Campton Coin with up to 3 decimal places (e.g., 0.123).", ephemeral=True)
        return

    result = buy_coin(interaction.user.id, coin_name, quantity)
    await interaction.followup.send(result, ephemeral=True)

@bot.tree.command(name='sell', description='Sells a specified quantity of Campton Coin (up to 3 decimal places).')
@app_commands.describe(quantity='The number of Campton Coins to sell (e.g., 0.123).')
async def sell(interaction: discord.Interaction, quantity: float):
    """Sells a specified quantity of Campton Coin."""
    await interaction.response.defer(ephemeral=True)
    coin_name = "Campton Coin"

    if quantity <= 0:
        await interaction.followup.send("You must sell a positive amount.", ephemeral=True)
        return

    if has_more_than_three_decimals(quantity):
        await interaction.followup.send("You can only sell Campton Coin with up to 3 decimal places (e.g., 0.123).", ephemeral=True)
        return

    result = sell_coin(interaction.user.id, coin_name, quantity)
    await interaction.followup.send(result, ephemeral=True)

@bot.tree.command(name='addfunds', description='Adds funds to a specified user\'s balance. (Bot Owner Only)')
@app_commands.describe(member='The user to add funds to.', amount='The amount of funds to add.')
async def add_funds(interaction: discord.Interaction, member: discord.Member, amount: float):
    """Adds funds to a specified user's balance. (Bot Owner Only)"""
    await interaction.response.defer(ephemeral=True)

    if interaction.user.id != bot.owner_id:
        await interaction.followup.send("You must be the bot owner to use this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.followup.send("Amount must be greater than 0.", ephemeral=True)
        return

    user_data = get_user_data(member.id)
    user_data["balance"] += amount
    save_data(market_data)

    await interaction.followup.send(f"Successfully added {amount:.2f} dollars to {member.display_name}'s balance. Their new balance is {user_data['balance']:.2f} dollars.", ephemeral=True)

@bot.tree.command(name='withdraw', description='Requests a withdrawal of funds from your balance. Funds are deducted upon owner approval.')
@app_commands.describe(amount='The amount of funds to request for withdrawal.')
async def withdraw(interaction: discord.Interaction, amount: float):
    """Requests a withdrawal of funds from your balance. Funds are deducted upon owner approval."""
    await interaction.response.defer(ephemeral=True)

    if amount <= 0:
        await interaction.followup.send("You must request a positive amount for withdrawal.", ephemeral=True)
        return

    user_data = get_user_data(interaction.user.id)
    if user_data["balance"] < amount:
        await interaction.followup.send(f"Insufficient funds. You only have {user_data['balance']:.2f} dollars.", ephemeral=True)
        return

    owner = await bot.fetch_user(bot.owner_id)
    if owner:
        try:
            withdrawal_embed = discord.Embed(
                title="❗ New Withdrawal Request ❗",
                description=f"**{interaction.user.display_name}** (`{interaction.user.id}`) has requested a withdrawal.",
                color=discord.Color.red()
            )
            withdrawal_embed.add_field(name="Requested Amount", value=f"{amount:.2f} dollars", inline=False)
            withdrawal_embed.add_field(name="User's Current Balance", value=f"{user_data['balance']:.2f} dollars", inline=False)
            withdrawal_embed.set_footer(text=f"To approve, use /approvewithdrawal {interaction.user.id} {amount}")

            await owner.send(embed=withdrawal_embed)
            await interaction.followup.send(f"Your withdrawal request for {amount:.2f} dollars has been sent to the bot owner for approval. Your balance remains {user_data['balance']:.2f} dollars for now.", ephemeral=True)
        except discord.Forbidden:
            print(f"Could not send DM to owner {owner.name} about withdrawal request. DMs might be disabled.")
            await interaction.followup.send("Could not send the withdrawal request to the bot owner. Please ensure the bot can DM the owner.", ephemeral=True)
    else:
        await interaction.followup.send("Could not find the bot owner to send the withdrawal request. Please ensure the bot owner is correctly configured.", ephemeral=True)

@bot.tree.command(name='approvewithdrawal', description='Approves a user\'s withdrawal request and deducts funds. (Bot Owner Only)')
@app_commands.describe(user_id='The ID of the user whose withdrawal to approve.', amount='The amount to deduct.')
async def approve_withdrawal(interaction: discord.Interaction, user_id: str, amount: float):
    """Approves a user's withdrawal request and deducts funds. (Bot Owner Only)"""
    await interaction.response.defer(ephemeral=True)

    if interaction.user.id != bot.owner_id:
        await interaction.followup.send("You must be the bot owner to use this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.followup.send("Amount must be greater than 0.", ephemeral=True)
        return

    try:
        target_user = await bot.fetch_user(int(user_id))
    except ValueError:
        await interaction.followup.send("Invalid user ID provided. Please provide a numerical user ID.", ephemeral=True)
        return
    except discord.NotFound:
        await interaction.followup.send("User not found with the provided ID.", ephemeral=True)
        return

    user_data = get_user_data(target_user.id)

    if user_data["balance"] < amount:
        await interaction.followup.send(f"User {target_user.display_name} only has {user_data['balance']:.2f} dollars, which is less than the requested {amount:.2f} dollars. Cannot approve.", ephemeral=True)
        return

    user_data["balance"] -= amount
    save_data(market_data)

    await interaction.followup.send(f"Successfully approved withdrawal of {amount:.2f} dollars for {target_user.display_name}. Their new balance is {user_data['balance']:.2f} dollars.", ephemeral=True)

    try:
        user_approved_embed = discord.Embed(
            title="✅ Withdrawal Approved! ✅",
            description=f"Your withdrawal request for {amount:.2f} dollars has been approved by the bot owner.",
            color=discord.Color.green()
        )
        user_approved_embed.add_field(name="New Balance", value=f"{user_data['balance']:.2f} dollars", inline=False)
        await target_user.send(embed=user_approved_embed)
    except discord.Forbidden:
        print(f"Could not send DM to user {target_user.name} about approved withdrawal. DMs might be disabled.")

@bot.tree.command(name='transfer', description='Transfer cash or Campton Coin to another user.')
@app_commands.describe(
    recipient='The user to transfer funds/coins to.',
    amount='The amount to transfer (e.g., 50.00 or 5).',
    currency_type='The type of currency to transfer.'
)
@app_commands.choices(currency_type=[
    app_commands.Choice(name='Cash', value='cash'),
    app_commands.Choice(name='Campton Coin', value='campton_coin')
])
async def transfer(interaction: discord.Interaction, recipient: discord.Member, amount: float, currency_type: app_commands.Choice[str]):
    """Transfer cash or Campton Coin to another user."""
    await interaction.response.defer(ephemeral=True)

    if amount <= 0:
        await interaction.followup.send("You must transfer a positive amount.", ephemeral=True)
        return

    if currency_type.value == 'campton_coin' and has_more_than_three_decimals(amount):
        await interaction.followup.send("You can only transfer Campton Coin with up to 3 decimal places (e.g., 0.123).", ephemeral=True)
        return

    if interaction.user.id == recipient.id:
        await interaction.followup.send("You cannot transfer to yourself.", ephemeral=True)
        return

    sender_data = get_user_data(interaction.user.id)
    recipient_data = get_user_data(recipient.id)
    currency_value = currency_type.value
    currency_name = currency_type.name

    transfer_successful = False
    feedback_message = ""
    recipient_dm_message = ""

    if currency_value == 'cash':
        if sender_data["balance"] < amount:
            feedback_message = f"Insufficient funds. You only have {sender_data['balance']:.2f} dollars."
        else:
            sender_data["balance"] -= amount
            recipient_data["balance"] += amount
            transfer_successful = True
            feedback_message = f"Successfully transferred {amount:.2f} dollars to {recipient.display_name}. Your new balance is {sender_data['balance']:.2f} dollars."
            recipient_dm_message = f"You received {amount:.2f} dollars from {interaction.user.display_name}. Your new balance is {recipient_data['balance']:.2f} dollars."
    elif currency_value == 'campton_coin':
        coin_name = "Campton Coin"
        if coin_name not in sender_data["portfolio"] or sender_data["portfolio"][coin_name] < amount:
            feedback_message = f"Insufficient Campton Coins. You only have {sender_data['portfolio'].get(coin_name, 0.0):.3f} {coin_name}(s)."
        else:
            sender_data["portfolio"][coin_name] -= amount
            recipient_data["portfolio"][coin_name] = recipient_data["portfolio"].get(coin_name, 0.0) + amount
            if sender_data["portfolio"][coin_name] <= 0.0001:
                del sender_data["portfolio"][coin_name]
            transfer_successful = True
            feedback_message = f"Successfully transferred {amount:.3f} {coin_name}(s) to {recipient.display_name}. You now have {sender_data['portfolio'].get(coin_name, 0.0):.3f} {coin_name}(s)."
            recipient_dm_message = f"You received {amount:.3f} {coin_name}(s) from {interaction.user.display_name}. You now have {recipient_data['portfolio'].get(coin_name, 0.0):.3f} {coin_name}(s)."
    else:
        feedback_message = "Invalid currency type specified."

    if transfer_successful:
        save_data(market_data)
        await interaction.followup.send(feedback_message, ephemeral=True)
        if recipient_dm_message:
            try:
                recipient_embed = discord.Embed(
                    title=f"💰 {currency_name} Transfer Received! 💰",
                    description=recipient_dm_message,
                    color=discord.Color.green()
                )
                await recipient.send(embed=recipient_embed)
            except discord.Forbidden:
                print(f"Could not send DM to {recipient.name}. DMs might be disabled.")
                await interaction.followup.send(f"Note: Could not DM {recipient.display_name} about the transfer. They might have DMs disabled.", ephemeral=True)
    else:
        await interaction.followup.send(feedback_message, ephemeral=True)

# --- NEW: Owner-only command to send the ticket button ---
@bot.tree.command(name='sendticketbutton', description='(Owner Only) Sends the "Open Ticket" button to the current channel.')
@app_commands.check(is_bot_owner_slash)
async def send_ticket_button(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    if interaction.channel.id != HELP_DESK_CHANNEL_ID:
        await interaction.followup.send(f"This command should ideally be used in the designated help desk channel (<#{HELP_DESK_CHANNEL_ID}>).", ephemeral=True)

    embed = discord.Embed(
        title="Need Help? Open a Support Ticket!",
        description="Click the button below to open a private support ticket with the staff. Please describe your issue clearly once the ticket channel is created.",
        color=discord.Color.blue()
    )
    # Send the message with the persistent view
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.followup.send("The 'Open Ticket' button has been sent to this channel.", ephemeral=True)

@send_ticket_button.error
async def send_ticket_button_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You must be the bot owner to use this command.", ephemeral=True)
    else:
        if interaction.response.is_done():
            await interaction.followup.send(f"An unexpected error occurred: {error}", ephemeral=True)
        else:
            await interaction.response.send_message(f"An unexpected error occurred: {error}", ephemeral=True)

# --- Ticket Close Command (remains a slash command) ---
@bot.tree.command(name='close', description='Close the current support ticket. (Can only be used in a ticket channel)')
async def close(interaction: discord.Interaction):
    """Close the current support ticket."""
    await interaction.response.defer(ephemeral=True)

    if not TICKET_CATEGORY_ID:
        await interaction.followup.send("Ticket system is not fully configured. Please contact the bot owner.", ephemeral=True)
        return

    # Check if the command is used in a ticket channel
    if str(interaction.channel.id) not in market_data["tickets"]:
        await interaction.followup.send("This command can only be used in a ticket channel.", ephemeral=True)
        return

    ticket_info = market_data["tickets"][str(interaction.channel.id)]
    
    # Check if user is the ticket creator or bot owner
    if interaction.user.id != ticket_info["user_id"] and interaction.user.id != bot.owner_id:
        await interaction.followup.send("You must be the ticket creator or bot owner to close this ticket.", ephemeral=True)
        return

    # Confirm closure
    confirm_view = discord.ui.View()
    confirm_button = discord.ui.Button(label="Confirm Close", style=discord.ButtonStyle.red)

    async def confirm_callback(button_interaction: discord.Interaction):
        await button_interaction.response.defer()
        if button_interaction.user.id != interaction.user.id:
            await button_interaction.followup.send("Only the person who initiated the close can confirm.", ephemeral=True)
            return

        ticket_info["status"] = "closed"
        ticket_info["closed_at"] = discord.utils.utcnow().isoformat()
        save_data(market_data)

        await interaction.channel.send("Ticket closed. This channel will be deleted shortly.")
        await button_interaction.message.delete()
        await discord.utils.sleep(5)
        await interaction.channel.delete()

    confirm_button.callback = confirm_callback
    confirm_view.add_item(confirm_button)

    await interaction.followup.send("Are you sure you want to close this ticket?", view=confirm_view, ephemeral=True)


# Run the bot
bot.run(TOKEN)
