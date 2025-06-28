# utils/helpers.py - Utility functions
import discord
import configparser

async def create_interface_messages(bot, guild, config):
    """Create interface messages in each channel"""
    # Constants from config
    CHANNEL_REGISTRATION = config['GAME']['registration_channel']
    CHANNEL_LEVELING = config['GAME']['leveling_channel']
    CHANNEL_DUNGEON = config['GAME']['dungeon_channel']
    CHANNEL_MARKETPLACE = config['GAME']['marketplace_channel']
    CHANNEL_ADMIN = config['GAME']['admin_channel']
    PIXEL_ASSETS = {
        "logo": config['ASSETS']['logo'],
        "hero": config['ASSETS']['hero'],
        "dungeon": config['ASSETS']['dungeon'],
        "xp": config['ASSETS']['xp'],
        "shop": config['ASSETS']['shop']
    }

    # Registration channel
    reg_channel = discord.utils.get(guild.text_channels, name=CHANNEL_REGISTRATION)
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
    level_channel = discord.utils.get(guild.text_channels, name=CHANNEL_LEVELING)
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
    dungeon_channel = discord.utils.get(guild.text_channels, name=CHANNEL_DUNGEON)
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
    market_channel = discord.utils.get(guild.text_channels, name=CHANNEL_MARKETPLACE)
    if market_channel:
        await market_channel.purge()
        embed = discord.Embed(
            title="🛒 RPG Marketplace",
            description="Buy, sell, and trade items with other players",
            color=0x3498db
        )
        embed.set_thumbnail(url=PIXEL_ASSETS["shop"])
        embed.add_field(name="Sections", value="• Global Shop\n• Player Marketplace\n• Mystery Boxes", inline=False)
        view = views.MarketplaceView()
        await market_channel.send(embed=embed, view=view)
    
    # Admin channel
    admin_channel = discord.utils.get(guild.text_channels, name=CHANNEL_ADMIN)
    if admin_channel:
        await admin_channel.purge()
        embed = discord.Embed(
            title="🛠️ RPG Admin Dashboard",
            description="Manage all aspects of the RPG system",
            color=0x3498db
        )
        embed.set_thumbnail(url=PIXEL_ASSETS["logo"])
        embed.add_field(name="Sections", value="• Items Database\n• Player Management\n• Economy Controls", inline=False)
        view = views.AdminDashboardView()
        await admin_channel.send(embed=embed, view=view)

def get_rarity_emoji(rarity):
    """Get emoji for item rarity"""
    rarity_emojis = {
        "common": "⚪",
        "uncommon": "🟢",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟠"
    }
    return rarity_emojis.get(rarity, "⚪")

def get_asset(asset_name):
    """Get URL for a pixel art asset"""
    assets = {
        "logo": "https://i.imgur.com/8cJQ4ZR.png",
        "hero": "https://i.imgur.com/5kI1q6P.png",
        "dungeon": "https://i.imgur.com/7z9sKXb.png",
        "sword": "https://i.imgur.com/3sT7VQj.png",
        "shield": "https://i.imgur.com/4bLQ9Yf.png",
        "potion": "https://i.imgur.com/2vBq8Qk.png",
        "chest": "https://i.imgur.com/9zGQk2c.png",
        "dragon": "https://i.imgur.com/5bJtGgR.png",
        "coin": "https://i.imgur.com/1vZ8Q9j.png",
        "xp": "https://i.imgur.com/3qJZQY7.png",
        "shop": "https://i.imgur.com/7QZ8J9c.png",
        "mystery": "https://i.imgur.com/5XZ9J7c.png"
    }
    return assets.get(asset_name, "")