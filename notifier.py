# File: notifier.py

print("[DEBUG] Loaded notifier.py")

import requests
from config import Config

config = Config()

def send_telegram(msg):
    try:
        bot_token = config.get("telegram.bot_token")
        chat_id = config.get("telegram.chat_id")
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"📢 {msg}",
            "parse_mode": "HTML"
        }
        r = requests.post(url, data=payload, timeout=10)
        return r.ok
    except Exception as e:
        print(f"[!] Telegram notify failed: {e}")
        return False
