# database.py - Database operations
import sqlite3
import threading
import json
import random
import math
from datetime import datetime, timedelta

# Thread-safe database connection
db_lock = threading.Lock()

class Database:
    def __enter__(self):
        db_lock.acquire()
        self.conn = sqlite3.connect('rpg.db', check_same_thread=False)
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.conn.commit()
        finally:
            self.conn.close()
            db_lock.release()

def initialize_database():
    with Database() as c:
        # Players table
        c.execute('''CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            coins INTEGER DEFAULT 0,
            stamina INTEGER DEFAULT 5,
            max_stamina INTEGER DEFAULT 5,
            last_stamina_time DATETIME,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            tier TEXT DEFAULT 'beginner',
            current_dungeon_end DATETIME,
            current_dungeon_stamina INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Items table
        c.execute('''CREATE TABLE IF NOT EXISTS items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            value INTEGER,
            image_url TEXT,
            rarity TEXT,
            drop_rate FLOAT DEFAULT 0.1,
            min_level INTEGER DEFAULT 1
        )''')
        
        # Inventory table
        c.execute('''CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, item_id)
        )''')
        
        # Dungeons table
        c.execute('''CREATE TABLE IF NOT EXISTS dungeons (
            dungeon_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tier INTEGER NOT NULL,
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            stamina_used INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            rewards TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Marketplace table
        c.execute('''CREATE TABLE IF NOT EXISTS marketplace (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Global shop table
        c.execute('''CREATE TABLE IF NOT EXISTS global_shop (
            item_id INTEGER PRIMARY KEY,
            price INTEGER,
            stock INTEGER DEFAULT -1,
            FOREIGN KEY(item_id) REFERENCES items(item_id)
        )''')
        
        # Insert default items
        default_items = [
            ("Wooden Sword", "Basic training weapon", 10, "https://i.imgur.com/3sT7VQj.png", "common", 0.3, 1),
            ("Leather Armor", "Simple protective gear", 15, "https://i.imgur.com/4bLQ9Yf.png", "common", 0.3, 1),
            ("Minor Health Potion", "Restores 20 HP", 15, "https://i.imgur.com/2vBq8Qk.png", "common", 0.4, 1),
            ("Iron Sword", "Reliable combat weapon", 50, "https://i.imgur.com/3sT7VQj.png", "uncommon", 0.15, 5),
            ("Chainmail Armor", "Solid metal protection", 75, "https://i.imgur.com/4bLQ9Yf.png", "uncommon", 0.15, 5),
            ("Health Potion", "Restores 50 HP", 30, "https://i.imgur.com/2vBq8Qk.png", "uncommon", 0.2, 5),
            ("Steel Longsword", "Well-balanced weapon", 120, "https://i.imgur.com/3sT7VQj.png", "rare", 0.08, 10),
            ("Scale Armor", "Flexible protection", 150, "https://i.imgur.com/4bLQ9Yf.png", "rare", 0.08, 10),
            ("Mithril Sword", "Light yet strong", 300, "https://i.imgur.com/3sT7VQj.png", "epic", 0.03, 15),
            ("Dragonbone Sword", "Legendary weapon", 500, "https://i.imgur.com/3sT7VQj.png", "legendary", 0.01, 20),
            ("Stamina Potion", "Restores 1 stamina", 50, "https://i.imgur.com/2vBq8Qk.png", "rare", 0.1, 5),
            ("Dungeon Key", "Unlocks special dungeons", 100, "https://i.imgur.com/9zGQk2c.png", "epic", 0.05, 10)
        ]
        
        c.executemany('''INSERT OR IGNORE INTO items (name, description, value, image_url, rarity, drop_rate, min_level)
                      VALUES (?, ?, ?, ?, ?, ?, ?)''', default_items)
        
        # Add items to global shop
        shop_items = [
            ("Stamina Potion", 50, 100),
            ("Health Potion", 30, 200),
            ("Dungeon Key", 150, 50)
        ]
        
        for name, price, stock in shop_items:
            c.execute("SELECT item_id FROM items WHERE name = ?", (name,))
            item_id = c.fetchone()
            if item_id:
                c.execute('''INSERT OR IGNORE INTO global_shop (item_id, price, stock)
                          VALUES (?, ?, ?)''', (item_id[0], price, stock))

# Player operations
def create_player(user_id, username):
    with Database() as c:
        c.execute("INSERT OR IGNORE INTO players (user_id, username) VALUES (?, ?)", (user_id, username))

def get_player(user_id):
    with Database() as c:
        c.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        return c.fetchone()

def add_xp(user_id, amount):
    with Database() as c:
        player = get_player(user_id)
        if not player:
            return
            
        current_xp = player[2] + amount
        current_level = player[3]
        new_level = calculate_level(current_xp)
        levels_gained = new_level - current_level
        
        # Update player
        new_tier = get_level_tier(new_level)
        c.execute(
            "UPDATE players SET xp = ?, level = ?, tier = ? WHERE user_id = ?",
            (current_xp, new_level, new_tier, user_id)
        )
        
        # Add level up rewards
        if levels_gained > 0:
            coin_reward = levels_gained * LEVEL_COIN_REWARD
            c.execute(
                "UPDATE players SET coins = coins + ? WHERE user_id = ?",
                (coin_reward, user_id)
            )
            return new_level, coin_reward
        
        return new_level, 0

def add_coins(user_id, amount):
    with Database() as c:
        c.execute("UPDATE players SET coins = coins + ? WHERE user_id = ?", (amount, user_id))

def regenerate_stamina():
    current_time = datetime.now()
    with Database() as c:
        c.execute("SELECT user_id, stamina, max_stamina, last_stamina_time FROM players")
        players = c.fetchall()
        
        for player in players:
            user_id, stamina, max_stamina, last_stamina_time = player
            if stamina >= max_stamina:
                continue
                
            if not last_stamina_time:
                continue
                
            last_time = datetime.strptime(last_stamina_time, '%Y-%m-%d %H:%M:%S.%f')
            minutes_passed = (current_time - last_time).total_seconds() / 60
            
            # Calculate stamina to add (1 per 30 minutes)
            stamina_to_add = min(int(minutes_passed // 30), max_stamina - stamina)
            
            if stamina_to_add > 0:
                new_stamina = stamina + stamina_to_add
                new_last_time = last_time + timedelta(minutes=30 * stamina_to_add)
                c.execute(
                    "UPDATE players SET stamina = ?, last_stamina_time = ? WHERE user_id = ?",
                    (new_stamina, new_last_time.strftime('%Y-%m-%d %H:%M:%S.%f'), user_id)
                )

# Item operations
def create_item(name, description, value, image_url, rarity, drop_rate, min_level):
    with Database() as c:
        c.execute('''INSERT INTO items (name, description, value, image_url, rarity, drop_rate, min_level)
                  VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                  (name, description, value, image_url, rarity, drop_rate, min_level))
        return c.lastrowid

def get_item(item_id):
    with Database() as c:
        c.execute("SELECT * FROM items WHERE item_id = ?", (item_id,))
        return c.fetchone()

def get_random_item():
    with Database() as c:
        c.execute("SELECT item_id FROM items ORDER BY RANDOM() LIMIT 1")
        result = c.fetchone()
        return result[0] if result else None

def add_item_to_inventory(user_id, item_id, quantity=1):
    with Database() as c:
        c.execute('''INSERT OR IGNORE INTO inventory (user_id, item_id, quantity)
                  VALUES (?, ?, ?)''', (user_id, item_id, quantity))
        c.execute('''UPDATE inventory SET quantity = quantity + ?
                  WHERE user_id = ? AND item_id = ?''', (quantity, user_id, item_id))

def get_player_inventory(user_id):
    with Database() as c:
        c.execute('''SELECT items.item_id, items.name, items.description, items.rarity, 
                  items.image_url, inventory.quantity, items.value
                  FROM inventory 
                  JOIN items ON inventory.item_id = items.item_id 
                  WHERE user_id = ?''', (user_id,))
        return c.fetchall()

# Dungeon operations
def start_dungeon(user_id, stamina_used, tier):
    with Database() as c:
        start_time = datetime.now()
        duration = timedelta(hours=tier)
        end_time = start_time + duration
        
        # Create dungeon
        c.execute('''INSERT INTO dungeons (user_id, tier, start_time, end_time, stamina_used)
                  VALUES (?, ?, ?, ?, ?)''', 
                  (user_id, tier, start_time, end_time, stamina_used))
        
        # Deduct stamina
        c.execute("UPDATE players SET stamina = stamina - ?, current_dungeon_end = ?, current_dungeon_stamina = ? WHERE user_id = ?", 
                 (stamina_used, end_time, stamina_used, user_id))

def complete_dungeons(bot):
    current_time = datetime.now()
    with Database() as c:
        c.execute('''SELECT d.dungeon_id, d.user_id, d.stamina_used, d.tier, d.end_time, 
                  p.stamina, p.max_stamina 
                  FROM dungeons d
                  JOIN players p ON d.user_id = p.user_id
                  WHERE d.status = 'active' AND d.end_time <= ?''', (current_time,))
        dungeons = c.fetchall()
        
        for dungeon in dungeons:
            dungeon_id, user_id, stamina_used, tier, end_time, stamina, max_stamina = dungeon
            
            # Determine success
            success = stamina_used >= tier
            status = "success" if success else "failed"
            
            # Calculate rewards
            rewards = {"xp": 0, "coins": 0, "items": []}
            if success:
                base_xp = tier * 50 * stamina_used
                base_coins = tier * 25 * stamina_used
                rewards["xp"] = base_xp
                rewards["coins"] = base_coins
                
                # Add random items
                item_count = max(1, tier // 2)
                for _ in range(item_count):
                    item_id = get_random_item()
                    if item_id:
                        rewards["items"].append(item_id)
                        add_item_to_inventory(user_id, item_id)
            else:
                # Partial rewards
                rewards["xp"] = tier * 25 * stamina_used * 0.5
                rewards["coins"] = tier * 10 * stamina_used
            
            # Update player rewards
            add_xp(user_id, rewards["xp"])
            add_coins(user_id, rewards["coins"])
            
            # Update dungeon status
            c.execute("UPDATE dungeons SET status = ?, rewards = ? WHERE dungeon_id = ?", 
                     (status, json.dumps(rewards), dungeon_id))
            
            # Clear active dungeon
            c.execute("UPDATE players SET current_dungeon_end = NULL, current_dungeon_stamina = NULL WHERE user_id = ?", 
                     (user_id,))
            
            # Return stamina if failed
            if not success:
                c.execute("UPDATE players SET stamina = LEAST(stamina + ?, ?) WHERE user_id = ?", 
                         (stamina_used // 2, max_stamina, user_id))
            
            # Notify player
            try:
                user = bot.get_user(user_id)
                if user:
                    embed = discord.Embed(
                        title=f"🏰 Dungeon {'Successful!' if success else 'Failed'}",
                        color=0x2ecc71 if success else 0xe74c3c
                    )
                    embed.set_thumbnail(url="https://i.imgur.com/7z9sKXb.png")
                    embed.add_field(name="XP Earned", value=rewards["xp"], inline=True)
                    embed.add_field(name="Coins Earned", value=f"{CURRENCY_ICON}{rewards['coins']}", inline=True)
                    
                    if rewards["items"]:
                        items_list = "\n".join([get_item(item)['name'] for item in rewards["items"]])
                        embed.add_field(name="Items Found", value=items_list, inline=False)
                    
                    await user.send(embed=embed)
            except:
                pass

# Utility functions
def calculate_level(xp):
    BASE_XP = 100
    XP_MULTIPLIER = 1.5
    return max(1, int(math.log(max(1, xp / BASE_XP), XP_MULTIPLIER) + 1)

def get_level_tier(level):
    if level < 5: return "beginner"
    elif level < 10: return "apprentice"
    elif level < 20: return "journeyman"
    elif level < 30: return "adept"
    elif level < 40: return "expert"
    elif level < 50: return "master"
    else: return "grandmaster"