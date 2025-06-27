"""
v2.4.2 与 v2.4.1 没有区别
修复版本显示不一致：统一为v2.4.2
"""

import random
import time
import telebot
import json
import os
import threading
import http.server
import socketserver
from datetime import datetime, timedelta

# 配置 Telegram Bot
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

if not TELEGRAM_TOKEN:
    print("Error: Please set TELEGRAM_BOT_TOKEN environment variable")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 存储文件 - 优先使用数据目录，回退到脚本目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'data')

# 如果数据目录存在，使用数据目录；否则使用脚本目录
if os.path.exists(DATA_DIR):
    CAPSULES_FILE = os.path.join(DATA_DIR, 'time_capsules.json')
    print(f"📁 Using data directory: {DATA_DIR}")
else:
    CAPSULES_FILE = os.path.join(SCRIPT_DIR, 'time_capsules.json')
    print(f"📁 Using script directory: {SCRIPT_DIR}")

# HTTP服务器配置
WEB_PORT = 9000

def load_capsules():
    """Load time capsules"""
    if os.path.exists(CAPSULES_FILE):
        with open(CAPSULES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_capsules(capsules):
    """Save time capsules"""
    with open(CAPSULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(capsules, f, ensure_ascii=False, indent=2)

# 添加HTTP服务器类
class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # 设置服务器根目录为脚本所在目录
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)
    
    def add_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')
    
    def do_GET(self):
        # 处理 time_capsules.json 请求
        if self.path == '/time_capsules.json' or self.path.startswith('/time_capsules.json'):
            try:
                capsules = load_capsules()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.add_cors_headers()
                self.end_headers()
                json_data = json.dumps(capsules, ensure_ascii=False, indent=2)
                self.wfile.write(json_data.encode('utf-8'))
                print(f"📤 Served {len(capsules)} capsules via HTTP")
                return
            except Exception as e:
                print(f"❌ Error serving capsules: {e}")
                self.send_response(500)
                self.add_cors_headers()
                self.end_headers()
                return
        
        # 处理预检请求
        if self.path.endswith('OPTIONS'):
            self.send_response(200)
            self.add_cors_headers()
            self.end_headers()
            return
        
        # 默认页面重定向到index.html
        if self.path == '/':
            self.path = '/index.html'
        
        # 其他请求交给父类处理
        super().do_GET()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.add_cors_headers()
        self.end_headers()
    
    def end_headers(self):
        self.add_cors_headers()
        super().end_headers()

def start_web_server():
    """启动HTTP服务器"""
    try:
        with socketserver.TCPServer(("", WEB_PORT), CORSHTTPRequestHandler) as httpd:
            print(f"🌐 Web server running on port {WEB_PORT}")
            print(f"📁 Serving files from: {SCRIPT_DIR}")
            print(f"🔗 Access at: http://localhost:{WEB_PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"❌ Web server error: {e}")

def add_capsule(message, user_id):
    """Add new time capsule"""
    capsules = load_capsules()
    
    if user_id == ADMIN_CHAT_ID:
        # 管理模式：1-3分钟
        delay_minutes = random.randint(1, 3)
        send_time = datetime.now() + timedelta(minutes=delay_minutes)
        print(f"👑 ADMIN MODE: Capsule will open in {delay_minutes} minutes")
    else:
        # 用户模式：30天-3年
        delay_days = random.randint(30, 1095)
        send_time = datetime.now() + timedelta(days=delay_days)
        print(f"⏰ USER MODE: Capsule will open in {delay_days} days")
    
    capsule = {
        'user_id': user_id,
        'message': message,
        'created_at': datetime.now().isoformat(),
        'send_at': send_time.isoformat(),
        'sent': False,
        'shared': False
    }
    
    capsules.append(capsule)
    save_capsules(capsules)
    
    if user_id == ADMIN_CHAT_ID:
        bot.send_message(chat_id=user_id, 
                        text=f"👑 Admin time capsule buried! Will open in {delay_minutes} minutes.")
    else:
        bot.send_message(chat_id=user_id, 
                        text="⏰ Time capsule buried and will open at an unknown time!")

def ask_for_sharing(user_id, message, original_time):
    """Ask user if they want to share the opened message"""
    markup = telebot.types.InlineKeyboardMarkup()
    share_btn = telebot.types.InlineKeyboardButton("👊🏼 Share with the world", callback_data=f"share_{len(load_capsules())}")
    keep_btn = telebot.types.InlineKeyboardButton("💔 Keep private", callback_data="keep_private")
    markup.add(share_btn)
    markup.add(keep_btn)
    
    bot.send_message(
        chat_id=user_id,
        text="💫 Would you like to share this Time Capsule with others?\n\n"
             "Your Time Capsule will appear anonymously on our public [Time Capsule Wall](https://nothingwall.com).\n"
             "Leave your mark on this world.",
        reply_markup=markup,
        parse_mode='Markdown'
    )

def check_and_send_capsules():
    """Check and send due time capsules"""
    capsules = load_capsules()
    now = datetime.now()
    
    for i, capsule in enumerate(capsules):
        if not capsule['sent']:
            send_time = datetime.fromisoformat(capsule['send_at'])
            if now >= send_time:
                # Send time capsule
                created_date = datetime.fromisoformat(capsule['created_at'])
                
                # 计算相对时间（重用现有逻辑）
                time_ago = now - created_date
                if time_ago.days > 0:
                    time_str = f"{time_ago.days} days ago"
                else:
                    hours = time_ago.seconds // 3600
                    time_str = f"{hours} hours ago"
                
                bot.send_message(
                    chat_id=capsule['user_id'], 
                    text=f"📮 Time capsule opened!\n\nThis is a message from you {time_str}:\n\n「{capsule['message']}」"
                )
                
                capsule['sent'] = True
                
                # Ask if user wants to share
                ask_for_sharing(capsule['user_id'], capsule['message'], capsule['created_at'])
    
    save_capsules(capsules)

# Handle callback queries for sharing
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data.startswith("share_"):
        # Find the message and mark as shared (不再写入shared_messages.json)
        capsules = load_capsules()
        capsule_index = int(call.data.split("_")[1]) - 1
        
        if 0 <= capsule_index < len(capsules):
            capsule = capsules[capsule_index]
            capsule['shared'] = True  # 只标记为shared，不单独存储
            save_capsules(capsules)
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✨ Thank you for sharing your Time Capsule with the world!\n\n"
                     "The World is expecting you!"
            )
        
    elif call.data == "keep_private":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔒 Your message remains private.\n\n"
                 "Sometimes the most precious thoughts are meant for our eyes only."
        )

