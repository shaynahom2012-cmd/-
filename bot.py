import discord
from discord.ext import commands, tasks
import json, random, os
from datetime import datetime

TOKEN = os.getenv("TOKEN") or "MTU1MDA5NjA3Nzg1ODkzNDc4NA.GUlC5q.pnLCvhefXBee3lxlkCroCLIY_2PB5dZPOBwncs"
DAILY_AMOUNT = 10
ADMIN_ID = 1322491202704113736

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
        data[uid]={"coins":0,"last_daily":""}
    return data[uid]

# --- כפתור Daily ---
class DailyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # כפתור נשאר לנצח
    
    @discord.ui.button(label="🎁 קבל 10 מטבעות יומיים", style=discord.ButtonStyle.gold, custom_id="daily_claim")
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
    print(f"Casino Bot is online! Logged in as {bot.user}")
    # מחזיר את הכפתור לעבוד אחרי ריסטארט
    bot.add_view(DailyView())
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)} commands registered.")
        print("הבוט אוטומטי ומוכן! הכפתור יעבוד 24/7")
    except Exception as e:
        print(e)

# פקודה ששולחת את הכפתור
@bot.tree.command(name="daily", description="לחץ על כפתור לקבל 10 מטבעות כל יום")
async def daily(interaction: discord.Interaction):
    u = get_user(interaction.user.id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    embed = discord.Embed(
        title="🎰 בונוס יומי",
        description=f"יש לך **{u['coins']}** מטבעות\nלחץ על הכפתור למטה כדי לקבל {DAILY_AMOUNT} מטבעות!",
        color=discord.Color.gold()
    )
    if u["last_daily"] == today:
        embed.description = f"כבר לקחת היום! יש לך **{u['coins']}** מטבעות\nתחזור מחר"
    
    await interaction.response.send_message(embed=embed, view=DailyView())

# פקודה לאדמין - שולח כפתור קבוע לערוץ
@bot.tree.command(name="setup_daily", description="שולח כפתור daily קבוע לערוץ (אדמין)")
async def setup_daily(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ רק אדמין", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎁 בונוס יומי - לחץ כל יום!",
        description=f"לחצו על הכפתור כל יום וקבלו **{DAILY_AMOUNT}** מטבעות בחינם!\n\nהכפתור הזה עובד **24/7 אוטומטית** - גם כשהמחשב שלך מכובה!",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=DailyView())
    # שולח גם הודעה רגילה עם הכפתור שישאר
    await interaction.followup.send("⬇️ הכפתור כאן למטה - תלחצו כל יום!", view=DailyView())

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
    win = len(set(r))==1
    if win:
        prize=amount*5
        u["coins"]+=prize
        msg=f"{''.join(r)}\n🎰 JACKPOT! זכית ב {prize}!"
    else:
        u["coins"]-=amount
        msg=f"{''.join(r)}\n😢 הפסדת {amount}"
    save()
    await interaction.response.send_message(msg+f"\nיתרה: {u['coins']}")

@bot.command(name="addmoney")
async def addmoney_prefix(ctx, member: discord.Member, amount: int):
    if ctx.author.id != ADMIN_ID:
        await ctx.send("❌ רק אתה יכול!")
        return
    u = get_user(member.id)
    u["coins"] += amount
    save()
    await ctx.send(f"✅ הוספתי **{amount}** ל-{member.mention} | יש לו עכשיו **{u['coins']}**")

@bot.tree.command(name="addmoney", description="הוסף כסף למישהו (אדמין)")
async def addmoney_slash(interaction: discord.Interaction, user: discord.Member, amount: int):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ רק אתה יכול", ephemeral=True)
        return
    u = get_user(user.id)
    u["coins"] += amount
    save()
    await interaction.response.send_message(f"✅ הוספתי **{amount}** ל-{user.mention} | יש לו עכשיו **{u['coins']}**")

bot.run(TOKEN)
