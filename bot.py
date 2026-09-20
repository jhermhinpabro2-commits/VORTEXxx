import discord
from discord.ext import commands
import datetime
import os
from flask import Flask
import threading

app = Flask('')
@app.route('/')
def home(): return "✅ BOT IS ALIVE!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): threading.Thread(target=run).start()

BOT_TOKEN = os.getenv("BOT_TOKEN")  # ✅ WALANG TOKEN DITO — KUKUNIN SA RENDER!
OWNER_ID = 1432638241177075827
DEFAULT_BALANCE = 100000
DAILY_REWARD = 500
DAILY_GIVE_LIMIT = 100000
MAX_BET = 250000

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="*", intents=intents, help_command=None)
balances = {}
daily_used = {}
last_reset = datetime.date.today()

info_log_channel_id = None
auto_role_id = None
whitelisted_users = set()
BAN_LIMIT = 3
KICK_LIMIT = 3
CREATE_LIMIT = 2
TIME_WINDOW = 10


# ──────────── UTILS ────────────
def is_owner(uid): return uid == OWNER_ID
def is_protected(user_id):
    return user_id in whitelisted_users or user_id == OWNER_ID
def get_bal(uid):
    if uid not in balances: balances[uid] = DEFAULT_BALANCE
    return balances[uid]
def add_bal(uid, amt):
    if is_owner(uid):
        balances[uid] = balances.get(uid, DEFAULT_BALANCE) + amt
    else:
        balances[uid] = max(0, balances.get(uid, DEFAULT_BALANCE) + amt)
    return balances[uid]
def reset_daily():
    global last_reset, daily_used
    today = datetime.date.today()
    if today != last_reset:
        daily_used = {}
        last_reset = today

def calculate_account_age(created_at):
    now = datetime.datetime.now(datetime.timezone.utc)
    delta = now - created_at
    y, m, d = delta.days // 365, (delta.days % 365) // 30, (delta.days % 365) % 30
    h = delta.seconds // 3600
    if y > 0: return f"{y}y {m}m {d}d"
    elif m > 0: return f"{m}m {d}d"
    elif d > 0: return f"{d}d {h}h"
    else: return f"{h}h"

def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

# 🎨 GRADIENT GENERATOR
def make_gradient(text, hex_colors):
    chars = list(text)
    n = len(chars)
    if len(hex_colors) == 1:
        return f'<font color="{hex_colors[0]}">{text}</font>'
    elif len(hex_colors) == 2:
        mid = n // 2
        return f'<font color="{hex_colors[0]}">{text[:mid]}</font><font color="{hex_colors[1]}">{text[mid:]}</font>'
    elif len(hex_colors) == 3:
        p1, p2 = n//3, (n*2)//3
        return f'<font color="{hex_colors[0]}">{text[:p1]}</font><font color="{hex_colors[1]}">{text[p1:p2]}</font><font color="{hex_colors[2]}">{text[p2:]}</font>'
    elif len(hex_colors) == 4:
        q1, q2, q3 = n//4, n//2, (n*3)//4
        return f'<font color="{hex_colors[0]}">{text[:q1]}</font><font color="{hex_colors[1]}">{text[q1:q2]}</font><font color="{hex_colors[2]}">{text[q2:q3]}</font><font color="{hex_colors[3]}">{text[q3:]}</font>'
    return text

# ──────────── 📋 MEMBER JOIN — ENHANCED USER INFO ────────────
@bot.event
async def on_member_join(member):
    global info_log_channel_id, auto_role_id
    if auto_role_id:
        role = member.guild.get_role(auto_role_id)
        if role:
            try: await member.add_roles(role, reason="Auto-Role")
            except: pass
    if info_log_channel_id:
        channel = bot.get_channel(info_log_channel_id)
        if channel:
            created_at = member.created_at
            account_age = calculate_account_age(created_at)
            join_time = datetime.datetime.now(datetime.timezone.utc)
            shared_servers = 0
            server_list = []
            for guild in bot.guilds:
                if member in guild.members:
                    shared_servers += 1
                    if len(server_list) < 5:
                        server_list.append(f"• {guild.name}")
            server_text = f"{shared_servers} server(s)"
            if server_list:
                server_text += "\n" + "\n".join(server_list)
                if shared_servers > 5:
                    server_text += f"\n• +{shared_servers - 5} more..."
            em = discord.Embed(
                title="🎉 NEW MEMBER JOINED",
                description=f"**User:** {member.mention}\n**Username:** `{member}`",
                color=discord.Color.from_rgb(79, 84, 255),
                timestamp=join_time
            )
            em.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            em.add_field(name="🆔 User ID", value=f"`{member.id}`", inline=True)
            em.add_field(name="📅 Account Age", value=account_age, inline=True)
            em.add_field(name="🕐 Created At", value=format_time(created_at), inline=True)
            em.add_field(name="🔄 Servers Shared", value=server_text, inline=False)
            em.add_field(name="✅ Joined At", value=format_time(join_time), inline=False)
            em.set_footer(text=f"Total Members: {member.guild.member_count} • VORTEX Bot 💜")
            await channel.send(embed=em)