# Listen to all messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    print(f"Message from {username} ({user_id}): {message.text}")
    
    if message.text == '/status':
        # Show capsule status
        capsules = load_capsules()
        user_capsules = [c for c in capsules if c['user_id'] == user_id]
        pending = len([c for c in user_capsules if not c['sent']])
        sent = len([c for c in user_capsules if c['sent']])
        shared = len([c for c in user_capsules if c.get('shared', False)])
        
        bot.send_message(
            chat_id=user_id, 
            text=f"💡 Your capsules:\n⏳ Waiting: {pending}\n✅ Opened: {sent}\n👊🏼 Shared: {shared}"
        )

    elif message.text == '/wall':
        # Show Time Capsule Wall link
        bot.send_message(
            chat_id=user_id,
            text="💫 Nothing Wall\n\n"
                 "Visit our Nothing Wall to read shared Time Capsules from others:\n\n"
                 "[Nothing Wall ● Time Capsules](https://nothingwall.com)\n\n"
                 "Experience the wisdom floating through time and space!",
            parse_mode='Markdown'
        )
            
    elif message.text == '/help':
        # Show help
        bot.send_message(
            chat_id=user_id,
            text="🕰️ Welcome to Time Capsule Bot!\n\n"
                 "Simply send any message and it will be buried as a Time Capsule.\n"
                 "It will be returned to you at an unknown time.!\n\n"
                 "Commands:\n"
                 "⌛️ /status - Check your Time Capsules\n"
                 "💫 /wall - Read shared Time Capsules from others\n"
                 "❓ /help - Show this help\n\n"
                 "When your Time Capsule opens,\n"
                 "you can choose to share it with the World anonymously! "
        )
    else:
        # Create time capsule for any other message
        add_capsule(message.text, user_id)

# Background thread to check time capsules
def capsule_checker():
    while True:
        try:
            print("Checking time capsules...")
            check_and_send_capsules()
            time.sleep(10)  # Check every 10 seconds for testing
        except Exception as e:
            print(f"Error checking capsules: {e}")
            time.sleep(10)

# 启动服务
print("🕰️ Time Capsule Bot v2.4.2 starting...")
print(f"📁 Capsules stored in: {CAPSULES_FILE}")
print(f"🌐 Web server will start on port {WEB_PORT}")

# 启动Web服务器线程
print("🌐 Starting web server...")
web_thread = threading.Thread(target=start_web_server, daemon=True)
web_thread.start()

# 启动时间胶囊检查线程
checker_thread = threading.Thread(target=capsule_checker, daemon=True)
checker_thread.start()

# Start Bot with error handling and auto-restart
while True:
    try:
        print("🚀 Starting bot polling...")
        bot.polling(none_stop=True, interval=1, timeout=30)
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
        break
    except Exception as e:
        print(f"❌ Bot error: {e}")
        print("🔄 Restarting bot in 5 seconds...")
        time.sleep(5)