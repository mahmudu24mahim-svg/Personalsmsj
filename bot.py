import telebot
from telebot import types
import sqlite3, requests, time
from datetime import datetime

# ================= BOT CONFIG =================
BOT_TOKEN = "7918956631:AAEXbx0YUFAkuSR_IdFJyCZ7xgkpRjZU6SI"
ADMIN_IDS = [7276206449,6153708648]
ADMIN_CONTACT = "@Unkonwn_BMT"
ADMIN_CONTACTS = "@Wanted_bmt"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ================= DATABASE =================
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
 user_id INTEGER PRIMARY KEY,
 balance INTEGER DEFAULT 2,
 banned INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS stats(
 id INTEGER PRIMARY KEY,
 total_sms INTEGER DEFAULT 0,
 bot_status INTEGER DEFAULT 1
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS sms_log(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER,
 number TEXT,
 message TEXT,
 time TEXT
)
""")

try: cur.execute("ALTER TABLE users ADD COLUMN name TEXT") 
except: pass
try: cur.execute("ALTER TABLE users ADD COLUMN join_date TEXT") 
except: pass
try: cur.execute("ALTER TABLE users ADD COLUMN total_sms INTEGER DEFAULT 0") 
except: pass
db.commit()

cur.execute("INSERT OR IGNORE INTO stats(id,total_sms,bot_status) VALUES(1,0,1)")
db.commit()

# ================= FUNCTIONS =================
def get_user(uid):
    cur.execute("SELECT balance,banned,name,join_date,total_sms FROM users WHERE user_id=?", (uid,))
    r = cur.fetchone()
    if not r:
        now = datetime.now().strftime("%Y-%m-%d")
        cur.execute("INSERT INTO users(user_id,balance,join_date) VALUES(?,?,?)", (uid,2,now))
        db.commit()
        return 2, 0, "", now, 0
    return r

def get_all_users():
    cur.execute("SELECT user_id,name,balance,total_sms,join_date FROM users")
    return cur.fetchall()

def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📨 Send SMS")
    kb.add("💰 Balance","🛒 Buy Balance")
    kb.add("🆘 Support")
    if uid in ADMIN_IDS:
        kb.add("⚙ Admin Panel")
    return kb

def back_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅ Back")
    return kb

def bot_on():
    cur.execute("SELECT bot_status FROM stats WHERE id=1")
    return cur.fetchone()[0]==1

sms_state = {}
broadcast_state = {}

# ================= TELEGRAM HANDLERS =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    bal, ban, name, join_date, total_sms = get_user(uid)
    if ban:
        bot.send_message(m.chat.id,"🚫 You are banned")
        return
    bot.send_message(
        m.chat.id,
        "👋 <b>Welcome to Professional SMS Bot</b>\n\n"
        "✔ Easy & Fast\n✔ Stable & Pro\n✔ 2 Free SMS added",
        reply_markup=main_menu(uid)
    )

# ===== SMS FLOW =====
@bot.message_handler(func=lambda m: m.text=="📨 Send SMS")
def sms_start(m):
    uid = m.from_user.id
    bal, _, _, _, _ = get_user(uid)

    if not bot_on() and uid not in ADMIN_IDS:
        bot.send_message(m.chat.id,"⛔ Bot is OFF")
        return

    if bal<=0:
        bot.send_message(m.chat.id,"❌ Balance finished")
        return

    sms_state[uid] = {"step":"number"}
    bot.send_message(
        m.chat.id,
        "📱 <b>Enter Receiver Mobile Number</b>\nExample: 017XXXXXXXX",
        reply_markup=back_kb()
    )

@bot.message_handler(func=lambda m: m.from_user.id in sms_state)
def sms_flow(m):
    uid = m.from_user.id
    state = sms_state[uid]

    if state["step"]=="number":
        if not m.text.isdigit() or len(m.text)!=11 or not m.text.startswith("01"):
            bot.send_message(m.chat.id,"❌ Invalid number\nEnter 11 digit BD number")
            return
        state["number"]=m.text
        state["step"]="message"
        bot.send_message(m.chat.id,"✍ Enter your message",reply_markup=back_kb())
        return

    if state["step"]=="message":
        msg_text = m.text.strip()
        bot.send_message(m.chat.id,"⏳ Sending SMS...")

        try:
            api_url = f"https://helobuy.shop/csms.php?key=unknown2&number={state['number']}&message={msg_text}"
            r = requests.get(api_url, timeout=10)
            result = r.json()
            
            if result.get('status') == 'success':
                cur.execute("UPDATE users SET balance=balance-1,total_sms=total_sms+1 WHERE user_id=?", (uid,))
                cur.execute("UPDATE stats SET total_sms=total_sms+1 WHERE id=1")
                cur.execute("INSERT INTO sms_log(user_id,number,message,time) VALUES(?,?,?,?)",
                            (uid,state["number"],msg_text,time.ctime()))
                db.commit()
                bot.send_message(m.chat.id,"✅ SMS Sent Successfully")
            else:
                error_msg = result.get('message', 'Unknown error')
                bot.send_message(m.chat.id, f"❌ SMS Failed: {error_msg}")
        except Exception as e:
            bot.send_message(m.chat.id, f"❌ API Error: {str(e)}")

        sms_state.pop(uid, None)
        bot.send_message(m.chat.id,"🏠 Back to Menu",reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text=="⬅ Back")
def back_menu(m):
    sms_state.pop(m.from_user.id, None)
    broadcast_state.pop(m.from_user.id, None)
    bot.send_message(m.chat.id,"🔙 Back to Main Menu",reply_markup=main_menu(m.from_user.id))

# ===== BALANCE =====
@bot.message_handler(func=lambda m:m.text=="💰 Balance")
def balance(m):
    bal,_,_,_,_ = get_user(m.from_user.id)
    cur.execute("SELECT SUM(balance) FROM users")
    total_balance = cur.fetchone()[0]
    bot.send_message(m.chat.id,f"💰 Your Main Balance: {bal} SMS\n\n📊 Total Users Balance In The Bot: {total_balance} SMS")

@bot.message_handler(func=lambda m:m.text=="🛒 Buy Balance")
def buy(m):
    bot.send_message(m.chat.id,f"\n\n40 TK = 100 SMS\n70 TK = 200 SMS\n160 TK = 450 SMS\n230 TK = 600 SMS\n✅ \n\n💳 To Buy balance, contact admin:\n{ADMIN_CONTACTS}")

@bot.message_handler(func=lambda m:m.text=="🆘 Support")
def support(m):
    bot.send_message(m.chat.id,f"🆘 Support Center\n\nFor any help contact:\n{ADMIN_CONTACT}")

# ===== ADMIN PANEL =====
@bot.message_handler(func=lambda m:m.text=="⚙ Admin Panel")
def admin_panel(m):
    if m.from_user.id not in ADMIN_IDS: return
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT total_sms FROM stats WHERE id=1")
    total_sms = cur.fetchone()[0]
    cur.execute("SELECT SUM(balance) FROM users")
    total_balance = cur.fetchone()[0]

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Add Balance","🚫 Ban User","✅ Unban User")
    kb.add("👥 View Users","📣 Broadcast")
    kb.add("📴 Bot OFF","📳 Bot ON")
    kb.add("📊 Stats","⬅ Back")
    bot.send_message(
        m.chat.id,
        f"⚙ <b>Admin Panel</b>\n\n"
        f"👤 Total Users: {total_users}\n"
        f"📨 Total SMS Sent: {total_sms}\n"
        f"💰 Total Balance: {total_balance} SMS",
        reply_markup=kb
    )

# ===== ADMIN ACTIONS =====
@bot.message_handler(func=lambda m:m.text=="➕ Add Balance")
def admin_add_balance(m):
    msg = bot.send_message(m.chat.id,"Enter User ID:")
    bot.register_next_step_handler(msg, admin_add_balance_amt)

def admin_add_balance_amt(m):
    try:
        uid = int(m.text)
        msg = bot.send_message(m.chat.id,"Enter Amount of SMS to Add:")
        bot.register_next_step_handler(msg, lambda x: add_balance_final(x,uid))
    except:
        bot.send_message(m.chat.id,"❌ Invalid ID")

def add_balance_final(m,uid):
    try:
        amt = int(m.text)
        cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt,uid))
        db.commit()
        bot.send_message(m.chat.id,f"✅ Added {amt} SMS to {uid}")
    except:
        bot.send_message(m.chat.id,"❌ Error")

@bot.message_handler(func=lambda m:m.text=="🚫 Ban User")
def admin_ban(m):
    msg = bot.send_message(m.chat.id,"Enter User ID to Ban:")
    bot.register_next_step_handler(msg, lambda x: exec_ban(x))

def exec_ban(m):
    cur.execute("UPDATE users SET banned=1 WHERE user_id=?", (int(m.text),))
    db.commit()
    bot.send_message(m.chat.id,"🚫 User Banned")

@bot.message_handler(func=lambda m:m.text=="✅ Unban User")
def admin_unban(m):
    msg = bot.send_message(m.chat.id,"Enter User ID to Unban:")
    bot.register_next_step_handler(msg, lambda x: exec_unban(x))

def exec_unban(m):
    cur.execute("UPDATE users SET banned=0 WHERE user_id=?", (int(m.text),))
    db.commit()
    bot.send_message(m.chat.id,"✅ User Unbanned")

@bot.message_handler(func=lambda m:m.text=="📴 Bot OFF")
def bot_off(m):
    cur.execute("UPDATE stats SET bot_status=0 WHERE id=1")
    db.commit()
    bot.send_message(m.chat.id,"❌ Bot is now OFF")

@bot.message_handler(func=lambda m:m.text=="📳 Bot ON")
def bot_on_cmd(m):
    cur.execute("UPDATE stats SET bot_status=1 WHERE id=1")
    db.commit()
    bot.send_message(m.chat.id,"✅ Bot is now ON")

@bot.message_handler(func=lambda m:m.text=="📊 Stats")
def admin_stats(m):
    cur.execute("SELECT COUNT(*),SUM(balance) FROM users")
    total_users, total_bal = cur.fetchone()
    cur.execute("SELECT total_sms FROM stats WHERE id=1")
    total_sms = cur.fetchone()[0]
    bot.send_message(m.chat.id,
                     f"📊 <b>Bot Stats</b>\n\n"
                     f"👤 Total Users: {total_users}\n"
                     f"💰 Total Balance: {total_bal} SMS\n"
                     f"📨 Total SMS Sent: {total_sms}"
                     )

@bot.message_handler(func=lambda m:m.text=="👥 View Users")
def view_users(m):
    users = get_all_users()
    text = "<b>All Users:</b>\n\n"
    for u in users:
        text += f"ID: {u[0]} | Balance: {u[2]} | SMS Sent: {u[3]} | Join: {u[4]}\n"
    bot.send_message(m.chat.id,text)

@bot.message_handler(func=lambda m:m.text=="📣 Broadcast")
def start_broadcast(m):
    broadcast_state[m.from_user.id] = True
    bot.send_message(m.chat.id,"📝 Enter the message to broadcast to all users:")

@bot.message_handler(func=lambda m:m.text and m.from_user.id in broadcast_state)
def broadcast_message(m):
    msg = m.text
    users = get_all_users()
    sent = 0
    for u in users:
        try:
            bot.send_message(u[0], msg)
            sent += 1
        except:
            continue
    bot.send_message(m.chat.id,f"✅ Broadcast sent to {sent} users")
    broadcast_state.pop(m.from_user.id)

# ================= FLASK FOR LIFETIME PING =================
from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "Bot is running ✅"

def run():
    app.run(host="0.0.0.0", port=8080)

# Flask app in a separate thread
t = Thread(target=run)
t.start()

# ================= START TELEGRAM BOT =================
print("Bot running...")
bot.infinity_polling()
