import discord
from discord.ext import commands
from discord import app_commands
import os, json, random
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is online!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_ID = os.getenv("ADMIN_ID") # Put your Discord ID here in Render Environment

def load_data():
    if not os.path.exists("data.json"):
        return {}
    try:
        with open("data.json","r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(d):
    with open("data.json","w",encoding="utf-8") as f:
        json.dump(d,f,indent=2)

def get_user_data(uid):
    data=load_data()
    s=str(uid)
    if s not in data:
        data[s]={"balance":1000}
        save_data(data)
    return data[s]

def is_admin(interaction: discord.Interaction):
    # ONLY YOU are admin - locked to ADMIN_ID
    if not ADMIN_ID:
        return False
    return str(interaction.user.id) == str(ADMIN_ID)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

# --- USER COMMANDS ---
@bot.tree.command(name="balance", description="Check your balance")
async def balance(interaction: discord.Interaction):
    d=get_user_data(interaction.user.id)
    await interaction.response.send_message(f"You have {d['balance']} coins")

@bot.tree.command(name="daily", description="Claim daily 500 coins")
async def daily(interaction: discord.Interaction):
    data=load_data()
    uid=str(interaction.user.id)
    ud=get_user_data(interaction.user.id)
    ud["balance"]+=500
    data[uid]=ud
    save_data(data)
    await interaction.response.send_message(f"You claimed 500! Balance: {ud['balance']}")

@bot.tree.command(name="coinflip", description="Coinflip gamble")
@app_commands.describe(amount="Amount to bet", choice="head or tail")
async def coinflip(interaction: discord.Interaction, amount: int, choice: str):
    ud=get_user_data(interaction.user.id)
    if amount>ud["balance"] or amount<=0:
        await interaction.response.send_message("Invalid amount!", ephemeral=True)
        return
    result=random.choice(["head","tail"])
    data=load_data()
    uid=str(interaction.user.id)
    if choice.lower()==result:
        ud["balance"]+=amount
        msg=f"You won! It was {result}"
    else:
        ud["balance"]-=amount
        msg=f"You lost! It was {result}"
    data[uid]=ud
    save_data(data)
    await interaction.response.send_message(f"{msg} | Balance: {ud['balance']}")

@bot.tree.command(name="slots", description="Play slot machine")
@app_commands.describe(amount="Amount to bet")
async def slots(interaction: discord.Interaction, amount: int):
    ud=get_user_data(interaction.user.id)
    if amount>ud["balance"] or amount<=0:
        await interaction.response.send_message("Invalid amount!", ephemeral=True)
        return
    symbols=["🍒","🍋","💎","7️⃣","🍀"]
    r1=random.choice(symbols); r2=random.choice(symbols); r3=random.choice(symbols)
    data=load_data(); uid=str(interaction.user.id)
    if r1==r2==r3:
        win=amount*5
        ud["balance"]+=win
        msg=f"{r1} | {r2} | {r3}\nJACKPOT! You won {win}!"
    elif r1==r2 or r2==r3 or r1==r3:
        win=amount*2
        ud["balance"]+=win
        msg=f"{r1} | {r2} | {r3}\nNice! You won {win}!"
    else:
        ud["balance"]-=amount
        msg=f"{r1} | {r2} | {r3}\nYou lost {amount}!"
    data[uid]=ud; save_data(data)
    await interaction.response.send_message(f"{msg} | Balance: {ud['balance']}")

@bot.tree.command(name="roulette", description="Roulette red or black")
@app_commands.describe(amount="Amount to bet", color="red or black")
async def roulette(interaction: discord.Interaction, amount: int, color: str):
    ud=get_user_data(interaction.user.id)
    if amount>ud["balance"] or amount<=0:
        await interaction.response.send_message("Invalid amount!", ephemeral=True)
        return
    result=random.choice(["red","black"])
    data=load_data(); uid=str(interaction.user.id)
    if color.lower()==result:
        ud["balance"]+=amount
        msg=f"Ball landed on {result}! You won {amount}!"
    else:
        ud["balance"]-=amount
        msg=f"Ball landed on {result}! You lost {amount}!"
    data[uid]=ud; save_data(data)
    await interaction.response.send_message(f"{msg} | Balance: {ud['balance']}")

@bot.tree.command(name="dice", description="Roll dice higher than bot")
@app_commands.describe(amount="Amount to bet")
async def dice(interaction: discord.Interaction, amount: int):
    ud=get_user_data(interaction.user.id)
    if amount>ud["balance"] or amount<=0:
        await interaction.response.send_message("Invalid amount!", ephemeral=True)
        return
    user_roll=random.randint(1,6); bot_roll=random.randint(1,6)
    data=load_data(); uid=str(interaction.user.id)
    if user_roll>bot_roll:
        ud["balance"]+=amount
        msg=f"You rolled {user_roll} vs Bot {bot_roll} - You WON!"
    elif user_roll<bot_roll:
        ud["balance"]-=amount
        msg=f"You rolled {user_roll} vs Bot {bot_roll} - You LOST!"
    else:
        msg=f"Draw! Both rolled {user_roll} - No coins lost"
    data[uid]=ud; save_data(data)
    await interaction.response.send_message(f"{msg} | Balance: {ud['balance']}")

@bot.tree.command(name="leaderboard", description="Show top richest players")
async def leaderboard(interaction: discord.Interaction):
    data=load_data()
    if not data:
        await interaction.response.send_message("No players yet!")
        return
    sorted_players=sorted(data.items(), key=lambda x: x[1].get("balance",0), reverse=True)[:10]
    text="**Top 10 Richest:**\n"
    for i,(uid,ud) in enumerate(sorted_players,1):
        text+=f"{i}. <@{uid}> - {ud.get('balance',0)} coins\n"
    await interaction.response.send_message(text)

# --- ADMIN COMMANDS ---
@bot.tree.command(name="admin_add", description="Admin: Add coins to user")
@app_commands.describe(user="User to add coins to", amount="Amount to add")
async def admin_add(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("You are not admin!", ephemeral=True)
        return
    data=load_data(); uid=str(user.id)
    ud=get_user_data(user.id)
    ud["balance"]+=amount
    data[uid]=ud; save_data(data)
    await interaction.response.send_message(f"Added {amount} to {user.mention}. New balance: {ud['balance']}")

@bot.tree.command(name="admin_remove", description="Admin: Remove coins from user")
@app_commands.describe(user="User to remove coins from", amount="Amount to remove")
async def admin_remove(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("You are not admin!", ephemeral=True)
        return
    data=load_data(); uid=str(user.id)
    ud=get_user_data(user.id)
    ud["balance"]=max(0, ud["balance"]-amount)
    data[uid]=ud; save_data(data)
    await interaction.response.send_message(f"Removed {amount} from {user.mention}. New balance: {ud['balance']}")

@bot.tree.command(name="admin_set", description="Admin: Set user balance")
@app_commands.describe(user="User to set", amount="New balance")
async def admin_set(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not is_admin(interaction):
        await interaction.response.send_message("You are not admin!", ephemeral=True)
        return
    data=load_data(); uid=str(user.id)
    ud=get_user_data(user.id)
    ud["balance"]=amount
    data[uid]=ud; save_data(data)
    await interaction.response.send_message(f"Set {user.mention} balance to {amount}")

bot.run(os.getenv("DISCORD_TOKEN"))
