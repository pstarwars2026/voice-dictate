"""Serverless daily allowance. Reservation-first accounting survives process exits.

UTC days avoid time-zone-based resets. This resists ordinary restart bypasses,
not deliberate clock advances, Keychain deletion, or source modification.
"""

from contextlib import contextmanager
import fcntl
import json
import math
from pathlib import Path
import threading
import time
import uuid

DAILY_SECONDS = 300
CLIP_SECONDS = 30
SERVICE = "com.pstarwars2026.voicedictate.free-usage"


class QuotaError(RuntimeError):
    pass


class KeychainStore:
    def __init__(self, service=SERVICE):
        self.service = service

    def query(self):
        import Security as sec
        return {sec.kSecClass: sec.kSecClassGenericPassword,
                sec.kSecAttrService: self.service, sec.kSecAttrAccount: "daily-usage-v1",
                sec.kSecAttrSynchronizable: False}

    def read(self):
        import Security as sec
        query = self.query()
        query.update({sec.kSecReturnData: True, sec.kSecMatchLimit: sec.kSecMatchLimitOne})
        status, data = sec.SecItemCopyMatching(query, None)
        if status == sec.errSecItemNotFound:
            return None
        if status != sec.errSecSuccess:
            raise QuotaError("Cannot read daily allowance from Keychain. Unlock Keychain and retry.")
        return bytes(data)

    def write(self, data):
        import Security as sec
        from Foundation import NSData
        value = NSData.dataWithBytes_length_(data, len(data))
        status = sec.SecItemUpdate(self.query(), {sec.kSecValueData: value})
        if status == sec.errSecItemNotFound:
            query = self.query()
            query[sec.kSecValueData] = value
            status, _ = sec.SecItemAdd(query, None)
        if status != sec.errSecSuccess:
            raise QuotaError("Cannot save daily allowance to Keychain. Recording has not been authorized.")


class DailyQuota:
    def __init__(self, store, lock_path, clock=time.time):
        self.store = store
        self.lock_path = Path(lock_path)
        self.clock = clock
        self.thread_lock = threading.RLock()

    @contextmanager
    def locked(self):
        with self.thread_lock:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            with self.lock_path.open("a+") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def load(self):
        now = self.clock()
        if not math.isfinite(now) or now < 0:
            raise QuotaError("System time is unavailable. Check your clock.")
        raw = self.store.read()
        if raw is None:
            return {"version": 1, "day": int(now // 86400), "last_seen": now,
                    "used": 0, "active": None}
        try:
            state = json.loads(raw)
            if not isinstance(state, dict) or set(state) != {"version", "day", "last_seen", "used", "active"}:
                raise ValueError()
            if type(state["version"]) is not int or state["version"] != 1:
                raise ValueError()
            if type(state["day"]) is not int or state["day"] < 0:
                raise ValueError()
            if type(state["used"]) is not int or not 0 <= state["used"] <= DAILY_SECONDS:
                raise ValueError()
            seen = state["last_seen"]
            if type(seen) not in (int, float) or not math.isfinite(seen) or seen < 0:
                raise ValueError()
            if state["day"] != int(seen // 86400):
                raise ValueError()
            active = state["active"]
            if active is not None:
                if not isinstance(active, dict) or set(active) != {"id", "seconds"}:
                    raise ValueError()
                if not isinstance(active["id"], str) or not active["id"]:
                    raise ValueError()
                if type(active["seconds"]) is not int or not 1 <= active["seconds"] <= min(CLIP_SECONDS, state["used"]):
                    raise ValueError()
        except (ValueError, TypeError, KeyError, UnicodeError, OverflowError) as error:
            raise QuotaError("Daily allowance data is invalid; it has not been reset.") from error
        effective = max(now, state["last_seen"])
        day = int(effective // 86400)
        if day > state["day"]:
            state.update(day=day, used=0, active=None)
        state["last_seen"] = effective
        return state

    def save(self, state):
        self.store.write(json.dumps(state, allow_nan=False).encode("utf-8"))

    def remaining(self):
        with self.locked():
            state = self.load()
            self.save(state)
            return DAILY_SECONDS - state["used"]

    def reserve(self, requested):
        if type(requested) is not int or not 1 <= requested <= CLIP_SECONDS:
            raise ValueError("Recording limit must be 1 to 30 seconds")
        with self.locked():
            state = self.load()
            seconds = min(requested, DAILY_SECONDS - state["used"])
            if seconds <= 0:
                self.save(state)
                raise QuotaError("Free daily allowance used. Resets at 00:00 UTC.")
            token = str(uuid.uuid4())
            # Any abandoned reservation remains charged; do not refund on relaunch.
            state["active"] = {"id": token, "seconds": seconds}
            state["used"] += seconds
            self.save(state)
            return token, seconds, DAILY_SECONDS - state["used"]

    def settle(self, token, elapsed):
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("Elapsed time must be finite and nonnegative")
        with self.locked():
            state = self.load()
            active = state["active"]
            if active is not None and active["id"] == token:
                charged = min(active["seconds"], math.ceil(elapsed))
                state["used"] -= active["seconds"] - charged
                state["active"] = None
            self.save(state)
            return DAILY_SECONDS - state["used"]
