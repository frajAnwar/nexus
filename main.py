# main.py - Bot entry point
import discord
from discord.ext import commands, tasks
from discord import app_commands
import database
import random
import os
import configparser
from datetime import datetime
from utils import views, helpers
from flask import Flask
from threading import Thread

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Get constants from config
ADMIN_ROLE = config['GAME']['admin_role']
PLAYER_ROLE = config['GAME']['player_role']
CHANNEL_REGISTRATION = config['GAME']['registration_channel']
CHANNEL_LEVELING = config['GAME']['leveling_channel']
CHANNEL_DUNGEON = config['GAME']['dungeon_channel']
CHANNEL_MARKETPLACE = config['GAME']['marketplace_channel']
CHANNEL_ADMIN = config['GAME']['admin_channel']
BOT_TOKEN = os.getenv('BOT_TOKEN') or config['GAME']['token']
BASE_XP = int(config['GAME']['base_xp'])
XP_MULTIPLIER = float(config['GAME']['xp_multiplier'])
LEVEL_COIN_REWARD = int(config['GAME']['level_coin_reward'])
ITEM_DROP_CHANCE = float(config['GAME']['item_drop_chance'])
MESSAGE_XP_CHANCE = float(config['GAME']['message_xp_chance'])
MESSAGE_XP_MIN = int(config['GAME']['message_xp_min'])
MESSAGE_XP_MAX = int(config['GAME']['message_xp_max'])
MAX_STAMINA = int(config['GAME']['max_stamina'])
CURRENCY_ICON = config['GAME']['currency_icon']

# Initialize bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Keep-alive server
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()
keep_alive()

# Background tasks
@tasks.loop(minutes=1)
async def stamina_regeneration():
    database.regenerate_stamina()

@tasks.loop(minutes=1)
async def dungeon_completion():
    database.complete_dungeons(bot)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    # Sync commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Command syncing error: {e}")
    
    # Start background tasks
    stamina_regeneration.start()
    dungeon_completion.start()
    
    # Create interface messages
    for guild in bot.guilds:
        await helpers.create_interface_messages(bot, guild, config)

@bot.event
async def on_message(message):
    try:
        if message.author.bot:
            return

        # Only process messages in game channels
        game_channels = [CHANNEL_LEVELING, CHANNEL_DUNGEON, CHANNEL_MARKETPLACE]
        if message.channel.name not in game_channels:
            return

        # Create player if not exists
        database.create_player(message.author.id, message.author.name)
        
        # Chance to gain XP
        if random.random() < MESSAGE_XP_CHANCE:
            xp_gain = random.randint(MESSAGE_XP_MIN, MESSAGE_XP_MAX)
            database.add_xp(message.author.id, xp_gain)
            
            # Chance to find an item
            if random.random() < ITEM_DROP_CHANCE:
                item_id = database.get_random_item()
                if item_id:
                    database.add_item_to_inventory(message.author.id, item_id)
                    item = database.get_item(item_id)
                    await message.channel.send(
                        f"{message.author.mention} found a {helpers.get_rarity_emoji(item['rarity'])} **{item['name']}** while exploring!"
                    )
    except Exception as e:
        print(f"on_message error: {e}")
    
    await bot.process_commands(message)

# Command groups
@bot.tree.command(name="dashboard", description="Access your RPG dashboard")
async def dashboard(interaction: discord.Interaction):
    """Show player dashboard"""
    embed = discord.Embed(
        title="🎮 Pixel RPG Dashboard",
        description="Navigate your adventure with the buttons below",
        color=0x3498db
    )
    embed.set_thumbnail(url=helpers.get_asset("logo"))
    view = views.DashboardView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="register", description="Register as an adventurer")
async def register(interaction: discord.Interaction):
    """Register a new player"""
    database.create_player(interaction.user.id, interaction.user.name)
    
    # Add starter items
    database.add_item_to_inventory(interaction.user.id, 1)  # Wooden Sword
    database.add_item_to_inventory(interaction.user.id, 3)  # Minor Health Potion
    
    # Assign player role
    guild = interaction.guild
    player_role = discord.utils.get(guild.roles, name=PLAYER_ROLE)
    if not player_role:
        player_role = await guild.create_role(name=PLAYER_ROLE, color=discord.Color.blue())
    
    await interaction.user.add_roles(player_role)
    
    embed = discord.Embed(
        title="🎉 Welcome Adventurer!",
        description="You've been registered for your RPG journey",
        color=discord.Color.green()
    )
    embed.add_field(name="Starter Items", value="• Wooden Sword\n• Minor Health Potion", inline=False)
    embed.add_field(name="Next Steps", value=f"Visit <#{discord.utils.get(guild.channels, name=CHANNEL_LEVELING).id}> to begin leveling up", inline=False)
    
    await interaction.response.send_message(embed=embed)

# Admin commands
@bot.tree.command(name="admin", description="Admin dashboard")
@app_commands.checks.has_role(ADMIN_ROLE)
async def admin_dashboard(interaction: discord.Interaction):
    """Admin dashboard"""
    embed = discord.Embed(
        title="🛠️ RPG Admin Dashboard",
        description="Manage the RPG system",
        color=0x3498db
    )
    embed.set_thumbnail(url=helpers.get_asset("logo"))
    view = views.AdminDashboardView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="add_item", description="Add a new item to the game")
@app_commands.checks.has_role(ADMIN_ROLE)
async def admin_add_item(
    interaction: discord.Interaction,
    name: str,
    description: str,
    value: int,
    rarity: str,
    image_url: str,
    drop_rate: float,
    min_level: int
):
    """Add a new item to the game"""
    item_id = database.create_item(name, description, value, image_url, rarity, drop_rate, min_level)
    embed = discord.Embed(
        title="✅ Item Added",
        description=f"New item created with ID: {item_id}",
        color=0x00ff00
    )
    embed.add_field(name="Name", value=name)
    embed.add_field(name="Rarity", value=rarity)
    embed.set_thumbnail(url=image_url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Run the bot
if __name__ == "__main__":
    database.initialize_database()
    bot.run(BOT_TOKEN)