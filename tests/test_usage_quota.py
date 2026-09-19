import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from usage_quota import DAILY_SECONDS, DailyQuota, KeychainStore, QuotaError


class MemoryStore:
    def __init__(self):
        self.data = None
        self.fail_write = False

    def read(self):
        return self.data

    def write(self, data):
        if self.fail_write:
            raise QuotaError("storage unavailable")
        self.data = data


class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "usage.lock"
        self.store = MemoryStore()
        self.now = 100 * 86400 + 3600
        self.quota = self.relaunch()

    def relaunch(self):
        return DailyQuota(self.store, self.path, clock=lambda: self.now)

    def test_new_install_and_ten_full_recordings(self):
        self.assertEqual(self.quota.remaining(), DAILY_SECONDS)
        for _ in range(10):
            token, seconds, _ = self.quota.reserve(30)
            self.assertEqual(seconds, 30)
            self.quota.settle(token, 30)
        self.assertEqual(self.relaunch().remaining(), 0)
        with self.assertRaises(QuotaError):
            self.relaunch().reserve(30)

    def test_abandoned_reservation_remains_charged_after_restart(self):
        self.quota.reserve(30)
        self.assertEqual(self.relaunch().remaining(), 270)
        self.relaunch().reserve(30)
        self.assertEqual(self.relaunch().remaining(), 240)

    def test_ordinary_stop_refunds_unused_seconds_once(self):
        token, _, _ = self.quota.reserve(30)
        self.assertEqual(self.quota.settle(token, 5.2), 294)
        self.assertEqual(self.relaunch().settle(token, 0), 294)

    def test_stale_token_cannot_refund_a_later_recording(self):
        old, _, _ = self.quota.reserve(30)
        new, _, _ = self.relaunch().reserve(30)
        self.assertEqual(self.quota.settle(old, 0), 240)
        self.assertEqual(self.quota.settle(new, 10), 260)

    def test_usage_is_capped_at_reservation(self):
        token, _, _ = self.quota.reserve(30)
        self.assertEqual(self.quota.settle(token, 120), 270)

    def test_failed_microphone_can_refund_zero_capture(self):
        token, _, _ = self.quota.reserve(30)
        self.assertEqual(self.quota.settle(token, 0), 300)

    def test_last_few_seconds_are_available(self):
        for _ in range(9):
            self.quota.reserve(30)
        token, _, _ = self.quota.reserve(30)
        self.quota.settle(token, 27)
        _, seconds, remaining = self.quota.reserve(30)
        self.assertEqual((seconds, remaining), (3, 0))

    def test_utc_midnight_resets_and_old_token_cannot_refund_new_day(self):
        old, _, _ = self.quota.reserve(30)
        self.now = 101 * 86400
        self.assertEqual(self.relaunch().remaining(), 300)
        self.relaunch().reserve(30)
        self.assertEqual(self.quota.settle(old, 0), 270)

    def test_clock_rollback_does_not_grant_another_allowance(self):
        self.quota.reserve(30)
        self.now -= 2 * 86400
        self.assertEqual(self.relaunch().remaining(), 270)
        self.now += 86400
        self.assertEqual(self.relaunch().remaining(), 270)

    def test_timezone_settings_do_not_change_utc_reset(self):
        self.quota.reserve(30)
        with patch.dict("os.environ", {"TZ": "Pacific/Kiritimati"}):
            self.assertEqual(self.relaunch().remaining(), 270)

    def test_write_failure_does_not_authorize_recording(self):
        self.store.fail_write = True
        with self.assertRaises(QuotaError):
            self.quota.reserve(30)

    def test_failed_settlement_retains_full_reservation(self):
        token, _, _ = self.quota.reserve(30)
        self.store.fail_write = True
        with self.assertRaises(QuotaError):
            self.quota.settle(token, 1)
        self.store.fail_write = False
        self.assertEqual(self.relaunch().remaining(), 270)

    def test_corrupt_data_is_not_silently_reset(self):
        self.quota.remaining()
        valid = json.loads(self.store.data)
        bad_states = [b"not JSON", b"null", b"{}", b"[]", b"\xff"]
        for field, value in (("used", -1), ("used", 301), ("used", True),
                             ("day", 0), ("last_seen", float("nan")),
                             ("version", 2), ("active", {"id": "x", "seconds": 31})):
            bad_states.append(json.dumps({**valid, field: value}).encode())
        for data in bad_states:
            with self.subTest(data=data):
                self.store.data = data
                with self.assertRaises(QuotaError):
                    self.relaunch().reserve(30)
                self.assertEqual(self.store.data, data)

    def test_invalid_requests_and_times(self):
        for value in (0, -1, 31, True, 1.5):
            with self.assertRaises(ValueError):
                self.quota.reserve(value)
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.quota.settle("unknown", value)

    def test_separate_instances_serialize_reservations(self):
        def reserve(_):
            try:
                self.relaunch().reserve(30)
                return True
            except QuotaError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(reserve, range(20)))
        self.assertEqual(sum(results), 10)
        self.assertEqual(self.quota.remaining(), 0)


class KeychainTests(unittest.TestCase):
    def test_query_is_scoped_to_our_service_and_not_synced(self):
        try:
            import Security as sec
        except ImportError:
            self.skipTest("macOS Security framework not installed")
        query = KeychainStore("com.pstarwars2026.voicedictate.tests").query()
        self.assertEqual(query[sec.kSecAttrService], "com.pstarwars2026.voicedictate.tests")
        self.assertFalse(query[sec.kSecAttrSynchronizable])

    def test_locked_keychain_is_not_treated_as_missing_data(self):
        try:
            import Security as sec
        except ImportError:
            self.skipTest("macOS Security framework not installed")
        with patch.object(sec, "SecItemCopyMatching", return_value=(sec.errSecInteractionNotAllowed, None)):
            with self.assertRaises(QuotaError):
                KeychainStore().read()