# ──────────── 👋 MEMBER LEAVE — AUTO LOG ────────────
@bot.event
async def on_member_remove(member):
    global info_log_channel_id
    if info_log_channel_id:
        channel = bot.get_channel(info_log_channel_id)
        if channel:
            em = discord.Embed(
                title="➖ MEMBER LEFT",
                color=discord.Color.from_rgb(231, 76, 60),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            em.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            em.add_field(name="👤 User", value=f"{member.mention}\n`{member}`", inline=True)
            em.add_field(name="🆔 User ID", value=f"`{member.id}`", inline=True)
            em.set_footer(text=f"Total Members: {member.guild.member_count}")
            await channel.send(embed=em)

# ──────────── ON READY ────────────
@bot.event
async def on_ready():
    print(f"✅ LOGGED IN: {bot.user}")
    print(f"📋 Info Log Channel: {'Set' if info_log_channel_id else 'Not set — use *setinfolog #channel'}")
    await bot.change_presence(activity=discord.Game(name="*help | JHER BOT 🎲"))

# ──────────── HELP — BEAUTIFUL UI ✨ ────────────
@bot.command(name="help")
async def help_cmd(ctx):
    b = get_bal(ctx.author.id)
    own = " 👑 UNLIMITED" if is_owner(ctx.author.id) else ""
    
    em = discord.Embed(
        title="✨ JHER BOT — COMMAND LIST ✨",
        description=f"💳 **Your Balance:** `₱{b:,}`{own}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=discord.Color.from_rgb(102, 126, 234)
    )
    em.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
    em.add_field(
        name="🛡️ ANTI-NUKE & WHITELIST 🔒",
        value="`*whitelist add @user` — Protect user from anti-nuke\n`*whitelist remove @user` — Remove from protection\n`*whitelist list` — Show all protected users",
        inline=False
    )
    
    em.add_field(
        name="🔧 MODERATION",
        value="`*kick @user [reason]`\n`*ban @user [reason]`\n`*unban @user`\n`*timeout @user 10m [reason]`\n`*clear [amount]`",
        inline=False
    )
    
    em.add_field(
        name="🎲 GAMBLING",
        value="`*cf heads 500` — Bet heads\n`*coinflip tails 1000` — Bet tails",
        inline=False
    )
    
    em.add_field(
        name="💰 ECONOMY",
        value="`*balance` — Check your balance\n`*daily` — Claim daily reward\n`*give @user 5000` — Send coins\n`*leaderboard` — Top 10 richest users",
        inline=False
    )
    
    em.add_field(
        name="⚙️ SETUP & FEATURES",
        value="`*setinfolog #ch` — Set join log channel\n`*setautorole @role` — Auto-role on join\n`*dm @user message` — DM user via bot",
        inline=False
    )
    
    em.add_field(
        name="🎨 TOOLS",
        value="`*gradient #FF0000 #FFFFFF Your Text` — Create gradient text",
        inline=False
    )

    
    await ctx.send(embed=em)


# ──────────── ✉️ DM USER ────────────
@bot.command(name="dm")
@commands.has_permissions(administrator=True)
async def dm_user(ctx, member: discord.Member, *, message=None):
    if not message:
        return await ctx.send("❌ Usage: `*dm @user Your message here`", delete_after=5)
    if member.bot:
        return await ctx.send("❌ Cannot DM bots!", delete_after=5)
    try:
        em = discord.Embed(
            title="📩 Message from Server",
            description=message,
            color=discord.Color.from_rgb(79, 84, 255),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        em.set_footer(text=f"From: {ctx.guild.name} • By: {ctx.author.display_name}")
        await member.send(embed=em)
        await ctx.send(f"✅ Message sent to {member.mention}!")
    except discord.Forbidden:
        await ctx.send(f"❌ Cannot DM {member.mention} — their DMs are off!", delete_after=5)

# ──────────── ⚙️ SET INFO LOG ────────────
@bot.command(name="setinfolog")
@commands.has_permissions(administrator=True)
async def set_info_log(ctx, channel: discord.TextChannel = None):
    global info_log_channel_id
    if not channel:
        return await ctx.send("❌ Usage: `*setinfolog #channel`", delete_after=5)
    info_log_channel_id = channel.id
    await ctx.send(f"✅ Info Log Channel set to {channel.mention}!")

# ──────────── ⚙️ SET AUTO ROLE ────────────
@bot.command(name="setautorole")
@commands.has_permissions(administrator=True)
async def set_auto_role(ctx, role: discord.Role = None):
    global auto_role_id
    if not role:
        return await ctx.send("❌ Usage: `*setautorole @role`", delete_after=5)
    auto_role_id = role.id
    await ctx.send(f"✅ Auto-Role set to {role.mention}!")

# ──────────── 🛡️ MODERATION ────────────
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, reason="No reason given"):
    if member.top_role >= ctx.author.top_role and not is_owner(ctx.author.id):
        await ctx.send("❌ You cannot kick someone with a higher or equal role!", delete_after=5)
        return
    await member.kick(reason=reason)
    em = discord.Embed(title="👤 KICKED", color=discord.Color.orange())
    em.add_field(name="User", value=member.mention, inline=True)
    em.add_field(name="Reason", value=reason, inline=True)
    em.set_footer(text=f"By: {ctx.author.display_name}")
    await ctx.send(embed=em)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, member: discord.Member, *, reason="No reason given"):
    if member.top_role >= ctx.author.top_role and not is_owner(ctx.author.id):
        await ctx.send("❌ You cannot ban someone with a higher or equal role!", delete_after=5)
        return
    await member.ban(reason=reason)
    em = discord.Embed(title="🔨 BANNED", color=discord.Color.red())
    em.add_field(name="User", value=member.mention, inline=True)
    em.add_field(name="Reason", value=reason, inline=True)
    em.set_footer(text=f"By: {ctx.author.display_name}")
    await ctx.send(embed=em)

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban_cmd(ctx, user: discord.User, *, reason="No reason given"):
    try:
        await ctx.guild.unban(user, reason=reason)
        em = discord.Embed(title="✅ UNBANNED", color=discord.Color.green())
        em.add_field(name="User", value=user.mention, inline=True)
        em.set_footer(text=f"By: {ctx.author.display_name}")
        await ctx.send(embed=em)
    except:
        await ctx.send("❌ That user is not banned!", delete_after=5)

