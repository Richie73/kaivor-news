"""Focused regression tests for FP018.2 finance endpoints; no network access."""
import unittest
from unittest.mock import patch
import main

class FinanceApiTests(unittest.TestCase):
    def setUp(self):
        self.client = main.app.test_client()
        with main._cache_lock:
            main._finance_cache["data"] = {"Gold": 3000.0}
            main._finance_cache["last_updated"] = 1000.0
        with main._finance_refresh_lock:
            main._finance_refresh_state.update({"running": False, "started_at": 0.0, "last_completed": 0.0, "last_error": "", "last_updated_keys": []})

    def test_ticker_has_legacy_and_freshness_fields(self):
        response = self.client.get('/api/ticker')
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['ticker']['Gold'], 3000.0)
        self.assertIn('last_updated', payload)
        self.assertIn('age_seconds', payload)
        self.assertIn('refresh', payload)

    def test_refresh_returns_202_and_starts_worker(self):
        with patch.object(main.threading, 'Thread') as thread:
            response = self.client.post('/api/finance/refresh')
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.get_json()['status'], 'started')
            thread.return_value.start.assert_called_once()
        with main._finance_refresh_lock:
            main._finance_refresh_state['running'] = False

    def test_refresh_does_not_start_duplicate(self):
        with main._finance_refresh_lock:
            main._finance_refresh_state['running'] = True
        with patch.object(main.threading, 'Thread') as thread:
            response = self.client.post('/api/finance/refresh')
            self.assertEqual(response.status_code, 202)
            self.assertEqual(response.get_json()['status'], 'running')
            thread.assert_not_called()
        with main._finance_refresh_lock:
            main._finance_refresh_state['running'] = False

if __name__ == '__main__':
    unittest.main()
