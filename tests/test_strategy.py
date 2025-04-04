# File: tests/test_strategy.py

import unittest
from unittest.mock import patch, MagicMock
from strategy import TradeStrategy
from discovery import PairDiscovery
from telegram_notifications import *

class TestTradeStrategy(unittest.TestCase):
    @patch('strategy.kraken')
    @patch('strategy.db')
    def test_place_buy_success(self, mock_db, mock_kraken):
        mock_kraken.get_balance.return_value = {'ZGBP': '1000'}
        mock_kraken.get_ticker.return_value = {'c': [["20000"]]}
        mock_kraken.place_order.return_value = {"result": "success"}

        strategy = TradeStrategy()
        strategy.fetch_latest_price = MagicMock(return_value=20000.0)
        strategy.evaluate_buy_signal = MagicMock(return_value=True)

        strategy.place_buy("BTC/GBP")
        self.assertIn("BTC/GBP", strategy.open_positions)
        mock_db.save_position.assert_called_once()

    @patch('strategy.kraken')
    @patch('strategy.db')
    def test_stop_loss_trigger(self, mock_db, mock_kraken):
        mock_kraken.get_balance.return_value = {'ZGBP': '1000'}
        mock_kraken.get_ticker.return_value = {'c': [["16000"]]}
        mock_kraken.place_order.return_value = {"result": "sold"}

        strategy = TradeStrategy()
        strategy.open_positions = {"BTC/GBP": {"price": 20000.0, "volume": 0.01}}
        strategy.fetch_latest_price = MagicMock(return_value=16000.0)
        strategy.check_stop_loss("BTC/GBP")

        self.assertNotIn("BTC/GBP", strategy.open_positions)
        mock_db.remove_position.assert_called_once()

class TestDiscovery(unittest.TestCase):
    @patch('discovery.kraken')
    @patch('discovery.config')
    @patch('discovery.send_telegram')
    def test_get_eligible_pairs(self, mock_notify, mock_config, mock_kraken):
        mock_config.discovery = {'enabled': True, 'min_volume_24h_gbp': 100000}
        mock_config.strategy = {'excluded_pairs': []}

        mock_kraken.get_tradable_asset_pairs.return_value = {
            'BTC/GBP': {'pair': 'BTC/GBP'},
            'DOGE/GBP': {'pair': 'DOGE/GBP'}
        }
        mock_kraken.get_ticker.side_effect = lambda p: {'v': [None, '10'], 'c': [["10000"]]}

        discovery = PairDiscovery()
        results = discovery.get_eligible_pairs()
        self.assertTrue(any("BTC/GBP" in r for r in results))

class TestNotifier(unittest.TestCase):
    @patch('notifier.requests.post')
    def test_send_telegram_success(self, mock_post):
        mock_post.return_value.ok = True
        result = send_telegram("Test message")
        self.assertTrue(result)

    @patch('notifier.requests.post', side_effect=Exception("fail"))
    def test_send_telegram_failure(self, mock_post):
        result = send_telegram("Test message")
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
