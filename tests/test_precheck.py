# File: tests/test_precheck.py

import unittest
from unittest.mock import patch, MagicMock
import precheck

class TestPrecheck(unittest.TestCase):

    @patch("precheck.os.environ.get")
    def test_conda_env_check(self, mock_env):
        mock_env.return_value = "myenv"
        self.assertTrue(precheck.check_conda_env())

    @patch("precheck.torch.cuda.is_available")
    @patch("precheck.torch.cuda.get_device_name")
    def test_gpu_check(self, mock_name, mock_available):
        mock_available.return_value = True
        mock_name.return_value = "Tesla P4"
        self.assertEqual(precheck.check_gpu(), "Tesla P4")

    def test_talib_check(self):
        self.assertTrue(precheck.check_talib())

    @patch("precheck.krakenex.API")
    def test_kraken_api_check(self, mock_api):
        mock_instance = mock_api.return_value
        mock_instance.query_private.return_value = {"error": []}
        result = precheck.check_kraken_api("key", "secret")
        self.assertTrue(result)

    @patch("precheck.requests.get")
    def test_telegram_check_success(self, mock_get):
        mock_get.return_value.status_code = 200
        result = precheck.check_telegram("bot_token", "chat_id")
        self.assertTrue(result)

    @patch("precheck.requests.get", side_effect=Exception("fail"))
    def test_telegram_check_fail(self, mock_get):
        result = precheck.check_telegram("bot_token", "chat_id")
        self.assertFalse(result)

    def test_sqlite_check(self):
        self.assertTrue(precheck.check_sqlite())

if __name__ == '__main__':
    unittest.main()
