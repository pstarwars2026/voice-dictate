#!/usr/bin/env python3
"""
Voice Dictate Doctor
====================
Quick environment diagnostics for Voice Dictate without loading the model.

The doctor is intentionally lightweight: it can run before setup completes,
then point users at the exact macOS permission or dependency step to fix.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Iterable


REQUIRED_MODULES = (
    "mlx_vlm",
    "jinja2",
    "rumps",
    "pynput",
    "sounddevice",
    "pyperclip",
    "numpy",
    "ApplicationServices",
    "Security",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    fix: str = ""


def status(ok: bool, warning: bool = False) -> str:
    if ok:
        return "ok"
    return "warn" if warning else "fail"


def check_macos() -> CheckResult:
    system = platform.system()
    version = platform.mac_ver()[0] if system == "Darwin" else platform.release()
    ok = system == "Darwin"
    return CheckResult(
        "macOS",
        status(ok),
        f"{system} {version}".strip(),
        "" if ok else "Voice Dictate currently targets macOS menubar and permission APIs.",
    )


def check_architecture() -> CheckResult:
    machine = platform.machine()
    ok = machine == "arm64"
    return CheckResult(
        "Apple Silicon",
        status(ok),
        machine or "unknown",
        "" if ok else "Run on an M-series Mac; MLX acceleration requires Apple Silicon.",
    )


def check_python_version() -> CheckResult:
    version = sys.version_info
    ok = version >= (3, 10)
    text = f"{version.major}.{version.minor}.{version.micro}"
    return CheckResult(
        "Python",
        status(ok),
        text,
        "" if ok else "Install Python 3.10 or newer, then rerun ./setup.sh.",
    )


def check_venv(repo_root: str) -> CheckResult:
    venv_python = os.path.join(repo_root, ".venv", "bin", "python")
    ok = os.path.exists(venv_python)
    active = os.path.realpath(sys.executable) == os.path.realpath(venv_python) if ok else False
    detail = "created" if ok else "missing"
    if active:
        detail += ", active"
    return CheckResult(
        "Virtualenv",
        status(ok, warning=True),
        detail,
        "" if ok else "Run ./setup.sh from the repository root.",
    )


def check_modules(modules: Iterable[str] = REQUIRED_MODULES) -> list[CheckResult]:
    results: list[CheckResult] = []
    for module in modules:
        found = importlib.util.find_spec(module) is not None
        results.append(
            CheckResult(
                f"Python module: {module}",
                status(found),
                "installed" if found else "not found",
                "" if found else "Run ./setup.sh, then start with ./start.sh.",
            )
        )
    return results


def check_audio_input() -> CheckResult:
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        inputs = [d for d in devices if d.get("max_input_channels", 0) > 0]
        ok = len(inputs) > 0
        names = ", ".join(d.get("name", "unknown") for d in inputs[:3])
        if len(inputs) > 3:
            names += f", +{len(inputs) - 3} more"
        return CheckResult(
            "Audio input",
            status(ok),
            names or "no input devices",
            "" if ok else "Connect or enable a microphone, then grant Microphone permission.",
        )
    except Exception as exc:
        return CheckResult(
            "Audio input",
            "warn",
            f"could not query devices: {exc}",
            "Install dependencies with ./setup.sh and check macOS Microphone permission.",
        )


def check_python_permission_target(repo_root: str) -> CheckResult:
    venv_python = os.path.join(repo_root, ".venv", "bin", "python")
    target = os.path.realpath(venv_python) if os.path.exists(venv_python) else os.path.realpath(sys.executable)
    return CheckResult(
        "macOS permission target",
        "info",
        target,
        "Add this exact binary to Accessibility and Input Monitoring in System Settings.",
    )


def check_clipboard() -> CheckResult:
    has_pbcopy = shutil.which("pbcopy") is not None
    return CheckResult(
        "Clipboard helper",
        status(has_pbcopy, warning=True),
        "pbcopy found" if has_pbcopy else "pbcopy not found",
        "" if has_pbcopy else "Clipboard paste may fail outside standard macOS shells.",
    )


def check_model_cache() -> CheckResult:
    hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    exists = os.path.exists(hf_home)
    free_gb = disk_free_gb(os.path.expanduser("~"))
    detail = f"{hf_home} ({'exists' if exists else 'not created'}, {free_gb:.1f} GB free)"
    ok = free_gb >= 6
    return CheckResult(
        "Model cache space",
        status(ok, warning=True),
        detail,
        "" if ok else "Free at least 6 GB before the first model download.",
    )


def disk_free_gb(path: str) -> float:
    usage = shutil.disk_usage(path)
    return usage.free / (1024**3)


def run_checks(repo_root: str) -> list[CheckResult]:
    results = [
        check_macos(),
        check_architecture(),
        check_python_version(),
        check_venv(repo_root),
        *check_modules(),
        check_audio_input(),
        check_python_permission_target(repo_root),
        check_clipboard(),
        check_model_cache(),
    ]
    return results


def print_text(results: list[CheckResult]) -> None:
    width = max(len(result.name) for result in results)
    for result in results:
        label = result.status.upper()
        print(f"{label:>4}  {result.name:<{width}}  {result.detail}")
        if result.fix and result.status != "ok":
            print(f"      fix: {result.fix}")

    failures = [r for r in results if r.status == "fail"]
    warnings = [r for r in results if r.status == "warn"]
    print()
    if failures:
        print(f"Voice Dictate is not ready yet: {len(failures)} failed check(s), {len(warnings)} warning(s).")
    elif warnings:
        print(f"Voice Dictate is close: {len(warnings)} warning(s) to review.")
    else:
        print("Voice Dictate environment looks ready.")


def repo_root_from_script() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Voice Dictate environment diagnostics.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--repo-root", default=repo_root_from_script(), help=argparse.SUPPRESS)
    args = parser.parse_args()

    results = run_checks(args.repo_root)
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        print_text(results)

    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
