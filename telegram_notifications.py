# File: telegram_notifications.py

#print("[DEBUG] Loaded telegram_notifications.py")

import time
import sys
from database import Database
from notifier import send_telegram
from config import Config

db = Database()
config = Config()

INTERVALS = config.get("telegram_intervals") or {}
MEDIUM_INTERVAL = float(INTERVALS.get("medium_sec", 1800))  # default 30 min
LOW_INTERVAL = float(INTERVALS.get("low_sec", 3600))        # default 1 hour
last_sent = {}

def notify(msg: str, key: str = None, priority: str = "medium"):
    notify_enabled = config.get("telegram_enabled", default=True)
    if not notify_enabled:
        print(f'[TELEGRAM] Skipped or failed: {msg}')
        return False

    now = time.time()
    if key:
        try:
            last = float(db.get_state(f"last_sent_{key}") or 0)
        except Exception as e:
            print(f"[WARN] Invalid last_sent_{key} value: {e}")
            last = 0.0

        if priority == "high":
            pass  # always send
        elif priority == "medium" and now - last < MEDIUM_INTERVAL:
            print(f'[TELEGRAM] Skipped or failed: {msg}')
            return False
        elif priority == "low" and now - last < LOW_INTERVAL:
            print(f'[TELEGRAM] Skipped or failed: {msg}')
            return False
        db.set_state(f"last_sent_{key}", now)

    try:
        # Suppress if last send failure was < 10 minutes ago
        last_fail = db.get_state("last_notify_failure")
        if last_fail and (time.time() - float(last_fail)) < 600:
            print("[TELEGRAM] Skipping due to recent send failure.")
            return False
        success = send_telegram(msg)
        print(f"[TELEGRAM] Sent: {msg}" if success else f"[TELEGRAM] FAILED to send: {msg}")
        return success
    except Exception as e:
        import traceback
        print(f"[TELEGRAM] EXCEPTION: {e}\n" + traceback.format_exc())
        db.set_state("last_notify_failure", time.time())
        return False

# --- Notification Types ---

def sell_order_notification(user, pair, vol, price, reason, result):
    msg = f"{user}: 🔻 SELL {pair}: {vol} @ £{price:.2f} ({reason}). Order: {result}"
    return notify(msg, key=f"sell_{pair}", priority="high")

def paper_sell_notification(user, pair, vol, price, reason):
    msg = f"{user}: 🧪 Paper SELL {vol} {pair} at £{price:.2f} ({reason})"
    return notify(msg, key=f"paper_sell_{pair}", priority="high")

def notify_trade_summary(user, pair, action, vol, price, reason=None, paper=False):
    label = "🧪 Paper" if paper else "✅ Live"
    reason_txt = f" ({reason})" if reason else ""
    msg = f"{user}: {label} {action.upper()} {pair} {vol} @ £{price:.2f}{reason_txt}"
    return notify(msg, key=f"{action}_{pair}", priority="high")

def buy_order_notification(user, pair, vol, price, result=None, paper=False, gbp_equivalent=None):
    label = "📝 Paper BUY" if paper else "📈 Bought"
    gbp_text = f" (~£{gbp_equivalent:.2f})" if gbp_equivalent else ""
    msg = f"{user}: {label} {vol} {pair} @ £{price:.2f}{gbp_text}"
    if result:
        msg += f" Order: {result}"
    return notify(msg, key=f"buy_{pair}", priority="high")

def ai_score_notification(user, pair, score):
    msg = f"{user}: 🤖 AI Score {pair} = {score:.3f}"
    return notify(msg, key=f"ai_{pair}", priority="high")

def discovery_update_notification(user, added, removed):
    lines = []
    if added:
        lines.append(f"🆕 Discovered: {', '.join(added)}")
    if removed:
        lines.append(f"🗑 Removed: {', '.join(removed)}")
    msg = f"{user}: 🔍 Discovery update:\n" + "\n".join(lines)
    return notify(msg, key="discovery", priority="low")

def trade_report_notification(user, report_lines):
    msg = f"{user}: Trade report:\n" + "\n".join(report_lines)
    return notify(msg, key="report", priority="low")

def hourly_pl_notification(user, report_lines):
    """
    Sends a throttled hourly P&L update once every LOW_INTERVAL,
    using 'hourly_pnl' as the rate-limiting key.
    """
    msg = f"{user}: 📊 Hourly P&L Report:\n" + "\n".join(report_lines)
    return notify(msg, key="hourly_pnl", priority="low")

def notify_startup(user):
    return notify(f"{user}: Kraken AI Bot started. Live trading enabled.", key="startup", priority="high")

def notify_error(user, error):
    return notify(f"{user}: Bot error occurred: {error}", key="error", priority="medium")

def notify_balance(user, lines):
    return notify(f"{user}: 💰 Balance Snapshot:\n" + "\n".join(lines), key="balance", priority="high")
    