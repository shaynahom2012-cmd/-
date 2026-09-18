import discord
from discord.ext import commands
from discord import app_commands
import os, json, random
from flask import Flask
import threading

app = Flask(__name__)
@app.route('/')
def home(): return "Bot is online!"
def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def load_data():
    if not os.path.exists("data.json"): return {}
    try:
        with open("data.json","r",encoding="utf-8") as f: return json.load(f)
    except: return {}
def save_data(d):
    with open("data.json","w",encoding="utf-8") as f: json.dump(f,f)
def get_user_data(uid):
    data=load_data()
    s=str(uid)
    if s not in data: data[s]={"balance":1000}; save_data(data)
    return data[s]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.tree.sync()

@bot.tree.command(name="balance", description="בדוק יתרה")
async def balance(interaction: discord.Interaction):
    d=get_user_data(interaction.user.id)
    await interaction.response.send_message(f"💰 יש לך {d['balance']}")

@bot.tree.command(name="daily", description="בונוס יומי")
async def daily(interaction: discord.Interaction):
    data=load_data(); uid=str(interaction.user.id); ud=get_user_data(interaction.user.id)
    ud["balance"]+=500; data[uid]=ud; save_data(data)
    await interaction.response.send_message(f"קיבלת 500! יש לך {ud['balance']}")

@bot.tree.command(name="coinflip", description="הטלת מטבע")
@app_commands.describe(amount="סכום", choice="head/tail")
async def coinflip(interaction: discord.Interaction, amount: int, choice: str):
    ud=get_user_data(interaction.user.id)
    if amount>ud["balance"] or amount<=0:
        await interaction.response.send_message("סכום לא תקין!", ephemeral=True); return
    result=random.choice(["head","tail"]); data=load_data(); uid=str(interaction.user.id)
    if choice.lower()==result: ud["balance"]+=amount; msg=f"ניצחת! יצא {result}"
    else: ud["balance"]-=amount; msg=f"הפסדת! יצא {result}"
    data[uid]=ud; save_data(data)
    await interaction.response.send_message(f"{msg} | יתרה: {ud['balance']}")

bot.run(os.getenv("DISCORD_TOKEN"))
