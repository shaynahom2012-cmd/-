import discord
from discord.ext import commands
from discord import app_commands
import json, os, random, asyncio, traceback
from datetime import datetime, timedelta
from pathlib import Path
import sys

# --- CONFIG ---
# הטוקן יגיע מ-Secret בשם DISCORD_TOKEN (ב-Replit / Render)
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
if not TOKEN:
    print("❌ לא נמצא טוקן! הגדר Secret בשם DISCORD_TOKEN")
    # נסיון לקרוא מקובץ .env אם קיים
    if Path(".env").exists():
        from dotenv import load_dotenv
        load_dotenv()
        TOKEN = os.getenv("DISCORD_TOKEN")

DATA_FILE = "casino_data.json"
START_BALANCE = 1000
DAILY_AMOUNT = 500

intents = discord.Intents.default()
# לא צריך message_content ל-Slash Commands
bot = commands.Bot(command_prefix="!", intents=intents)

# --- DATA HANDLING (אטומי ולא נשבר) ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        # אם הקובץ נשבר, מגבה אותו
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

# --- BLACKJACK ---
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
        if interaction.user.id != self.user_id:
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
            embed.set_footer(text=f"יתרה: {load_data().get(str(self.user_id), {}).get('balance',0)}$")
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            embed=discord.Embed(title="Blackjack", color=0x2ecc71)
            embed.add_field(name=f"היד שלך ({pv})", value=", ".join(self.player), inline=False)
            embed.add_field(name=f"דילר ({hand_value([self.dealer[0]])}+?)", value=f"{self.dealer[0]}, ?", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Stand 🛑", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("זה לא המשחק שלך!", ephemeral=True); return
        self.finished=True; self.clear_items()
        pv=hand_value(self.player); dv=hand_value(self.dealer)
        while dv<17:
            self.dealer.append(self.deck.pop()); dv=hand_value(self.dealer)
        embed=discord.Embed(title="Blackjack - סיום", color=0x2ecc71)
        embed.add_field(name=f"היד שלך ({pv})", value=", ".join(self.player), inline=False)
        embed.add_field(name=f"דילר ({dv})", value=", ".join(self.dealer), inline=False)
        if dv>21 or pv>dv:
            win=int(self.bet*1.5) if pv==21 and len(self.player)==2 else self.bet
            update_balance(self.user_id, self.bet+win)
            embed.add_field(name="תוצאה", value=f"ניצחת! +{win}$ רווח!", inline=False)
        elif pv==dv:
            update_balance(self.user_id, self.bet)
            embed.add_field(name="תוצאה", value="תיקו! כסף חוזר.", inline=False)
        else:
            embed.add_field(name="תוצאה", value=f"הפסדת {self.bet}$", inline=False)
        embed.set_footer(text=f"יתרה: {load_data().get(str(self.user_id), {}).get('balance',0)}$")
        await interaction.response.edit_message(embed=embed, view=self)

@bot.event
async def on_ready():
    print(f"✅ ONLINE {bot.user} | {len(bot.guilds)} servers")
    try:
        synced=await bot.tree.sync()
        print(f"✅ סונכרנו {len(synced)} פקודות Slash")
    except Exception as e:
        print(f"Sync error: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    traceback.print_exc()

# --- COMMANDS ---
@bot.tree.command(name="balance", description="כמה כסף יש לך")
async def balance_cmd(interaction: discord.Interaction):
    u,_=get_user_data(interaction.user.id)
    await interaction.response.send_message(embed=discord.Embed(title="💰 יתרה", description=f"יש לך **{u['balance']}$**", color=0xf1c40f))

@bot.tree.command(name="daily", description="בונוס יומי 500$")
async def daily_cmd(interaction: discord.Interaction):
    data=load_data(); uid=str(interaction.user.id)
    if uid not in data: data[uid]={"balance": START_BALANCE, "last_daily": None}
    last=data[uid].get("last_daily"); now=datetime.now()
    if last:
        try:
            lt=datetime.fromisoformat(last)
            if now-lt < timedelta(hours=24):
                rem=timedelta(hours=24)-(now-lt)
                h=int(rem.total_seconds()//3600); m=int((rem.total_seconds()%3600)//60)
                await interaction.response.send_message(f"כבר לקחת היום! תחזור בעוד {h}ש' {m}ד'", ephemeral=True); return
        except: pass
    data[uid]["balance"]+=DAILY_AMOUNT
    data[uid]["last_daily"]=now.isoformat()
    save_data(data)
    await interaction.response.send_message(f"🎉 קיבלת {DAILY_AMOUNT}$! יתרה: {data[uid]['balance']}$")

@bot.tree.command(name="slots", description="מכונת סלוטים")
@app_commands.describe(amount="סכום הימור")
async def slots_cmd(interaction: discord.Interaction, amount: int):
    u,_=get_user_data(interaction.user.id)
    if amount<=0 or u["balance"]<amount:
        await interaction.response.send_message(f"אין מספיק כסף! יתרה: {u['balance']}$", ephemeral=True); return
    update_balance(interaction.user.id, -amount)
    symbols=["🍒","🍋","🔔","⭐","💎"]
    reels=[random.choice(symbols) for _ in range(3)]
    text=" | ".join(reels)
    if reels[0]==reels[1]==reels[2]:
        win=amount*5 if reels[0]=="💎" else amount*3
        update_balance(interaction.user.id, amount+win)
        embed=discord.Embed(title="🎰 JACKPOT!", description=f"{text}\nזכית ב **{win}$**!", color=0x2ecc71)
    elif reels[0]==reels[1] or reels[1]==reels[2] or reels[0]==reels[2]:
        win=int(amount*0.5); update_balance(interaction.user.id, amount+win)
        embed=discord.Embed(title="⭐ זכייה קטנה", description=f"{text}\nזכית ב **{win}$**!", color=0xf1c40f)
    else:
        embed=discord.Embed(title="😢 הפסדת", description=f"{text}\nהפסדת {amount}$", color=0xe74c3c)
    embed.set_footer(text=f"יתרה: {load_data().get(str(interaction.user.id), {}).get('balance',0)}$")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="coinflip", description="הטלת מטבע")
@app_commands.describe(choice="בחר צד", amount="סכום הימור")
@app_commands.choices(choice=[app_commands.Choice(name="Heads", value="heads"), app_commands.Choice(name="Tails", value="tails")])
async def coinflip_cmd(interaction: discord.Interaction, choice: str, amount: int):
    u,_=get_user_data(interaction.user.id)
    if amount<=0 or u["balance"]<amount:
        await interaction.response.send_message(f"יתרה: {u['balance']}$", ephemeral=True); return
    update_balance(interaction.user.id, -amount)
    result=random.choice(["heads","tails"])
    if result==choice:
        update_balance(interaction.user.id, amount*2)
        msg=f"יצא **{result}**! ניצחת {amount}$"; col=0x2ecc71
    else:
        msg=f"יצא **{result}**! הפסדת {amount}$"; col=0xe74c3c
    embed=discord.Embed(title="Coinflip", description=msg, color=col)
    embed.set_footer(text=f"יתרה: {load_data().get(str(interaction.user.id), {}).get('balance',0)}$")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="blackjack", description="שחק בלאק ג'ק")
@app_commands.describe(amount="סכום הימור")
async def blackjack_cmd(interaction: discord.Interaction, amount: int):
    u,_=get_user_data(interaction.user.id)
    if amount<=0 or u["balance"]<amount:
        await interaction.response.send_message(f"יתרה: {u['balance']}$", ephemeral=True); return
    update_balance(interaction.user.id, -amount)
    view=BlackjackView(interaction.user.id, amount)
    pv=hand_value(view.player)
    if pv==21:
        view.finished=True; view.clear_items()
        win=int(amount*1.5); update_balance(interaction.user.id, amount+win)
        embed=discord.Embed(title="🃏 BLACKJACK!", description=f"{', '.join(view.player)}\nניצחת {win}$!", color=0xf1c40f)
        await interaction.response.send_message(embed=embed, view=view)
    else:
        embed=discord.Embed(title="Blackjack", color=0x2ecc71)
        embed.add_field(name=f"היד שלך ({pv})", value=", ".join(view.player), inline=False)
        embed.add_field(name=f"דילר ({hand_value([view.dealer[0]])}+?)", value=f"{view.dealer[0]}, ?", inline=False)
        await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="leaderboard", description="טבלת עשירים")
async def leaderboard_cmd(interaction: discord.Interaction):
    data=load_data()
    top=sorted(data.items(), key=lambda x: x[1].get("balance",0), reverse=True)[:10]
    desc="\n".join([f"**{i}.** <@{uid}> - **{ud.get('balance',0)}$**" for i,(uid,ud) in enumerate(top,1)]) or "אין נתונים"
    await interaction.response.send_message(embed=discord.Embed(title="🏆 Leaderboard", description=desc, color=0xf1c40f))

# --- RUNNER עם RECONNECT אוטומטי (ל-24/7) ---
async def main():
    if not TOKEN:
        print("❌ אין DISCORD_TOKEN - הגדר ב-Secrets")
        sys.exit(1)
    while True:
        try:
            await bot.start(TOKEN)
        except Exception as e:
            print(f"⚠️ הבוט נפל, מנסה להתחבר מחדש בעוד 5 שניות... {e}")
            traceback.print_exc()
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
