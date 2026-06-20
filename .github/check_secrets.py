"""Fail when tracked repository files contain obvious credentials or runtime data."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATH_PARTS = {
    "cookies",
    "login data",
    "web data",
    "local state",
}

SECRET_PATTERNS = {
    "GitHub personal access token": re.compile(rb"\bghp_[A-Za-z0-9]{20,}\b"),
    "GitHub fine-grained token": re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "Google API key": re.compile(rb"\bAIza[A-Za-z0-9_-]{20,}\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "ls-files",
            "-z",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / item.decode("utf-8")
        for item in result.stdout.split(b"\0")
        if item
    ]


def forbidden_path(path: Path) -> str | None:
    relative = path.relative_to(ROOT)
    normalized = relative.as_posix().lower()
    parts = {part.lower() for part in relative.parts}

    if normalized == ".env" or normalized.startswith("data/"):
        return "runtime data"
    if normalized.endswith("/auth.json") or parts.intersection(FORBIDDEN_PATH_PARTS):
        return "browser or account credential data"
    if "profile" in parts:
        return "browser profile data"
    return None


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        path_issue = forbidden_path(path)
        if path_issue:
            findings.append(f"{path.relative_to(ROOT)}: tracked {path_issue}")
            continue

        try:
            content = path.read_bytes()
        except OSError as exc:
            findings.append(f"{path.relative_to(ROOT)}: could not inspect ({exc})")
            continue

        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{path.relative_to(ROOT)}: possible {label}")

    if findings:
        print("Sensitive-data check failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print("Sensitive-data check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
