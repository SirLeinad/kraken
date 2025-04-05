
# Kraken AI Bot – Development Roadmap

## ✅ 1. Telegram Bot
- [x] Command routing working (/help, /buy, /convert, etc.)
- [x] `/config` to view live values
- [ ] Command audit log

## ✅ 2. ML Discovery Pipeline
- [x] `discovery.py` calls pipeline correctly
- [x] Validate `(pair, score)` from backtest
- [x] Timestamp `discovered_pairs.json`
- [x] Interval-based discovery enforcement
- [x] Store `model_version` in discovery file

## ✅ 3. Trade Execution
- [x] Multi-currency support (GBP/USD/EUR)
- [x] FX conversion with proper volume
- [x] Enforce `max_open_positions`
- [ ] Risk buckets per asset group (GBP-heavy focus)
- [x] Position sizing by confidence or volatility

## ⚠️ 4. Backtesting & AI
- [ ] Log metrics on `train_model_from_backtest.py`
- [x] Save model to `model_vX.pkl`
- [ ] Self-learning loop (trade → train)
- [ ] Confidence score decay logic

## ❗ 5. Strategy Logic
- [x] Focus pairs fallback works
- [ ] Consider volatility/spread dynamically
- [ ] Dynamic `buy_allocation_pct`, `stop_loss_pct`

## 📦 Suggestions To Improve

### Critical (High ROI)
- [x] `last_updated` in `discovered_pairs.json`
- [x] `max_open_positions`
- [ ] Confidence thresholding / decay
- [ ] `exit_below_ai_score` enforcement (implemented)

### Advanced ML
- [ ] Store trade outcomes + learn from them
- [ ] Confidence score evolution
- [ ] Signal blending (ML + MACD/RSI)

### Analytics & Reporting
- [x] `/recent` trades (5 most recent)
- [ ] `/summary today` showing today's P&L
- [ ] Cron-based Telegram reports
- [ ] CSV P&L export and PNG graph
