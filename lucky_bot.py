"""
LuckyCheats Discord Bot - Button System
========================================
Sends a message with button in the channel.
User clicks button → receives Free Trial Key via DM.

Setup:
  pip install discord.py requests
  Then: python lucky_bot.py
"""

import discord
from discord.ui import Button, View
import requests
import random
import string
import json
import os
import time

# ─────────────────────────────────────────────
#  ⚙️  CONFIGURATION
# ─────────────────────────────────────────────
BOT_TOKEN    = "MTQ3NzYzMjM1NDQ1NjQzNjc1Nw.GYFqrt.7VJDwHl0p_wx51R5YIXxZPJff33ITF4yI-8iPk"        # ← Enter your token here!
CHANNEL_ID   = 1476024477195436102
BASE_URL     = "http://luckycheats.atwebpages.com/lucky_auth.php"
ADMIN_USER   = "LuckyCheats"
ADMIN_PASS   = "Radman123S"
ADMIN_PIN    = "1390"
SEC_COLOR    = "orange"
SEC_CAR      = "radman"
KEY_DURATION = 3600   # 1 Hour in seconds
USED_FILE    = "used_users.json"
# ─────────────────────────────────────────────

def load_used():
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r") as f:
            return json.load(f)
    return {}

def save_used(data):
    with open(USED_FILE, "w") as f:
        json.dump(data, f)

def generate_key():
    number = random.randint(10000000, 99999999)  # 8 zufällige Zahlen
    return f"LuckyCheats-trial-{number}"

def do_login():
    r = requests.get(BASE_URL, params={"action": "login_step1", "email": ADMIN_USER, "pass": ADMIN_PASS})
    if r.text.strip() != "success":
        print(f"[Login] Step 1 failed: {r.text}")
        return False
    r = requests.get(BASE_URL, params={"action": "login_step2", "email": ADMIN_USER, "code": ADMIN_PIN})
    if r.text.strip() != "success":
        print(f"[Login] Step 2 failed: {r.text}")
        return False
    r = requests.get(BASE_URL, params={"action": "login_step3", "email": ADMIN_USER, "color": SEC_COLOR, "car": SEC_CAR})
    if r.text.strip() != "success":
        print(f"[Login] Step 3 failed: {r.text}")
        return False
    print("[Login] ✅ Admin session active.")
    return True

def ensure_session():
    try:
        r = requests.get(BASE_URL, params={"action": "status", "admin_user": ADMIN_USER})
        data = r.json()
        if data.get("status") == "success" and data.get("session", {}).get("verified"):
            return True
    except Exception:
        pass
    return do_login()

def create_key_on_server(key: str) -> bool:
    r = requests.get(BASE_URL, params={
        "action": "create",
        "key": key,
        "duration": KEY_DURATION,
        "admin_user": ADMIN_USER,
        "admin_key": ADMIN_PASS
    })
    return r.text.strip() == "success"


# ── Button View (persistent – survives bot restart) ──
class KeyButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔑 Get Free Trial Key",
        style=discord.ButtonStyle.green,
        custom_id="get_key_button"
    )
    async def get_key(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        used    = load_used()
        user_id = str(interaction.user.id)

        # ── Has the user already claimed a key? ──
        if user_id in used:
            existing_key = used[user_id]["key"]
            created_at   = used[user_id]["created_at"]
            expire_time  = created_at + KEY_DURATION
            remaining    = int(expire_time - time.time())

            if remaining > 0:
                mins = remaining // 60
                await interaction.followup.send(
                    f"❌ You already claimed a Free Trial Key!\n"
                    f"⏳ It is still valid for **{mins} minutes**.\n"
                    f"Check your **DMs**!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Your Free Trial Key has **expired**.\n"
                    f"You have already used your free trial.",
                    ephemeral=True
                )
            return

        # ── Check session ──
        if not ensure_session():
            await interaction.followup.send("⚠️ Server error. Please contact an admin.", ephemeral=True)
            return

        # ── Create key ──
        new_key = generate_key()
        if not create_key_on_server(new_key):
            await interaction.followup.send("⚠️ Failed to create key. Please try again later.", ephemeral=True)
            return

        # ── Send key via DM ──
        try:
            dm_embed = discord.Embed(
                title="🎉 Your LuckyCheats Free Trial Key",
                color=0x00FF88
            )
            dm_embed.add_field(name="🔑 Key", value=f"```{new_key}```", inline=False)
            dm_embed.add_field(name="⏳ Valid for", value="**1 Hour** starting now", inline=True)
            dm_embed.add_field(name="⚠️ Note", value="Your PC will be bound on first launch (HWID).", inline=False)
            dm_embed.set_footer(text="LuckyCheats • Enjoy!")

            await interaction.user.send(embed=dm_embed)

            used[user_id] = {
                "key": new_key,
                "created_at": int(time.time()),
                "username": str(interaction.user)
            }
            save_used(used)

            await interaction.followup.send(
                "✅ Your Free Trial Key has been sent to your **DMs**! 📬",
                ephemeral=True
            )
            print(f"[Key] ✅ {interaction.user} ({user_id}) → {new_key}")

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ I couldn't send you a DM!\n"
                "Please enable **Allow direct messages from server members** in your settings and try again.",
                ephemeral=True
            )


# ── Bot Setup ──
intents = discord.Intents.all()
client  = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"[Bot] ✅ Logged in as {client.user}")
    ensure_session()

    # Register persistent view (important for restarts!)
    client.add_view(KeyButtonView())

    channel = client.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"[Bot] ❌ Channel {CHANNEL_ID} not found!")
        return

    # Check if button message already exists (prevents duplicates)
    async for msg in channel.history(limit=20):
        if msg.author == client.user and msg.embeds:
            if "Free Trial Key" in (msg.embeds[0].title or ""):
                print("[Bot] ℹ️ Button message already exists.")
                return

    # Send new button message
    embed = discord.Embed(
        title="🔑 Free Trial Key",
        description=(
            "Click the button below to claim your **Free Trial Key**!\n\n"
            "📬 The key will be sent to you via **DM**.\n"
            "⚠️ Each Discord account can only claim **one** Free Trial Key."
        ),
        color=0x00FF88
    )
    embed.set_footer(text="LuckyCheats • Powered by luckycheats.atwebpages.com")

    await channel.send(embed=embed, view=KeyButtonView())
    print("[Bot] ✅ Button message sent!")

client.run(BOT_TOKEN)
