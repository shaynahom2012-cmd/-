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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)}")
    except Exception as e:
        print(e)

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

bot.run(os.getenv("DISCORD_TOKEN"))
