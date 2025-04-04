# File: tests/test_main.py

import unittest
from unittest.mock import patch, MagicMock
import main

class TestMain(unittest.TestCase):

    @patch("main.discovery")
    @patch("main.strategy")
    @patch("main.send_telegram")
    def test_run_bot_loop_once(self, mock_notify, mock_strategy, mock_discovery):
        # Patch time to simulate single iteration
        with patch("main.time") as mock_time:
            mock_time.time.side_effect = [0, 14401]  # simulate elapsed > 4h
            mock_time.sleep = MagicMock()

            # Force loop break by overriding while True
            with patch("builtins.__import__", side_effect=KeyboardInterrupt):
                try:
                    main.run_bot()
                except KeyboardInterrupt:
                    pass

        mock_notify.assert_any_call("Daniel: Kraken AI Bot started. Live trading enabled.")
        mock_strategy.execute.assert_called_once()
        mock_discovery.suggest_new_pairs.assert_called_once()

if __name__ == '__main__':
    unittest.main()
