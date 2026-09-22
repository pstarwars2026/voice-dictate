"""Reject common private-only files and secret formats without echoing values.

Checks tracked working-tree content, not history or GitHub discussions. This is
a publishing safeguard, not a comprehensive secret detector or access control.
"""

from pathlib import Path, PurePosixPath
import re
import subprocess


PRIVATE_DIRS = {
    "commercial", "DerivedData", "xcuserdata", ".git", ".venv",
}
PRIVATE_DOCS = {
    "docs/release-state.json", "docs/APPLE_SANDBOX_CHECKS.md",
    "docs/PRO_ICON_CHECKS.md", "docs/APP_STORE_SUBMISSION.md",
    "docs/NATIVE_CHECKS.md", "docs/UPDATE-THESE-FIELDS.txt",
}
PRIVATE_SUFFIXES = {
    ".swift", ".storekit", ".p8", ".p12", ".key", ".mobileprovision",
    ".provisionprofile", ".pkg", ".dmg", ".ipa", ".wav", ".xcarchive",
    ".xcodeproj", ".xcworkspace", ".app",
}
SECRET_PATTERNS = {
    "GitHub credential": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})",
    "service credential": rb"(?:sk-(?:proj-)?[A-Za-z0-9_-]{30,}|AIza[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16}|hf_[A-Za-z0-9]{30,})",
    "private key": rb"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
}


def violations(path, data):
    parts = PurePosixPath(path).parts
    private_path = (
        path in PRIVATE_DOCS
        or path.startswith(("docs/assets/sandbox/", "docs/evidence/", "docs/release-history/"))
        or any(part in PRIVATE_DIRS or part == ".env" or part.startswith(".env.")
               or PurePosixPath(part).suffix.lower() in PRIVATE_SUFFIXES for part in parts)
    )
    result = ["private-only file"] if private_path else []
    result.extend(label for label, pattern in SECRET_PATTERNS.items() if re.search(pattern, data))
    return result


def main():
    root = Path(__file__).resolve().parents[1]
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    failed = False
    for name in filter(None, files):
        path = root / name
        if not path.exists():
            continue
        if path.is_symlink():
            print(f"{name}: symlinks require manual disclosure review")
            failed = True
            continue
        for problem in violations(name, path.read_bytes()):
            print(f"{name}: {problem} (content withheld)")
            failed = True
    if not failed:
        print("Public file and credential-pattern checks passed.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