@bot.command(name="timeout", aliases=["mute"])
@commands.has_permissions(moderate_members=True)
async def timeout_cmd(ctx, member: discord.Member, duration=None, *, reason="No reason given"):
    if member.top_role >= ctx.author.top_role and not is_owner(ctx.author.id):
        await ctx.send("❌ You cannot timeout someone with a higher or equal role!", delete_after=5)
        return
    if not duration:
        await ctx.send("❌ Usage: `*timeout @user 10m reason`\nTime: m=min, h=hrs, d=days", delete_after=6)
        return
    dur = duration.lower()
    if dur.endswith("m"): seconds = int(dur[:-1]) * 60
    elif dur.endswith("h"): seconds = int(dur[:-1]) * 3600
    elif dur.endswith("d"): seconds = int(dur[:-1]) * 86400
    else:
        await ctx.send("❌ Format: 10m / 1h / 1d", delete_after=5)
        return
    if seconds > 604800:
        await ctx.send("❌ Max timeout is 7 days!", delete_after=5)
        return
    await member.timeout(datetime.timedelta(seconds=seconds), reason=reason)
    em = discord.Embed(title="⏱️ TIMED OUT", color=discord.Color.dark_orange())
    em.add_field(name="User", value=member.mention, inline=True)
    em.add_field(name="Duration", value=duration, inline=True)
    em.add_field(name="Reason", value=reason, inline=False)
    em.set_footer(text=f"By: {ctx.author.display_name}")
    await ctx.send(embed=em)

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_cmd(ctx, amount: int = 10):
    if amount > 100: amount = 100
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ Cleared {amount} messages!", delete_after=3)

