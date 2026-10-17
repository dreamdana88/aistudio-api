"""Fail unless a manifest list contains linux/amd64 and linux/arm64."""

from __future__ import annotations

import json
import os
import sys

REQUIRED = ("linux/amd64", "linux/arm64")


def platforms_in(manifest: dict) -> list[str]:
    found: list[str] = []
    for item in manifest.get("manifests", []):
        platform = item.get("platform") or {}
        system = platform.get("os")
        architecture = platform.get("architecture")
        if system and architecture:
            found.append(f"{system}/{architecture}")
    return sorted(set(found))


def main() -> int:
    path = os.environ.get("MANIFEST_FILE")
    if not path:
        print("MANIFEST_FILE is required", file=sys.stderr)
        return 1
    with open(path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    found = platforms_in(manifest)
    tag = os.environ.get("IMAGE_TAG", "")
    if tag:
        print(f"tag: {tag}")
    print("platforms: " + ", ".join(found))
    missing = [name for name in REQUIRED if name not in found]
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            if tag:
                handle.write(f"Multi-arch tag: `{tag}`\n\n")
            handle.write("Platforms: " + ", ".join(f"`{name}`" for name in found) + "\n\n")
            handle.write("Pin production to the manifest list digest from imagetools inspect, not `latest`.\n")
    if missing:
        print("missing: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
