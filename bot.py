import discord
from discord.ext import commands
from discord import app_commands
import json, os, random, asyncio, traceback
from datetime import datetime, timedelta
from pathlib import Path
import sys
from flask import Flask
from threading import Thread

# --- WEB SERVER FOR RENDER ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is alive! ✅"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
Thread(target=run_web, daemon=True).start()
# -----------------------------

# --- CONFIG ---
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
if not TOKEN:
    print("❌ לא נמצא טוקן! הגדר Secret בשם DISCORD_TOKEN")
    if Path(".env").exists():
        from dotenv import load_dotenv
        load_dotenv()
        TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = "casino_data.json"
START_BALANCE = 1000
DAILY_AMOUNT = 500

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        if os.path.exists(DATA_FILE):
            os.rename(DATA_FILE, f"{DATA_FILE}.bak.{int(datetime.now().timestamp())}")
        return {}

def save_data(data):
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, DATA_FILE)

def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": START_BALANCE, "last_daily": None}
        save_data(data)
    return data[uid], data

def update_balance(user_id, amount):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"balance": START_BALANCE, "last_daily": None}
    data[uid]["balance"] = int(data[uid]["balance"] + amount)
    if data[uid]["balance"] < 0:
        data[uid]["balance"] = 0
    save_data(data)
    return data[uid]["balance"]

def card_value(card):
    rank = card[:-1]
    if rank in ["J","Q","K"]: return 10
    if rank == "A": return 11
    return int(rank)

def hand_value(hand):
    val, aces = 0, 0
    for c in hand:
        v = card_value(c); val+=v
        if c.startswith("A"): aces+=1
    while val>21 and aces:
        val-=10; aces-=1
    return val

class BlackjackView(discord.ui.View):
    def __init__(self, user_id, bet):
        super().__init__(timeout=120)
        self.user_id=user_id; self.bet=bet
        ranks=["A","2","3","4","5","6","7","8","9","10","J","Q","K"]
        suits=["♠","♥","♦","♣"]
        self.deck=[r+s for r in ranks for s in suits]
        random.shuffle(self.deck)
        self.player=[self.deck.pop(), self.deck.pop()]
        self.dealer=[self.deck.pop(), self.deck.pop()]
        self.finished=False

    async def on_timeout(self):
        if not self.finished:
            self.finished=True
            self.clear_items()

    @discord.ui.button(label="Hit 🃏", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id!= self.user_id:
            await interaction.response.send_message("זה לא המשחק שלך!", ephemeral=True); return
        if self.finished: return
        self.player.append(self.deck.pop())
        pv=hand_value(self.player)
        if pv>=21:
            self.finished=True; self.clear_items()
            dv=hand_value(self.dealer)
            while dv<17:
                self.dealer.append(self.deck.pop()); dv=hand_value(self.dealer)
            embed=discord.Embed(title="Blackjack - סיום", color=0xe74c3c if pv>21 else 0x2ecc71)
            embed.add_field(name=f"היד שלך ({pv})", value=", ".join(self.player), inline=False)
            embed.add_field(name=f"דילר ({dv})", value=", ".join(self.dealer), inline=False)
            if pv>21:
                embed.add_field(name="תוצאה", value=f"BUST! הפסדת {self.bet}$", inline=False)
            elif dv>21 or pv>dv:
                win=int(self.bet*1.5) if pv==21 and len(self.player)==2 else self.bet
                update_balance(self.user_id, self.bet+win)
                embed.add_field(name="תוצאה", value=f"ניצחת! +{win}$ רווח!", inline=False)
            elif pv==dv:
                update_balance(self.user_id, self.bet)
                embed.add_field(name="תוצאה", value="תיקו! כסף חוזר.", inline=False)
            else:
                embed.add_field(name="תוצאה", value=f"הפסדת {self.bet}$", inline=False)
            embed.set_footer(text=f"יתרה: {load_data().get(str(self.user_id), {}).get('balance
