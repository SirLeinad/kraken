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
    with open("logs/commands.log", "a") as f:
        f.write(f"{datetime.now().isoformat()} :: {text}\n")

    if text == "/help":
        help_text = (
            "📘 Available commands:\n"
            "/help – Show this help menu\n"
            "/start – Show bot is running\n"
            "/shutdown – Gracefully stop the bot\n"
            "/reload – Restart the bot process\n"
            "/pause – Pause AI trading\n"
            "/resume – Resume AI trading\n"
            "/threshold 0.85 – Set AI signal cutoff\n"
            "/balance – Show current asset balances\n"
            "/buy – Force execute strategy once\n"
            "/convert USD 100 – Convert to GBP or EUR\n"
            "/discovered – Show ML-picked trade pairs\n"
            "/positions – Show active positions with P&L\n"
            "/recent – Show last 5 trades\n"
            "/config – View current config settings\n"
            "/summary – Show today's P&L and open positions\n"
            "/graph – Export P&L graph (PNG)\n"
            "/set model vX – Set AI model version\n"
            "/auditlog – See the auditlog\n"

        )
        send_telegram(help_text)

    elif text == "/start":
        send_telegram("✅ Kraken AI Bot is running.")
        notify(f"{USER}: Kraken AI Bot is active.", key="bot", priority="low")

    elif text == "/shutdown":
        send_telegram("👋 Shutting down bot...")
        notify(f"{USER}: 🔻 Shutdown triggered.", key="bot", priority="high")
        exit(0)

    elif text == "/auditlog":
        try:
            lines = Path("logs/commands.log").read_text().splitlines()[-10:]
            send_telegram("📝 Last commands:\n" + "\n".join(lines))
        except:
            send_telegram("⚠️ No audit log available.")

    elif text.startswith("/set model "):
        model = text.split()[-1]
        config.set("model_version", model)
        send_telegram(f"📦 Switched model version to {model}")

    elif text == "/graph":
        try:
            from export_graph import plot_profit_graph
            path = plot_profit_graph()
            files = {'document': open(path, 'rb')}
            requests.post(f"{BASE_URL}/sendDocument", data={"chat_id": CHAT_ID}, files=files)
        except Exception as e:
            send_telegram(f"❌ Graph export failed: {e}")

    elif text == "/config":
        try:
            import json
            with open("config.json") as f:
                cfg = json.load(f)
            formatted = json.dumps(cfg, indent=2)
            send_telegram(f"🛠️ Current config:\n<pre>{formatted}</pre>", parse_mode="HTML")
        except Exception as e:
            send_telegram(f"❌ Failed to read config: {e}")

    elif text == "/recent":
        try:
            from pathlib import Path
            import json

            path = Path("data/trade_history.json")
            if not path.exists():
                send_telegram("⚠️ No trade history yet.")
            else:
                lines = path.read_text().strip().splitlines()[-5:]
                trades = [json.loads(line) for line in lines]
                msg = "📈 Recent Trades:\n" + "\n\n".join(
                    f"{t['timestamp'][:16]} {t['pair']} {t['action'].upper()} @ £{t['entry_price']} → £{t['exit_price']} (P&L: £{t['pnl']:+.2f})"
                    for t in trades
                )
                send_telegram(msg)
        except Exception as e:
            send_telegram(f"❌ Failed to load trade history: {e}")

    elif text == "/summary":
        try:
            from strategy import TradeStrategy
            from logger import load_trade_history

            strategy = STRATEGY  # assumes global instance
            balances = strategy.balance
            open_pos = strategy.open_positions
            trades = load_trade_history(limit=50)

            total_pnl = sum(t["pnl"] for t in trades if "pnl" in t)
            today_trades = [
                t for t in trades
                if "timestamp" in t and t["timestamp"].startswith(datetime.utcnow().strftime("%Y-%m-%d"))
            ]
            today_pnl = sum(t["pnl"] for t in today_trades)

            msg = f"📊 Summary Report\n"
            msg += f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}\n"
            msg += f"Today's P&L: £{today_pnl:.2f}\n"
            msg += f"Total P&L (last 50): £{total_pnl:.2f}\n"
            msg += f"Open Positions: {len(open_pos)}\n\n"

            for pair, pos in open_pos.items():
                msg += f"{pair}: {pos['volume']} @ £{pos['price']:.2f}\n"

            send_telegram(msg)
        except Exception as e:
            send_telegram(f"❌ Failed to generate summary: {e}")

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
            from_cur = parts[1].upper()
            amount = float(parts[2])
            to_cur = parts[3].upper() if len(parts) > 3 else "GBP"

            pair = from_cur + to_cur if from_cur + to_cur in kraken.assets else to_cur + from_cur
            ticker = kraken.get_ticker(pair)
            rate = float(ticker["c"].iloc[0][0])

            converted = amount * rate if pair.startswith(from_cur) else amount / rate
            send_telegram(f"💱 {amount} {from_cur} = {converted:.2f} {to_cur}")
        except Exception as e:
            send_telegram(f"❌ Usage: /convert USD 100 EUR\n{e}")
            
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
