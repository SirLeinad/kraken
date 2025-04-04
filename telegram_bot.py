# File: telegram_bot.py

import requests
import time
import logging
from config import Config
from strategy import TradeStrategy
from telegram_notifications import notify

config = Config()
USER = config.user
BOT_TOKEN = config.telegram['bot_token']
CHAT_ID = config.telegram['chat_id']
STRATEGY = TradeStrategy()

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
logging.basicConfig(level=logging.INFO)

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        resp = requests.get(url, params=params, timeout=60)
        return resp.json()
    except Exception as e:
        logging.error(f"Error fetching updates: {e}")
        return {}

def handle_command(text):
    if text == "/balance":
        balance = STRATEGY.balance
        formatted = "\n".join(f"{k}: {v}" for k, v in balance.items())
        requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": "✅ Done."})
        notify(f"{USER}: \U0001F4B0 Balance:\n{formatted}", key="bot", priority="medium")

    elif text == "/buy":
        STRATEGY.execute()
        requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": "✅ Done."})
        notify(f"{USER}: \u2705 Strategy executed manually.", key="bot", priority="medium")

    elif text == "/start":
        requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": "✅ Done."})
        notify(f"{USER}: Kraken AI Bot is already running.", key="bot", priority="low")

    elif text == "/reload":
        requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": "✅ Done."})
        notify(f"{USER}: \u267B Reload triggered.", key="bot", priority="high")
        import os, sys
        os.execv(sys.executable, [sys.executable] + sys.argv)

    else:
        requests.post(f"{BASE_URL}/sendMessage", data={"chat_id": CHAT_ID, "text": "✅ Done."})
        notify(f"{USER}: Unknown command '{text}'", key="bot", priority="low")

def main():
    logging.info("Starting Telegram bot loop...")
    offset = None
    while True:
        updates = get_updates(offset)
        if "result" in updates:
            for update in updates["result"]:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                text = message.get("text")

                if chat_id != CHAT_ID:
                    logging.warning(f"Unauthorized access attempt from chat_id: {chat_id}")
                    continue
                if not text:
                    continue
                logging.info(f"Command received: {text}")
                handle_command(text)

        time.sleep(2)

if __name__ == "__main__":
    main()
