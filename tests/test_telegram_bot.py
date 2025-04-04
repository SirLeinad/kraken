# File: tests/test_telegram_bot.py

import unittest
from unittest.mock import patch, MagicMock
import telegram_bot

class TestTelegramBot(unittest.TestCase):

    @patch("telegram_bot.send_telegram")
    @patch("telegram_bot.STRATEGY")
    def test_handle_command_balance(self, mock_strategy, mock_notify):
        mock_strategy.balance = {"ZGBP": 500, "XXBT": 0.01}
        telegram_bot.handle_command("/balance")
        mock_notify.assert_called_once()

    @patch("telegram_bot.send_telegram")
    @patch("telegram_bot.STRATEGY")
    def test_handle_command_buy(self, mock_strategy, mock_notify):
        telegram_bot.handle_command("/buy")
        mock_strategy.execute.assert_called_once()
        mock_notify.assert_called_once()

    @patch("telegram_bot.send_telegram")
    def test_handle_command_start(self, mock_notify):
        telegram_bot.handle_command("/start")
        mock_notify.assert_called_once_with("Daniel: Kraken AI Bot is already running.")

    @patch("telegram_bot.send_telegram")
    def test_handle_command_unknown(self, mock_notify):
        telegram_bot.handle_command("/unknown")
        mock_notify.assert_called_once_with("Daniel: Unknown command: /unknown")

if __name__ == '__main__':
    unittest.main()
