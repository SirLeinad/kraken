# File: kraken_api.py

import krakenex
from pykrakenapi import KrakenAPI
from config import Config
import warnings
import time
import threading
import requests
import pandas as pd

PUBLIC_CALL_INTERVAL = 1.1
_last_public_call = 0
_lock = threading.Lock()
config = Config()

warnings.filterwarnings("ignore", message="'T' is deprecated")

class KrakenClient:
    def __init__(self):
        self.api = krakenex.API(
            key=config.get('kraken.api_key'),
            secret=config.get('kraken.api_secret')
        )
        self.k = KrakenAPI(self.api)

    def _rate_limit(self):
        global _last_public_call
        with _lock:
            now = time.time()
            diff = now - _last_public_call
            if diff < PUBLIC_CALL_INTERVAL:
                wait = PUBLIC_CALL_INTERVAL - diff
                time.sleep(wait)
            _last_public_call = time.time()

    def get_trade_balance(self, asset="ZUSD"):
        return self.api.query_private("TradeBalance", {"asset": asset})

    def get_balance(self):
        response = self.api.query_private('Balance')
        return response['result']

    def get_all_balances(self):
        try:
            spot = self.k.get_account_balance()
        except Exception:
            spot = {}
        try:
            margin_gbp = self.api.query_private("TradeBalance", {"asset": "ZGBP"})
            margin_usd = self.api.query_private("TradeBalance", {"asset": "ZUSD"})
            margin_eur = self.api.query_private("TradeBalance", {"asset": "ZEUR"})
        except Exception:
            margin_gbp, margin_usd, margin_eur = {}, {}, {}

        return {
            "spot": spot,
            "margin": {
                "ZGBP": float(margin_gbp.get("eb", 0)),
                "ZUSD": float(margin_usd.get("eb", 0)),
                "ZEUR": float(margin_usd.get("eb", 0))
            }
        }

    @staticmethod
    def get_price_history(pair: str, interval: int = 60, since: int = None) -> pd.DataFrame:
        url = "https://api.kraken.com/0/public/OHLC"
        params = {"pair": pair, "interval": interval}
        if since:
            params["since"] = since

        response = requests.get(url, params=params)
        data = response.json()

        if not data.get("result"):
            raise ValueError("Invalid response from Kraken")

        key = next(k for k in data["result"] if k != "last")
        ohlcv = data["result"][key]

        df = pd.DataFrame(ohlcv, columns=["time", "open", "high", "low", "close", "vwap", "volume", "count"])
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})

        return df

    def get_ticker(self, pair):
        self._rate_limit()
        return self.k.get_ticker_information(pair)

    def get_ohlc(self, pair, interval=60):
        self._rate_limit()
        ohlc, _ = self.k.get_ohlc_data(pair, interval=interval)
        return ohlc

    def get_tradable_asset_pairs(self):
        self._rate_limit()
        return self.k.get_tradable_asset_pairs()

    def get_recent_trades(self, pair):
        self._rate_limit()
        trades, _ = self.k.get_recent_trades(pair)
        return trades

    def get_ohlcv(self, pair, interval=1, since=None):
        url = "https://api.kraken.com/0/public/OHLC"
        params = {"pair": pair, "interval": interval}
        if since:
            params["since"] = since
        resp = requests.get(url, params=params).json()
        data = resp["result"]
        for key in data:
            if key != "last":
                df = pd.DataFrame(data[key],
                    columns=["timestamp", "open", "high", "low", "close", "vwap", "volume", "count"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
                df.set_index("timestamp", inplace=True)
                return df[["open", "high", "low", "close", "volume", "count"]]

    def place_order(self, pair, side, volume, ordertype="market", leverage=None, reduce_only=False):
        order = {
            'pair': pair,
            'type': side,
            'ordertype': ordertype,
            'volume': str(volume),
        }
        if leverage:
            order['leverage'] = str(leverage)
        if reduce_only:
            order['oflags'] = 'reduceonly'

        return self.api.query_private('AddOrder', order)

    def convert_currency(self, from_cur, to_cur, volume):
        pair = f"{from_cur}/{to_cur}"
        return self.place_order(pair, "buy", volume)

# Usage:
# kraken = KrakenClient()
# print(kraken.get_balance())