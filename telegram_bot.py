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
    if text == "/help":
        help_text = (
            "📘 Available commands:\n"
            "/help – Show this help menu\n"
            "/start – Show bot is running\n"
            "/shutdown – Gracefully stop the bot\n"
            "/reload – Restart the bot process\n"
            "/balance – Show current asset balances\n"
            "/buy – Force execute strategy once\n"
            "/convert USD 100 – Convert to GBP\n"
            "/discovered – Show AI-picked trade pairs\n"
            "/summary – Show open positions\n"
        )
        send_telegram(help_text)

    elif text == "/start":
        send_telegram("✅ Kraken AI Bot is running.")
        notify(f"{USER}: Kraken AI Bot is active.", key="bot", priority="low")

    elif text == "/shutdown":
        send_telegram("👋 Shutting down bot...")
        notify(f"{USER}: 🔻 Shutdown triggered.", key="bot", priority="high")
        exit(0)

    elif text == "/reload":
        send_telegram("♻️ Reloading...")
        notify(f"{USER}: ♻️ Reload triggered.", key="bot", priority="high")
        import os, sys
        os.execv(sys.executable, [sys.executable] + sys.argv)

    elif text == "/balance":
        balance = STRATEGY.balance
        formatted = "\n".join(f"{k}: {v}" for k, v in balance.items())
        send_telegram(f"💰 Balance:\n{formatted}")

    elif text == "/buy":
        STRATEGY.execute()
        send_telegram("✅ Strategy executed manually.")
        notify(f"{USER}: ✅ Strategy executed by /buy.", key="bot", priority="medium")

    elif text == "/pause":
        config.set("bot_enabled", False)
        send_telegram("⏸️ Bot paused.")
        notify(f"{USER}: Bot paused via /pause", key="bot", priority="high")

    elif text == "/resume":
        config.set("bot_enabled", True)
        send_telegram("▶️ Bot resumed.")
        notify(f"{USER}: Bot resumed via /resume", key="bot", priority="high")

    elif text == "/positions":
        msg = ["📊 Open Positions:"]
        for pair, pos in STRATEGY.open_positions.items():
            entry = pos['price']
            volume = pos['volume']
            curr = STRATEGY.fetch_latest_price(pair)
            raw_gain = (curr - entry) * volume
            gbp_gain = STRATEGY.convert_to_gbp(pair, raw_gain, kraken)
            msg.append(f"{pair}: {volume} @ £{entry:.2f} → £{curr:.2f} (P&L: £{gbp_gain:+.2f})")
        send_telegram("\n".join(msg) if len(msg) > 1 else "No open positions.")

    elif text.startswith("/threshold "):
        try:
            value = float(text.split()[1])
            if 0 <= value <= 1:
                config.set("min_confidence", value)
                send_telegram(f"📈 Confidence threshold set to {value:.2f}")
            else:
                send_telegram("❌ Must be between 0.0 and 1.0")
        except:
            send_telegram("❌ Usage: /threshold 0.85")


    elif text == "/discovered":
        try:
            with open("data/discovered_pairs.json") as f:
                pairs = json.load(f)
            if pairs:
                msg = "🤖 Discovered pairs:\n" + "\n".join(
                    f"• {pair}: {score:.2f}" for pair, score in pairs.items()
                )
            else:
                msg = "⚠️ No discovered pairs currently."
        except Exception as e:
            msg = f"❌ Failed to load discovered pairs: {e}"
        send_telegram(msg)

    elif text.startswith("/convert "):
        try:
            parts = text.split()
            currency, amount = parts[1].upper(), float(parts[2])
            fx_pair = currency + "GBP"
            ticker = kraken.get_ticker(fx_pair)
            rate = float(ticker["c"].iloc[0][0])
            result = amount * rate
            send_telegram(f"💱 {amount} {currency} = £{result:.2f}")
        except Exception as e:
            send_telegram(f"❌ Conversion failed: {e}")

    elif text == "/summary":
        summary = []
        for pair, pos in STRATEGY.open_positions.items():
            p = pos['price']
            v = pos['volume']
            total = round(p * v, 2)
            summary.append(f"{pair}: {v} @ £{p:.2f} = £{total:.2f}")
        msg = "📊 Open Positions:\n" + ("\n".join(summary) if summary else "No active trades.")
        send_telegram(msg)

    else:
        send_telegram(f"❓ Unknown command: {text}")

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