# ──────────── 🎲 COINFLIP ────────────
@bot.command(name="coinflip", aliases=["cf"])
async def coinflip(ctx, choice=None, bet=None):
    uid = ctx.author.id
    if not choice or not bet:
        em = discord.Embed(title="🎲 COINFLIP — HEADS / TAILS", description=f"Max Bet: ₱{MAX_BET:,}\nUsage: `*cf heads 5000`", color=discord.Color.gold())
        em.add_field(name="💰 Your Balance", value=f"₱{get_bal(uid):,}", inline=True)
        await ctx.send(embed=em)
        return
    choice = choice.lower()
    if choice in ["head", "h"]: choice = "heads"
    elif choice in ["tail", "t"]: choice = "tails"
    if choice not in ["heads", "tails"]:
        await ctx.send("❌ Use: `heads` or `tails`\nExample: `*cf heads 1000`", delete_after=5)
        return
    try: bet = int(bet)
    except: await ctx.send("❌ Enter a number!", delete_after=5); return
    if bet <= 0: await ctx.send("❌ Bet must be positive!", delete_after=5); return
    if bet > MAX_BET and not is_owner(uid):
        await ctx.send(f"❌ Max bet is ₱{MAX_BET:,} only!", delete_after=5); return
    bal_now = get_bal(uid)
    if not is_owner(uid) and bet > bal_now:
        em = discord.Embed(title="❌ Insufficient Balance", color=discord.Color.red())
        em.add_field(name="You have", value=f"₱{bal_now:,}", inline=True)
        em.add_field(name="Your Bet", value=f"₱{bet:,}", inline=True)
        await ctx.send(embed=em); return
    result = random.choice(["heads", "tails"])
    won = choice == result
    if won:
        new_bal = add_bal(uid, bet)
        txt, col = "✅ YOU WON!", discord.Color.green()
    else:
        new_bal = add_bal(uid, -bet) if not is_owner(uid) else bal_now
        txt, col = "❌ YOU LOST!", discord.Color.red()
    em = discord.Embed(title="🎲 RESULT", color=col)
    em.add_field(name="Your Pick", value=choice.upper(), inline=True)
    em.add_field(name="Result", value=result.upper(), inline=True)
    em.add_field(name="Bet Amount", value=f"₱{bet:,}", inline=True)
    em.add_field(name="New Balance", value=f"₱{new_bal:,}", inline=False)
    await ctx.send(embed=em)

# ──────────── 💰 ECONOMY ────────────
@bot.command(name="balance", aliases=["bal"])
async def balance(ctx, mem: discord.Member=None):
    mem = mem or ctx.author
    own = " | 👑 UNLIMITED" if is_owner(mem.id) else ""
    await ctx.send(embed=discord.Embed(title="💰 BALANCE", description=f"{mem.mention}: ₱{get_bal(mem.id):,}{own}", color=discord.Color.green()))

@bot.command(name="daily")
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    nb = add_bal(ctx.author.id, DAILY_REWARD)
    await ctx.send(embed=discord.Embed(title="🎁 DAILY REWARD", description=f"+₱{DAILY_REWARD} claimed!\nNew Balance: ₱{nb:,}", color=discord.Color.yellow()))

