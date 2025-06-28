# main.py - Entry point for the bot
import discord
from discord.ext import commands, tasks
from discord import app_commands
import database
import random
import asyncio
import os
import configparser
from datetime import datetime, timedelta
from typing import List, Optional
from utils.views import DashboardView, MarketplaceView, DungeonView, AdminDashboardView
from utils.helpers import is_rpg_admin, calculate_level, get_level_xp, get_level_tier

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Constants from config
ADMIN_ROLE = config['GAME']['admin_role']
PLAYER_ROLE = config['GAME']['player_role']
CHANNEL_REGISTRATION = config['GAME']['registration_channel']
CHANNEL_LEVELING = config['GAME']['leveling_channel']
CHANNEL_DUNGEON = config['GAME']['dungeon_channel']
CHANNEL_MARKETPLACE = config['GAME']['marketplace_channel']
CHANNEL_ADMIN = config['GAME']['admin_channel']
LOG_CHANNEL_ID = int(config['GAME']['log_channel'])
BOT_TOKEN = config['GAME']['token']
BASE_XP = int(config['GAME']['base_xp'])
XP_MULTIPLIER = float(config['GAME']['xp_multiplier'])
LEVEL_COIN_REWARD = int(config['GAME']['level_coin_reward'])
ITEM_DROP_CHANCE = float(config['GAME']['item_drop_chance'])
MESSAGE_XP_CHANCE = float(config['GAME']['message_xp_chance'])
MESSAGE_XP_MIN = int(config['GAME']['message_xp_min'])
MESSAGE_XP_MAX = int(config['GAME']['message_xp_max'])
MAX_STAMINA = int(config['GAME']['max_stamina'])
CURRENCY_ICON = config['GAME']['currency_icon']
CURRENCY_NAME = config['GAME']['currency_name']

# Pixel art assets from config
PIXEL_ASSETS = {
    "logo": config['ASSETS']['logo'],
    "hero": config['ASSETS']['hero'],
    "dungeon": config['ASSETS']['dungeon'],
    "sword": config['ASSETS']['sword'],
    "shield": config['ASSETS']['shield'],
    "potion": config['ASSETS']['potion'],
    "chest": config['ASSETS']['chest'],
    "dragon": config['ASSETS']['dragon'],
    "coin": config['ASSETS']['coin'],
    "xp": config['ASSETS']['xp'],
    "shop": config['ASSETS']['shop'],
    "mystery": config['ASSETS']['mystery']
}

# Rarity data with colors and emojis
RARITY_DATA = {
    "common": {"color": 0x808080, "emoji": "⚪", "weight": 60},
    "uncommon": {"color": 0x00ff00, "emoji": "🟢", "weight": 25},
    "rare": {"color": 0x0080ff, "emoji": "🔵", "weight": 10},
    "epic": {"color": 0x8000ff, "emoji": "🟣", "weight": 4},
    "legendary": {"color": 0xffa500, "emoji": "🟠", "weight": 1}
}

# Tier colors for profile display
TIER_COLORS = {
    "beginner": 0x808080,
    "apprentice": 0x00ff00,
    "journeyman": 0x0080ff,
    "adept": 0x8000ff,
    "expert": 0xffd700,
    "master": 0xffa500,
    "grandmaster": 0xff0000
}

# Background tasks
@tasks.loop(minutes=1)
async def stamina_regeneration():
    database.regenerate_stamina()

@tasks.loop(minutes=1)
async def dungeon_completion():
    database.complete_dungeons(bot)

@tasks.loop(minutes=1)
async def shop_restock():
    database.restock_shop()

# Bot events
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
    shop_restock.start()
    
    # Create interface messages
    for guild in bot.guilds:
        await create_interface_messages(guild)

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
                        f"{message.author.mention} found a {RARITY_DATA[item['rarity']]['emoji']} **{item['name']}** while exploring!"
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
    embed.set_thumbnail(url=PIXEL_ASSETS["logo"])
    view = DashboardView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="register", description="Register as an adventurer")
@app_commands.checks.has_channel_named(CHANNEL_REGISTRATION)
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
    embed.set_thumbnail(url=PIXEL_ASSETS["logo"])
    view = AdminDashboardView()
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

# Helper functions
async def create_interface_messages(guild):
    """Create interface messages in each channel"""
    # Registration channel
    reg_channel = discord.utils.get(guild.channels, name=CHANNEL_REGISTRATION)
    if reg_channel:
        await reg_channel.purge()
        embed = discord.Embed(
            title="🌟 Welcome to Pixel RPG!",
            description="Begin your adventure by registering below",
            color=0x3498db
        )
        embed.set_thumbnail(url=PIXEL_ASSETS["hero"])
        embed.add_field(name="How to Start", value="Use the `/register` command to create your character", inline=False)
        embed.add_field(name="Features", value="• Character progression\n• Dungeon exploration\n• Player marketplace", inline=False)
        await reg_channel.send(embed=embed)
    
    # Leveling channel
    level_channel = discord.utils.get(guild.channels, name=CHANNEL_LEVELING)
    if level_channel:
        await level_channel.purge()
        embed = discord.Embed(
            title="📈 Leveling System",
            description="Gain XP and level up your character",
            color=0x3498db
        )
        embed.set_thumbnail(url=PIXEL_ASSETS["xp"])
        embed.add_field(name="How it Works", value="• Send messages to gain XP\n• Complete dungeons for rewards\n• Higher levels unlock better content", inline=False)
        await level_channel.send(embed=embed)
    
    # Dungeon channel
    dungeon_channel = discord.utils.get(guild.channels, name=CHANNEL_DUNGEON)
    if dungeon_channel:
        await dungeon_channel.purge()
        embed = discord.Embed(
            title="🏰 Dungeon Expeditions",
            description="Embark on dangerous adventures to earn rewards",
            color=0x8B4513
        )
        embed.set_thumbnail(url=PIXEL_ASSETS["dungeon"])
        embed.add_field(name="How it Works", value="• Use stamina to start expeditions\n• Higher risk = greater rewards\n• Discover rare items", inline=False)
        await dungeon_channel.send(embed=embed)
    
    # Marketplace channel
    market_channel = discord.utils.get(guild.channels, name=CHANNEL_MARKETPLACE)
    if market_channel:
        await market_channel.purge()
        embed = discord.Embed(
            title="🛒 RPG Marketplace",
            description="Buy, sell, and trade items with other players",
            color=0x3498db
        )
        embed.set_thumbnail(url=PIXEL_ASSETS["shop"])
        embed.add_field(name="Sections", value="• Global Shop\n• Player Marketplace\n• Mystery Boxes", inline=False)
        view = MarketplaceView()
        await market_channel.send(embed=embed, view=view)
    
    # Admin channel
    admin_channel = discord.utils.get(guild.channels, name=CHANNEL_ADMIN)
    if admin_channel:
        await admin_channel.purge()
        embed = discord.Embed(
            title="🛠️ RPG Admin Dashboard",
            description="Manage all aspects of the RPG system",
            color=0x3498db
        )
        embed.set_thumbnail(url=PIXEL_ASSETS["logo"])
        embed.add_field(name="Sections", value="• Items Database\n• Player Management\n• Economy Controls", inline=False)
        view = AdminDashboardView()
        await admin_channel.send(embed=embed, view=view)

if __name__ == "__main__":
    database.initialize_database()
    bot.run(BOT_TOKEN)