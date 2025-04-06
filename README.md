# 🧠 Kraken AI Trading Bot (Chat-Optimized Readme)

This repo contains a self-adaptive AI-driven trading bot that uses a discovery pipeline, model inference, strategy execution, and paper/live trading logic. This README is written **for AI agents/chat systems** to understand and support the codebase across sessions.

---

## 🔧 Core Purpose

- Periodically scans Kraken pairs via `PairDiscovery` if `discovery.enabled == true`
- Selects eligible pairs using volatility, volume, and model-based confidence scoring
- Allocates weights and executes buy/sell decisions
- Supports paper trading and live margin trading with configurable leverage
- Sends all trade activity to Telegram
- Saves and reloads position/trade history for persistent state

---

## 📁 File Overview

| File                  | Purpose                                                                 |
|-----------------------|-------------------------------------------------------------------------|
| `strategy.py`         | Main bot logic: handles entry/exit conditions, order placement, logging |
| `discovery.py`        | Discovers tradable pairs using historical volatility and AI scoring     |
| `kraken_api.py`       | Wrapper for interacting with Kraken's REST API                          |
| `train_pipeline.py`   | Trains new ML models using historical data                              |
| `ai_model.py`         | Uses trained models to generate confidence scores                       |
| `config.py`           | Loads nested config from JSON into dot-path access                      |
| `notifier.py`         | Sends Telegram alerts                                                   |
| `db.py` / `database.py` | SQLite wrapper for storing open positions and trades                   |
| `precheck.py`         | Validates environment, config, model, DB, and Kraken access             |
| `run_check.py`        | Same as precheck but focused on production health check                 |

---

## 🔑 Critical Config Keys (from `config.json`)

| Key                              | Purpose                                                                 |
|----------------------------------|-------------------------------------------------------------------------|
| `strategy.pair_trade_cooldown_sec` | Cooldown timer before re-trading the same pair                        |
| `discovery.enabled`             | Whether to run pair discovery or just use focus pairs                  |
| `discovery.min_volume_24h_gbp`  | Filters out low-volume pairs                                           |
| `discovery.max_active_pairs`    | Max number of pairs AI can auto-trade (excludes `focus_pairs`)         |
| `strategy.initial_budget_gbp`   | Used to track net PnL                                                  |
| `strategy.exit_below_ai_score`  | Exit position if AI confidence drops below this                        |
| `strategy.stop_loss_pct` / `take_profit_pct` | Used for dynamic thresholds                               |

---

## 🔁 Loop Flow Summary

1. Run `precheck.py` to validate everything
2. `main.py` instantiates `TradeStrategy`
3. Strategy:
   - Loads discovered + focus pairs
   - Checks stop-loss, take-profit, AI-score
   - Executes trades (paper/live)
   - Logs and notifies outcome
4. Pair discovery runs every `discovery.interval_hours`
5. Trades are saved in `data/trade_history.json`

---

## 📦 Notes for AI Agents

- Kraken rate limits cause errors like `'result'` — always guard `place_order()` and never assume response format.
- `sell_order_notification()` expects `result` to always be a dict.
- `log_trade_profit()` must run in all branches.
- Discovery can be disabled in config (`discovery.enabled = false`) and `focus_pairs` will still trade.
- Errors are logged but won't crash loop thanks to aggressive try/except guards.
- `PAPER_MODE` toggles in code — not set via CLI/env yet.
- Fallback models/logic should be added if ML fails to return scores.

---

## 🧪 Testing / Preflight

- `python precheck.py`: environment + config + DB
- `python run_check.py`: health check
- Run with logs via: `systemctl status kraken-ai-bot.service -f`

---

## 🧠 Final Notes

This repo is in active development. Previous AI sessions have implemented:
- Config-driven thresholds
- Telegram alerting
- Stop-loss + take-profit logic
- Trade history tracking
- Rate-limit-safe error recovery

Please maintain defensive programming:
- Don't assume config keys exist — always use `config.get()`
- Don’t assume API responses are successful — check for `.get('error')`
- Always guard use of `result`