@daily.error
async def daily_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        h = int(error.retry_after // 3600)
        m = int((error.retry_after % 3600) // 60)
        await ctx.send(f"⏳ Come back in {h}h {m}m!", delete_after=5)

@bot.command(name="give")
async def give(ctx, mem: discord.Member=None, amt=None):
    uid = ctx.author.id
    if not mem or not amt:
        await ctx.send("❌ Usage: `*give @user 5000`", delete_after=5); return
    if mem.id == uid:
        await ctx.send("❌ Cannot give to yourself!", delete_after=5); return
    try: amt = int(amt)
    except: await ctx.send("❌ Enter a number!", delete_after=5); return
    if amt <= 0:
        await ctx.send("❌ Amount must be positive!", delete_after=5); return
    reset_daily()
    if not is_owner(uid):
        used = daily_used.get(uid, 0)
        if amt > DAILY_GIVE_LIMIT - used:
            await ctx.send(f"❌ Daily limit left: ₱{DAILY_GIVE_LIMIT - used:,}", delete_after=5); return
        if amt > get_bal(uid):
            await ctx.send("❌ Insufficient balance!", delete_after=5); return
        add_bal(uid, -amt)
        daily_used[uid] = used + amt
    add_bal(mem.id, amt)
    em = discord.Embed(title="💸 PAYMENT SENT!", color=discord.Color.green())
    em.add_field(name="From", value=ctx.author.mention, inline=True)
    em.add_field(name="To", value=mem.mention, inline=True)
    em.add_field(name="Amount", value=f"₱{amt:,}", inline=False)
    await ctx.send(embed=em)

@bot.command(name="leaderboard", aliases=["lb"])
async def lb(ctx):
    if not balances:
        await ctx.send("❌ No data yet! Use `*daily` first.", delete_after=5); return
    top = sorted(balances.items(), key=lambda x:x[1], reverse=True)[:10]
    em = discord.Embed(title="🏆 TOP 10 RICHEST USERS", color=discord.Color.gold())
    med = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    for i,(uid,b) in enumerate(top):
        u = await bot.fetch_user(uid)
        tag = " 👑" if is_owner(uid) else ""
        em.add_field(name=f"{med[i]} #{i+1} — {u}{tag}", value=f"₱{b:,}", inline=False)
    await ctx.send(embed=em)

# ──────────── 🎨 GRADIENT ────────────
@bot.command(name="gradient")
async def gradient_cmd(ctx, *, args=None):
    if not args:
        em = discord.Embed(title="🎨 GRADIENT TEXT GENERATOR", description="Create colored text!\n\nFormat: `*gradient #FF0000 #FFFFFF Your Text`\n✅ 1–4 Hex Colors only!", color=discord.Color.purple())
        await ctx.send(embed=em); return
    parts = args.split()
    colors = []
    text_parts = []
    for p in parts:
        if p.startswith("#") and len(p) in [4,7]:
            colors.append(p)
        else:
            text_parts.append(p)
    text = " ".join(text_parts)
    if not colors or not text:
        await ctx.send("❌ Example: `*gradient #FF0000 #FFFFFF Your Text`", delete_after=5); return
    if len(colors) > 4:
        await ctx.send("❌ Max 4 colors!", delete_after=5); return
    output = make_gradient(text, colors)
    em = discord.Embed(title="🎨 GENERATED!", description=f"**Input:** `{text}`\n**Colors:** {' → '.join(colors)}\n\n📤 Output:\n```html\n{output}\n```", color=discord.Color.purple())
    await ctx.send(embed=em)
# ──────────── 👑 OWNER COMMANDS — HIDDEN, ONLY YOU CAN USE ✅ ────────────
@bot.command(name="setbalance", aliases=["setbal"])
async def setbal(ctx, mem: discord.Member=None, amt=None):
    if not is_owner(ctx.author.id):
        return
    if not mem or amt is None:
        return await ctx.send("❌ Usage: `*setbal @user 500000`")
    balances[mem.id] = int(amt)
    await ctx.send(f"✅ Balance set! {mem.mention} → ₱{amt:,}")

@bot.command(name="addbalance", aliases=["addbal"])
async def addbal(ctx, mem: discord.Member=None, amt=None):
    if not is_owner(ctx.author.id):
        return
    if not mem or amt is None:
        return await ctx.send("❌ Usage: `*addbal @user 10000`")
    nb = add_bal(mem.id, int(amt))
    await ctx.send(f"✅ Added! +₱{amt:,} → {mem.mention} = ₱{nb:,}")

@bot.command(name="resetall")
async def resetall(ctx):
    if not is_owner(ctx.author.id):
        return
    balances.clear()
    daily_used.clear()
    await ctx.send("✅ ALL BALANCES RESET! Back to ₱100,000 for everyone!")
    
    # ──────────── 🛡️ WHITELIST COMMAND ────────────
@bot.command(name="whitelist")
async def whitelist_cmd(ctx, action=None, target=None):
    if not is_owner(ctx.author.id):
        return
    if not action or not target:
        em = discord.Embed(title="🛡️ WHITELIST MANAGEMENT", color=discord.Color.blue())
        em.add_field(name="Add User", value="`*whitelist add @user`", inline=False)
        em.add_field(name="Remove User", value="`*whitelist remove @user`", inline=False)
        em.add_field(name="List All", value="`*whitelist list`", inline=False)
        await ctx.send(embed=em)
        return
    if action.lower() == "add":
        try:
            user = await commands.MemberConverter().convert(ctx, target)
            whitelisted_users.add(user.id)
            await ctx.send(f"✅ {user.mention} ADDED TO WHITELIST — protected from anti-nuke!")
        except:
            await ctx.send("❌ Invalid user! Use @mention", delete_after=5)
    elif action.lower() == "remove":
        try:
            user = await commands.MemberConverter().convert(ctx, target)
            whitelisted_users.discard(user.id)
            await ctx.send(f"✅ {user.mention} REMOVED FROM WHITELIST")
        except:
            await ctx.send("❌ Invalid user!", delete_after=5)
    elif action.lower() == "list":
        if not whitelisted_users:
            await ctx.send("❌ No whitelisted users!")
            return
        em = discord.Embed(title="🛡️ WHITELISTED USERS", color=discord.Color.green())
        desc = ""
        for uid in whitelisted_users:
            u = await bot.fetch_user(uid)
            desc += f"• {u.mention} (`{u.id}`)\n"
        em.description = desc
        await ctx.send(embed=em)


# ──────────── RUN BOT ────────────
print("⏳ JHER BOT — STARTING... ✅ Beautiful Help UI ✨")
keep_alive()  # ← DITO ILAGAY — BAGO MAG BOT.RUN!
bot.run(BOT_TOKEN)

