# File: strategy.py

import os
import json
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
from time import sleep, time
from collections import defaultdict
from datetime import datetime, timedelta
from logger import log_trade_result

config = Config()
kraken = KrakenClient()
db = Database()

FOCUS_PAIRS = config.get("trading_rules.focus_pairs")
STOP_LOSS = config.get('strategy.stop_loss_pct')
EXCLUDED = config.get("trading_rules.excluded_pairs")
USER = config.get("user")
PAPER_MODE = config.get("paper_trading")
MARGIN_ENABLED = config.get('margin.enabled', False)
LEVERAGE_BY_PAIR = config.get('margin.leverage_by_pair', {})
TAKE_PROFIT = config.get("strategy.take_profit_pct", 0.05)
EXIT_AI_SCORE = config.get("strategy.exit_below_ai_score", 0.3)
BUY_ALLOCATION_PCT = config.get("strategy.buy_allocation_pct", 0.2)
SCORE_HISTORY_FILE = "logs/ai_scores_history.json"

class TradeStrategy:
    def __init__(self):
        self.balance = kraken.get_balance()
        self.open_positions = db.load_positions()
        self.ai_scores = defaultdict(float)
        self.last_pair_trade_time = {}  # pair: timestamp
        self.pair_trade_cooldown = config.get("pair_trade_cooldown_sec", 3600)
        self.discovery_path = Path("data/discovered_pairs.json")
        self.discovery_interval = config.get("discovery.interval_hours", 4)
        self.trade_history_path = Path("data/trade_history.json")
        self.trade_history_archive_dir = Path("data/trade_history_archive")
        self.trade_history = self.load_trade_history()

        try:
            with open("data/discovered_pairs.json") as f:
                self.discovered_data = json.load(f)
            self.model_version = self.discovered_data.get("model_version", "unknown")
            self.discovered_pairs = {
                pair for pair, score in self.discovered_data.get("pairs", {}).items()
                if score >= config.get("min_confidence", 0.8)
            }
        except Exception as e:
            print(f"[WARN] Couldn't load discovered pairs: {e}")
            self.model_version = "unknown"
            self.discovered_pairs = set()
            self.discovered_data = {}

        self.focus_pairs = set(FOCUS_PAIRS) | self.discovered_pairs
        print(f"[STRATEGY] Pairs to evaluate: {sorted(self.focus_pairs)}")

        if self.should_refresh_discovery():
            from discovery import PairDiscovery
            discovery = PairDiscovery()
            discovery.get_eligible_pairs()
            print("[DISCOVERY] Discovery refreshed due to interval.")


        # Auto-clean stale paper trades if switching to live
        if not PAPER_MODE:
            db.clear_all_positions()
            self.open_positions = {}
            print("[INFO] Cleared all old paper positions on live start.")

    def convert_to_gbp(self, pair: str, value: float, kraken) -> float:
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

    def should_refresh_discovery(self) -> bool:
        if not self.discovery_path.exists():
            return True
        try:
            with self.discovery_path.open() as f:
                data = json.load(f)
                ts = data.get("last_updated")
                if not ts:
                    return True
                last_time = datetime.fromisoformat(ts)
                return (datetime.utcnow() - last_time) > timedelta(hours=self.discovery_interval)
        except Exception as e:
            print(f"[DISCOVERY] Timestamp check failed: {e}")
            return True

    def log_trade_profit(self, pair, entry_price, exit_price, volume, reason):
        if entry_price is None:
            print(f"[WARN] Missing entry price for {pair}. Skipping gain calc.")
            return

        raw_gain = (exit_price - entry_price) * volume
        gain = self.convert_to_gbp(pair, raw_gain, kraken)

        with open("logs/profit_log.csv", "a") as f:
            f.write(f"{datetime.utcnow()},{pair},{entry_price},{exit_price},{volume},{gain:.4f},{reason}\n")

        log_trade_result(
            pair=pair,
            action="buy",
            volume=vol,
            entry_price=entry,
            exit_price=exit,
            pnl=exit - entry,
            model=self.model_version,
            confidence=self.ai_scores.get(pair)
        )

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
        return score > config.get('strategy.bull_threshold')

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
        now = time.time()
        gbp_balance = float(self.balance.get('ZGBP', 0.0)) - used_gbp
        if gbp_balance <= 10:
            notify(f"{USER}: Not enough GBP to trade {pair}. Remaining: £{gbp_balance:.2f}", key=f"nogbp_{pair}", priority="medium")
            return used_gbp

        last_time = self.last_pair_trade_time.get(pair)
        if last_time and (now - last_time) < self.pair_trade_cooldown:
            notify(f"{USER}: Skipping {pair} — trade cooldown active.", key=f"cooldown_{pair}", priority="low")
            return used_gbp


        price = self.fetch_latest_price(pair)
        confidence = self.ai_scores.get(pair, 0.5)
        confidence = max(0.3, min(confidence, 0.95))  # clamp to range

        scaling_factor = (confidence - 0.3) / (0.95 - 0.3)  # map to 0–1 scale
        alloc_pct = config.get("strategy.buy_allocation_pct", 0.10)
        alloc_gbp = gbp_balance * (alloc_pct + scaling_factor * alloc_pct)

        print(f"[ALLOCATION] {pair} score={confidence:.2f} → allocation: {alloc_gbp:.2f}")
        alloc_quote = self.gbp_to_quote(pair, alloc_gbp, self.kraken)
        MAX_PAIR_EXPOSURE_GBP = 100  # e.g. allow max £100 exposure per pair

        vol = round(alloc_quote / price, 6)
        leverage = LEVERAGE_BY_PAIR.get(pair.upper()) if MARGIN_ENABLED else None

        existing_vol = self.open_positions.get(pair, {}).get("volume", 0)
        max_vol = (MAX_PAIR_EXPOSURE_GBP / price)

        if len(self.open_positions) >= config.get("strategy.max_open_positions", 4):
            notify(f"{USER}: Max open positions reached. Skipping {pair}.", key=f"maxpos_{pair}", priority="medium")
            return used_gbp

        if PAPER_MODE:
            self.open_positions[pair] = {'price': price, 'volume': vol}
            db.save_position(pair, price, vol)
            notify_trade_summary(USER, pair, action="buy", vol=vol, price=price, paper=PAPER_MODE)
            meta = {"model": self.model_version, "confidence": self.ai_scores.get(pair)}
            log_trade(pair, "buy", vol, price, meta=meta)
        else:
            result = kraken.place_order(pair, side="buy", volume=vol, leverage=leverage)
            self.open_positions[pair] = {'price': price, 'volume': vol}
            db.save_position(pair, price, vol)
            notify_trade_summary(USER, pair, action="buy", vol=vol, price=price, paper=PAPER_MODE)
            meta = {"model": self.model_version, "confidence": self.ai_scores.get(pair)}
            log_trade(pair, "buy", vol, price, meta=meta)
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

        stop_loss_pct, take_profit_pct = self.get_dynamic_thresholds(pair)
        if (price - entry_price) / entry_price <= -stop_loss_pct:
            notify(f"{USER}: 🔻 Stop-loss hit for {pair}. Selling...", priority="high")
            self.place_sell(pair, reason="stop_loss")
        elif (price - entry_price) / entry_price >= take_profit_pct:
            notify(f"{USER}: 🟢 Take-profit hit for {pair}. Selling...", priority="high")
            self.place_sell(pair, reason="take_profit")
        elif ai_score and ai_score < EXIT_BELOW_AI_SCORE:
            notify(f"{USER}: ⚠️ AI confidence dropped below threshold for {pair}. Selling...", priority="medium")
            self.place_sell(pair, reason="low_ai_conf")


        if should_exit:
            if PAPER_MODE:
                log_trade(pair, "sell", vol, current_price)
                paper_sell_notification(USER, pair, vol, current_price, reason, priority="high")
                self.log_trade_profit(pair, entry_price, current_price, vol, reason)
            else:
                leverage = LEVERAGE_BY_PAIR.get(pair.upper()) if MARGIN_ENABLED else None
                result = kraken.place_order(pair, side="sell", volume=vol, leverage=leverage, reduce_only=bool(leverage))
                log_trade(pair, "sell", vol, current_price)
                sell_order_notification(USER, pair, vol, current_price, reason, result, priority="high")
                self.log_trade_profit(pair, entry_price, current_price, vol, reason)
            del self.open_positions[pair]
            db.remove_position(pair)

            self.trade_history[pair] = {
                "pnl": round((current_price - entry_price) * vol, 6),
                "timestamp": datetime.utcnow().isoformat(),
                "confidence": self.ai_scores.get(pair),
                "model_version": self.model_version
            }
            self.save_trade_history()


    def get_dynamic_thresholds(self, pair):
        try:
            df = KrakenClient.get_price_history(pair)
            vol = df["close"].pct_change().std()
            if vol is None:
                raise ValueError("No volatility")

            stop_loss = min(0.03, vol * 2.0)  # e.g. 2× stddev
            take_profit = max(0.04, vol * 3.0)  # slightly more

            return stop_loss, take_profit
        except:
            return config.get("strategy.stop_loss_pct", 0.02), config.get("strategy.take_profit_pct", 0.05)

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

    def load_trade_history(self):
        if self.trade_history_path.exists():
            try:
                with self.trade_history_path.open() as f:
                    return json.load(f)
            except:
                print("[WARN] Failed to load trade history.")
        return {}

    def save_trade_history(self):
        try:
            self.archive_trade_history_if_old()
            with self.trade_history_path.open("w") as f:
                json.dump(self.trade_history, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save trade history: {e}")

    def archive_trade_history_if_old(self):
        if not self.trade_history_path.exists():
            return

        mtime = datetime.utcfromtimestamp(self.trade_history_path.stat().st_mtime)
        if (datetime.utcnow() - mtime).days < 7:
            return

        self.trade_history_archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        archive_path = self.trade_history_archive_dir / f"trade_history_{ts}.json"
        self.trade_history_path.rename(archive_path)
        print(f"[ARCHIVE] Archived old trade history to {archive_path}")

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

        confidence = self.ai_scores.get(pair)
        last_trade = self.trade_history.get(pair, {})
        last_pnl = last_trade.get("pnl", 0)

        if confidence and last_pnl < 0:
            adjusted_conf = confidence * 0.9  # decay 10% if previous trade lost money
            print(f"[DECAY] Adjusted confidence for {pair}: {confidence:.2f} → {adjusted_conf:.2f}")
            confidence = adjusted_conf

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
            balance = kraken.get_balance()

            # AI Top Score Summary
            top_scores = sorted(self.ai_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            top_txt = "\n".join(f"{p}: {s:.4f}" for p, s in top_scores)
            report.append("\n🧠 Top AI Scores:\n" + top_txt)
            if any("✅ Buy" in r or "SELL" in r for r in report):
                trade_report_notification(USER, report)
            
            if config.get("strategy.hourly_pl_report", True) and self.open_positions:
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
