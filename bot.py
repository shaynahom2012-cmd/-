import discord
from discord.ext import commands
import json, random, os
from datetime import datetime
from flask import Flask
import threading

# --- Flask for Render ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is online!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
ADMIN_ID = 1322491202704113736
DAILY_AMOUNT = 10

if not TOKEN:
    print("ERROR: No token found! Set DISCORD_TOKEN in Render")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

try:
    with open("data.json","r", encoding="utf-8") as f:
        data = json.load(f)
except:
    data = {}

def save():
    with open("data.json","w", encoding="utf-8") as f:
        json.dump(data,f, ensure_ascii=False, indent=2)

def get_user(uid):
    uid=str(uid)
    if uid not in data:
        data[uid]={"coins":1000,"last_daily":""}
    return data[uid]

# --- Daily Button 24/7 ---
class DailyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🎁 קבל 10 מטבעות יומיים", style=discord.ButtonStyle.success, custom_id="daily_claim")
    async def daily_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        u = get_user(interaction.user.id)
        today = datetime.now().strftime("%Y-%m-%d")
        if u["last_daily"] == today:
            await interaction.response.send_message("❌ כבר לקחת היום! תחזור מחר 🎰", ephemeral=True)
            return
        u["coins"] += DAILY_AMOUNT
        u["last_daily"] = today
        save()
        await interaction.response.send_message(f"🎉 קיבלת {DAILY_AMOUNT} מטבעות! יש לך עכשיו **{u['coins']}** מטבעות", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    bot.add_view(DailyView())
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands globally")
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
            print(f"Synced to guild {guild.name}")
    except Exception as e:
        print(f"Sync error: {e}")

@bot.tree.command(name="daily", description="לחץ על כפתור לקבל 10 מטבעות כל יום")
async def daily(interaction: discord.Interaction):
    u = get_user(interaction.user.id)
    embed = discord.Embed(title="🎰 בונוס יומי", description=f"יש לך **{u['coins']}** מטבעות\nלחץ על הכפתור למטה!", color=discord.Color.gold())
    if u["last_daily"] == datetime.now().strftime("%Y-%m-%d"):
        embed.description = f"כבר לקחת היום! יש לך **{u['coins']}** מטבעות\nתחזור מחר"
    await interaction.response.send_message(embed=embed, view=DailyView())

@bot.tree.command(name="setup_daily", description="שולח כפתור daily קבוע (אדמין בלבד)")
async def setup_daily(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ רק אדמין", ephemeral=True)
        return
    embed = discord.Embed(title="🎁 בונוס יומי - לחץ כל יום!", description=f"לחצו כל יום וקבלו **{DAILY_AMOUNT}** מטבעות בחינם!\n\nהכפתור עובד **24/7 אוטומטית**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed, view=DailyView())

@bot.tree.command(name="balance", description="כמה כסף יש לך")
async def balance(interaction: discord.Interaction):
    u=get_user(interaction.user.id)
    await interaction.response.send_message(f"💰 יש לך {u['coins']} מטבעות")

@bot.tree.command(name="slots", description="מכונת סלוטס")
async def slots(interaction: discord.Interaction, amount: int):
    u=get_user(interaction.user.id)
    if u["coins"]<amount or amount<=0:
        await interaction.response.send_message("אין לך מספיק כסף!", ephemeral=True)
        return
    symbols=["🍒","🍋","💎","7️⃣","🍀"]
    r=[random.choice(symbols) for _ in range(3)]
    if len(set(r))==1:
        prize=amount*5
        u["coins"]+=prize
        msg=f"{''.join(r)}\n🎰 JACKPOT! זכית ב {prize}!"
    else:
        u["coins"]-=amount
        msg=f"{''.join(r)}\n😢 הפסדת {amount}"
    save()
    await interaction.response.send_message(msg+f"\nיתרה: {u['coins']}")

@bot.tree.command(name="coinflip", description="הטלת מטבע")
@discord.app_commands.describe(amount="סכום", choice="head או tail")
async def coinflip(interaction: discord.Interaction, amount: int, choice: str):
    u=get_user(interaction.user.id)
    if u["coins"]<amount or amount<=0:
        await interaction.response.send_message("אין מספיק", ephemeral=True)
        return
    result=random.choice(["head","tail"])
    if choice.lower()==result:
        u["coins"]+=amount
        msg=f"ניצחת! יצא {result}"
    else:
        u["coins"]-=amount
        msg=f"הפסדת! יצא {result}"
    save()
    await interaction.response.send_message(f"{msg} | יתרה: {u['coins']}")

@bot.tree.command(name="roulette", description="רולטה אדום/שחור")
async def roulette(interaction: discord.Interaction, amount: int, color: str):
    u=get_user(interaction.user.id)
    if u["coins"]<amount or amount<=0:
        await interaction.response.send_message("אין מספיק", ephemeral=True)
        return
    result=random.choice(["red","black"])
    if color.lower()==result:
        u["coins"]+=amount
        msg=f"יצא {result}! ניצחת {amount}!"
    else:
        u["coins"]-=amount
        msg=f"יצא {result}! הפסדת {amount}!"
    save()
    await interaction.response.send_message(f"{msg} | יתרה: {u['coins']}")

@bot.tree.command(name="dice", description="קוביות נגד הבוט")
async def dice(interaction: discord.Interaction, amount: int):
    u=get_user(interaction.user.id)
    if u["coins"]<amount or amount<=0:
        await interaction.response.send_message("אין מספיק", ephemeral=True)
        return
    user_roll=random.randint(1,6); bot_roll=random.randint(1,6)
    if user_roll>bot_roll:
        u["coins"]+=amount
        msg=f"אתה {user_roll} נגד בוט {bot_roll} - ניצחת!"
    elif user_roll<bot_roll:
        u["coins"]-=amount
        msg=f"אתה {user_roll} נגד בוט {bot_roll} - הפסדת!"
    else:
        msg=f"תיקו! שניכם {user_roll}"
    save()
    await interaction.response.send_message(f"{msg} | יתרה: {u['coins']}")

@bot.tree.command(name="leaderboard", description="טבלת עשירים")
async def leaderboard(interaction: discord.Interaction):
    if not data:
        await interaction.response.send_message("אין שחקנים עדיין")
        return
    sorted_players=sorted(data.items(), key=lambda x: x[1].get("coins",0), reverse=True)[:10]
    text="**Top 10:**\n"
    for i,(uid,ud) in enumerate(sorted_players,1):
        text+=f"{i}. <@{uid}> - {ud.get('coins',0)} coins\n"
    await interaction.response.send_message(text)

@bot.tree.command(name="addmoney", description="הוסף כסף (אדמין בלבד)")
async def addmoney_slash(interaction: discord.Interaction, user: discord.Member, amount: int):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ רק אתה יכול", ephemeral=True)
        return
    u = get_user(user.id); u["coins"] += amount; save()
    await interaction.response.send_message(f"✅ הוספתי {amount} ל-{user.mention} | יש לו {u['coins']}")

@bot.command(name="addmoney")
async def addmoney_prefix(ctx, member: discord.Member, amount: int):
    if ctx.author.id != ADMIN_ID:
        await ctx.send("❌ רק אתה יכול!")
        return
    u = get_user(member.id); u["coins"] += amount; save()
    await ctx.send(f"✅ הוספתי {amount} ל-{member.mention} | {u['coins']}")

bot.run(TOKEN)
