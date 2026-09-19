#!/usr/bin/env python3
"""Exercise a real Keychain counter across abrupt process termination.

Uses only an isolated, uniquely named test item, which is removed afterward.
Never reads or changes the production usage counter.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from usage_quota import DailyQuota, KeychainStore

PREFIX = "com.pstarwars2026.voicedictate.tests."


def run():
    if len(sys.argv) == 4:
        service, lock_path, action = sys.argv[1:]
        if not service.startswith(PREFIX):
            raise ValueError("Only isolated test services are allowed")
        quota = DailyQuota(KeychainStore(service), lock_path, clock=lambda: 100 * 86400)
        if action == "crash":
            quota.reserve(30)
            os._exit(0)
        if action != "read":
            raise ValueError("Unknown test action")
        print(quota.remaining())
        return

    import Security as sec
    service = PREFIX + str(uuid.uuid4())
    store = KeychainStore(service)
    try:
        with tempfile.TemporaryDirectory() as root:
            command = [sys.executable, str(Path(__file__).resolve()), service, str(Path(root) / "usage.lock")]
            subprocess.run([*command, "crash"], check=True, timeout=30)
            first = subprocess.check_output([*command, "read"], text=True, timeout=30).strip()
            second = subprocess.check_output([*command, "read"], text=True, timeout=30).strip()
            if first != "270" or second != "270":
                raise AssertionError("Usage did not survive separate process launches")
            print(json.dumps({"isolated_keychain": True, "abrupt_exit_charged_seconds": 30,
                              "remaining_after_two_relaunches": 270, "passed": True}))
    finally:
        status = sec.SecItemDelete(store.query())
        if status not in (sec.errSecSuccess, sec.errSecItemNotFound):
            raise RuntimeError(f"Could not remove isolated test Keychain item: {service} ({status})")


if __name__ == "__main__":
    run()
