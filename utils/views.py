# utils/views.py - Interactive UI components
import discord
from discord.ui import Button, View, Select
import database
from datetime import datetime, timedelta

class DashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Dashboard buttons
        self.add_item(Button(label="👤 Profile", style=discord.ButtonStyle.primary, custom_id="profile"))
        self.add_item(Button(label="🎒 Inventory", style=discord.ButtonStyle.primary, custom_id="inventory"))
        self.add_item(Button(label="🏰 Dungeons", style=discord.ButtonStyle.success, custom_id="dungeons"))
        self.add_item(Button(label="🛒 Marketplace", style=discord.ButtonStyle.primary, custom_id="marketplace"))
        self.add_item(Button(label="⚔️ Arena", style=discord.ButtonStyle.danger, custom_id="arena"))
        self.add_item(Button(label="🛠️ Admin", style=discord.ButtonStyle.secondary, custom_id="admin_dash", row=1))

class MarketplaceView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Marketplace buttons
        self.add_item(Button(label="🛒 Global Shop", style=discord.ButtonStyle.primary, custom_id="global_shop"))
        self.add_item(Button(label="📜 Player Listings", style=discord.ButtonStyle.secondary, custom_id="player_market"))
        self.add_item(Button(label="🎁 Mystery Boxes", style=discord.ButtonStyle.success, custom_id="mystery_boxes"))
        self.add_item(Button(label="💼 My Listings", style=discord.ButtonStyle.secondary, custom_id="my_listings"))

class DungeonView(View):
    def __init__(self, user_id, has_active, max_stamina=5):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.has_active = has_active
        
        # Add stamina buttons
        for stamina in range(1, min(6, max_stamina + 1)):
            button = Button(
                label=f"Use {stamina} Stamina",
                style=discord.ButtonStyle.primary,
                disabled=has_active
            )
            button.callback = lambda i, s=stamina: self.start_dungeon(i, s)
            self.add_item(button)
        
        # Add stamina potion button
        potion_button = Button(
            label="Use Stamina Potion",
            style=discord.ButtonStyle.success,
            emoji="🧪",
            disabled=has_active
        )
        potion_button.callback = self.use_potion
        self.add_item(potion_button)
    
    async def start_dungeon(self, interaction, stamina):
        player = database.get_player(self.user_id)
        if not player:
            return
        
        if player['stamina'] < stamina:
            await interaction.response.send_message("❌ Not enough stamina!", ephemeral=True)
            return
        
        # Random dungeon tier (1-5)
        tier = random.randint(1, 5)
        database.start_dungeon(self.user_id, stamina, tier)
        
        # Send confirmation
        embed = discord.Embed(
            title="🏰 Expedition Launched!",
            description=f"You've started a dungeon expedition using {stamina} stamina",
            color=0x2ecc71
        )
        embed.set_thumbnail(url="https://i.imgur.com/7z9sKXb.png")
        embed.add_field(name="Dungeon Tier", value=f"Tier {tier}", inline=True)
        embed.add_field(name="Duration", value=f"{tier} hours", inline=True)
        embed.add_field(name="Success Condition", value=f"Stamina used ({stamina}) >= Dungeon tier ({tier})", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def use_potion(self, interaction):
        # Check if player has stamina potion
        player = database.get_player(self.user_id)
        if not player:
            return
        
        # Check stamina potion in inventory
        with database.Database() as c:
            c.execute('''SELECT inventory.quantity 
                      FROM inventory 
                      JOIN items ON inventory.item_id = items.item_id 
                      WHERE user_id = ? AND items.name = 'Stamina Potion' ''', 
                      (self.user_id,))
            potion = c.fetchone()
            
            if not potion or potion[0] < 1:
                await interaction.response.send_message("❌ You don't have any Stamina Potions!", ephemeral=True)
                return
            
            # Update stamina
            new_stamina = min(player['stamina'] + 1, player['max_stamina'])
            c.execute("UPDATE players SET stamina = ? WHERE user_id = ?", 
                     (new_stamina, self.user_id))
            
            # Remove potion
            c.execute('''UPDATE inventory SET quantity = quantity - 1 
                      WHERE user_id = ? AND item_id = (
                          SELECT item_id FROM items WHERE name = 'Stamina Potion'
                      )''', (self.user_id,))
        
        # Send confirmation
        embed = discord.Embed(
            title="🧪 Stamina Restored!",
            description="You used a Stamina Potion and restored 1 stamina point",
            color=0x2ecc71
        )
        embed.add_field(name="Current Stamina", value=f"{new_stamina}/{player['max_stamina']}", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AdminDashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Admin dashboard buttons
        self.add_item(Button(label="📦 Items Database", style=discord.ButtonStyle.primary, custom_id="admin_items"))
        self.add_item(Button(label="👥 Player Management", style=discord.ButtonStyle.primary, custom_id="admin_players"))
        self.add_item(Button(label="🛒 Shop Controls", style=discord.ButtonStyle.primary, custom_id="admin_shop"))
        self.add_item(Button(label="🏰 Dungeon Settings", style=discord.ButtonStyle.success, custom_id="admin_dungeons"))