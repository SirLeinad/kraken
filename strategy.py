# File: strategy.py

import pandas as pd
from kraken_api import KrakenClient
from config import Config
from telegram_notifications import *
from database import Database
from exporter import log_trade
from ai_model import calculate_confidence
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from time import sleep
from collections import defaultdict
import os
import json
import os

config = Config()
kraken = KrakenClient()
db = Database()

FOCUS_PAIRS = config.strategy['focus_pairs']
STOP_LOSS = config.strategy['stop_loss_pct']
EXCLUDED = set(config.strategy['excluded_pairs'])
USER = config.user
PAPER_MODE = config.paper_trading
MARGIN_ENABLED = config.margin.get('enabled', False)
LEVERAGE_BY_PAIR = config.margin.get('leverage_by_pair', {})
TAKE_PROFIT = config.strategy.get("take_profit_pct", 0.05)
EXIT_AI_SCORE = config.strategy.get("exit_below_ai_score", 0.3)
BUY_ALLOCATION_PCT = config.strategy.get("buy_allocation_pct", 0.2)
SCORE_HISTORY_FILE = "logs/ai_scores_history.json"

class TradeStrategy:
    def __init__(self):
        self.balance = kraken.get_balance()
        self.open_positions = db.load_positions()
        self.ai_scores = defaultdict(float)
        self.last_pair_trade_time = {}  # pair: timestamp
        self.pair_trade_cooldown = config.get("pair_trade_cooldown_sec", 3600)

        try:
            with open("data/discovered_pairs.json") as f:
                discovered = json.load(f)
                self.discovered_pairs = {
                    pair for pair, score in discovered.items()
                    if score >= 0.8  # or whatever confidence threshold you want
                }
        except Exception as e:
            print(f"[WARN] Couldn't load discovered pairs: {e}")
            self.discovered_pairs = set()

        self.focus_pairs = set(FOCUS_PAIRS) | self.discovered_pairs
        print(f"[STRATEGY] Pairs to evaluate: {sorted(self.focus_pairs)}")

        # Auto-clean stale paper trades if switching to live
        if not PAPER_MODE:
            db.clear_all_positions()
            self.open_positions = {}
            print("[INFO] Cleared all old paper positions on live start.")

    def convert_to_gbp(pair: str, value: float, kraken) -> float:
        """
        Converts value from pair's quote currency to GBP.
        Only needed if pair isn't already in GBP.
        """
        if pair.endswith("GBP"):
            return value
        quote = pair[-3:]
        conversion_pair = quote + "GBP"  # e.g. USDGBP or EURGBP
        try:
            ticker = kraken.get_ticker(conversion_pair)
            rate = float(ticker["c"].iloc[0][0])
            return value * rate
        except Exception as e:
            print(f"[FX] Failed to convert {value} {quote} to GBP: {e}")
            return value  # fallback to raw

    def gbp_to_quote(self, pair: str, gbp_amount: float, kraken) -> float:
        """
        Converts a GBP amount to the pair's quote currency (e.g., USD, EUR) using latest FX rate.
        If pair ends in GBP, returns unchanged.
        """
        quote = pair[-3:]
        if quote == "GBP":
            return gbp_amount

        fx_pair = quote + "GBP"
        try:
            ticker = kraken.get_ticker(fx_pair)
            rate = float(ticker["c"].iloc[0][0])
            return gbp_amount / rate
        except Exception as e:
            print(f"[FX] Failed to convert {gbp_amount} GBP to {quote}: {e}")
            return gbp_amount  # fallback

    def log_trade_profit(self, pair, entry_price, exit_price, volume, reason):
        if entry_price is None:
            print(f"[WARN] Missing entry price for {pair}. Skipping gain calc.")
            return

        raw_gain = (exit_price - entry_price) * volume
        gain = self.convert_to_gbp(pair, raw_gain, kraken)

        with open("logs/profit_log.csv", "a") as f:
            f.write(f"{datetime.utcnow()},{pair},{entry_price},{exit_price},{volume},{gain:.4f},{reason}\n")

    def load_discovered_pairs(self):
        path = Path("data/discovered_pairs.json")
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    return set(data) if isinstance(data, list) else set()
            except Exception as e:
                print(f"[WARN] Failed to load discovered pairs: {e}")
                return set()
        return set()

        self.discovered_pairs = self.load_discovered_pairs()
        self.validate_open_positions()

    def validate_open_positions(self):
        valid_positions = {}
        for pair, data in self.open_positions.items():
            try:
                price = self.fetch_latest_price(pair)
                if price > 0 and data['volume'] > 0:
                    valid_positions[pair] = data
            except Exception as e:
                print(f"[WARN] Position validation failed for {pair}: {e}")
        self.open_positions = valid_positions

    def eligible_pairs(self):
        return [p for p in (set(FOCUS_PAIRS) | self.discovered_pairs) if p not in EXCLUDED]
        return [p for p in (set(FOCUS_PAIRS) | self.discovered_pairs) if p not in EXCLUDED]
        return [p for p in FOCUS_PAIRS if p not in EXCLUDED]

    def fetch_latest_price(self, pair):
        try:
            ticker = kraken.get_ticker(pair)
            return float(ticker['c'].iloc[0][0])
        except Exception as e:
            print(f"[ERROR] fetch_latest_price({pair}): {e}")
            return None

    def evaluate_buy_signal(self, pair):
        score = calculate_confidence(pair)
        self.ai_scores[pair] = score
        db_log = f"AI_SCORE|{pair}|{score:.4f}"
        with open("logs/ai_scores.log", "a") as f:
            f.write(f"{db_log}\n")
        return score > config.strategy['bull_threshold']

    def store_top_ai_scores(self):
        top_scores = sorted(self.ai_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        timestamp = datetime.utcnow().isoformat()
        record = {"timestamp": timestamp, "scores": [{"pair": p, "score": s} for p, s in top_scores]}
        os.makedirs("logs", exist_ok=True)
        if os.path.exists(SCORE_HISTORY_FILE):
            with open(SCORE_HISTORY_FILE, "r") as f:
                history = json.load(f)
        else:
            history = []
            history.append(record)
        with open(SCORE_HISTORY_FILE, "w") as f:
            json.dump(history[-100:], f, indent=2)

    def place_buy(self, pair, used_gbp):
        gbp_balance = float(self.balance.get('ZGBP', 0.0)) - used_gbp
        if gbp_balance <= 10:
            notify(f"{USER}: Not enough GBP to trade {pair}. Remaining: £{gbp_balance:.2f}", key=f"nogbp_{pair}", priority="medium")
            return used_gbp

        last_time = self.last_pair_trade_time.get(pair)
        now = time.time()

        if last_time and (now - last_time) < self.pair_trade_cooldown:
            notify(f"{USER}: Skipping {pair} — trade cooldown active.", key=f"cooldown_{pair}", priority="low")
            return used_gbp


        price = self.fetch_latest_price(pair)
        alloc_gbp = gbp_balance * BUY_ALLOCATION_PCT
        alloc_quote = self.gbp_to_quote(pair, alloc_gbp, self.kraken)
        MAX_PAIR_EXPOSURE_GBP = 100  # e.g. allow max £100 exposure per pair

        vol = round(alloc_quote / price, 6)
        leverage = LEVERAGE_BY_PAIR.get(pair.upper()) if MARGIN_ENABLED else None

        existing_vol = self.open_positions.get(pair, {}).get("volume", 0)
        max_vol = (MAX_PAIR_EXPOSURE_GBP / price)

        if existing_vol >= max_vol:
            notify(f"{USER}: Already holding enough {pair}. Skipping buy.", key=f"skip_{pair}", priority="medium")
            return used_gbp

        if PAPER_MODE:
            self.open_positions[pair] = {'price': price, 'volume': vol}
            db.save_position(pair, price, vol)
            log_trade(pair, "buy", vol, price)
            buy_order_notification(USER, pair, vol, price, leverage, paper=True, gbp_equivalent=alloc_gbp)
        else:
            result = kraken.place_order(pair, side="buy", volume=vol, leverage=leverage)
            self.open_positions[pair] = {'price': price, 'volume': vol}
            db.save_position(pair, price, vol)
            log_trade(pair, "buy", vol, price)
            buy_order_notification(USER, pair, vol, price, leverage, result, gbp_equivalent=alloc_gbp)
            self.last_pair_trade_time[pair] = time.time()
            return used_gbp + alloc_gbp

    def check_stop_loss(self, pair):
        if pair not in self.open_positions:
            return

        try:
            current_price = self.fetch_latest_price(pair)
        except Exception as e:
            print(f"[ERROR] Failed to fetch price for {pair}: {e}")
            return

        entry_price = self.open_positions[pair]['price']
        vol = self.open_positions[pair]['volume']

        if entry_price is None or current_price is None:
            print(f"[WARN] Skipping stop-loss check for {pair} due to missing price.")
            return

        if entry_price is None:
            print(f"[WARN] Missing entry price for {pair}. Skipping gain_pct calc.")
            return
        
        if entry_price is None or entry_price == 0:
            print(f"[WARN] Missing or invalid entry price for {pair}. Skipping gain_pct calc.")
            return
        gain_pct = (current_price - entry_price) / entry_price
        loss_pct = -gain_pct
        should_exit = False
        reason = ""

        if loss_pct >= STOP_LOSS:
            should_exit = True
            reason = "stop-loss"
        elif gain_pct >= TAKE_PROFIT:
            should_exit = True
            reason = "take-profit"
        else:
            score = calculate_confidence(pair)
            if score < EXIT_AI_SCORE:
                should_exit = True
                reason = f"AI-score low ({score:.3f})"

        if should_exit:
            if PAPER_MODE:
                log_trade(pair, "sell", vol, current_price)
                paper_sell_notification(USER, pair, vol, current_price, reason, priority="high")
                self.log_trade_profit(pair, entry_price, current_price, vol, reason)
            else:
                #changed
                leverage = LEVERAGE_BY_PAIR.get(pair.upper()) if MARGIN_ENABLED else None
                result = kraken.place_order(pair, side="sell", volume=vol, leverage=leverage, reduce_only=bool(leverage))
                log_trade(pair, "sell", vol, current_price)
                sell_order_notification(USER, pair, vol, current_price, reason, result, priority="high")
                self.log_trade_profit(pair, entry_price, current_price, vol, reason)
            del self.open_positions[pair]
            db.remove_position(pair)

    def execute(self):
        print('[STRATEGY] Starting trade checks...')
        used_gbp = 0.0
        report = []
        for pair in self.eligible_pairs():
            try:
                print(f'[CHECK] Evaluating stop-loss for {pair}')
                self.check_stop_loss(pair)
                if self.evaluate_buy_signal(pair):
                    used_gbp = self.place_buy(pair, used_gbp)
                    report.append(f"✅ Buy: {pair}")
                else:
                    report.append(f"⏸ No signal: {pair}")  # suppressed for cleaner summary
            except Exception as e:
                report.append(f"❌ Error {pair}: {e}")

        if report:
            all_bal = kraken.get_all_balances()
            spot = all_bal['spot']
            gbp_spot = float(spot.loc['ZGBP']['vol']) if 'ZGBP' in spot.index else 0.0
            usd_spot = float(spot.loc['ZUSD']['vol']) if 'ZUSD' in spot.index else 0.0
            eur_spot = float(spot.loc['ZEUR']['vol']) if 'ZEUR' in spot.index else 0.0
            gbp_margin = all_bal['margin']['ZGBP']
            usd_margin = all_bal['margin']['ZUSD']
            eur_margin = all_bal['margin']['ZEUR']

            report.append(f"\n💰 GBP:   £{gbp_spot:>8.2f} (spot) / £{gbp_margin:>8.2f} (margin)")
            report.append(f"💵 USD:   ${usd_spot:>8.2f} (spot) / ${usd_margin:>8.2f} (margin)")
            report.append(f"💶 EUR:   €{eur_spot:>8.2f} (spot) / €{eur_margin:>8.2f} (margin)")
            # Inject live balance snapshot
            balance = kraken.get_balance()

            # AI Top Score Summary
            top_scores = sorted(self.ai_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            top_txt = "\n".join(f"{p}: {s:.4f}" for p, s in top_scores)
            report.append("\n🧠 Top AI Scores:\n" + top_txt)
            if any("✅ Buy" in r or "SELL" in r for r in report):
                trade_report_notification(USER, report)
            
            if config.strategy.get("hourly_pl_report", True) and self.open_positions:
                pl_lines = []
                net_gain = 0.0
                for pair, pos in self.open_positions.items():
                    current_price = self.fetch_latest_price(pair)
                    gain = (current_price - pos['price']) * pos['volume']
                    net_gain += gain
                    emoji = "🟢" if gain >= 0 else "🔻"
                    pl_lines.append(f"{emoji} {pair}: {gain:+.2f} GBP")
                pl_lines.append(f"Total P&L: {net_gain:+.2f} GBP")
                hourly_pl_notification(USER, pl_lines)
                
            self.store_top_ai_scores()

def send_daily_summary(self):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    rows = db.get_all_trades()
    daily_trades = [r for r in rows if r['timestamp'].startswith(today)]

    buy_count = sum(1 for r in daily_trades if r['type'] == 'buy')
    sell_count = sum(1 for r in daily_trades if r['type'] == 'sell')
    profit = 0.0

    for r in daily_trades:
        if r['type'] == 'sell':
            entry_price = db.get_entry_price(r['pair'])
            if entry_price:
                profit += (r['price'] - entry_price) * r['volume'] if entry_price is not None else 0

    lines = [
        f"📅 Daily Summary ({today})",
        f"Total Trades: {buy_count} buy / {sell_count} sell",
        f"Realized P&L: £{profit:.2f}"
    ]

    if self.open_positions:
        lines.append("\n📌 Open Positions:")
        for pair, pos in self.open_positions.items():
            try:
                current_price = self.fetch_latest_price(pair)
                gain = (current_price - pos['price']) * pos['volume']
                emoji = "🟢" if gain >= 0 else "🔻"
                lines.append(f"{emoji} {pair}: {gain:+.2f} GBP")
            except:
                continue

    notify(f"{USER}:\n" + "\n".join(lines), key="daily_summary", priority="low")
