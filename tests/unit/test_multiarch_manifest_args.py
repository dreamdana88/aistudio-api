"""The multi-arch merge command must receive two complete image references."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "docker" / "create_multiarch_manifest.sh"


def _bash() -> str:
    git_bash = Path(r"C:\Program Files\Git\bin\bash.exe")
    if git_bash.exists():
        return str(git_bash)
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    pytest.skip("bash is required to capture imagetools arguments")


def _bash_path(path: Path) -> str:
    if os.name != "nt":
        return str(path)
    result = subprocess.run(
        [_bash(), "-c", 'cygpath -u "$1"', "cygpath", str(path)],
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def _run(digest_dir: Path, capture: Path | None, digests: list[str], tags: list[str]):
    for name in digests:
        (digest_dir / name).write_text("", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "IMAGE": "ghcr.io/dreamdana88/aistudio-api",
            "DIGEST_DIR": _bash_path(digest_dir),
            "DOCKER_METADATA_OUTPUT_JSON": json.dumps({"tags": tags}),
        }
    )
    if capture is not None:
        env["IMAGETOOLS_CAPTURE"] = _bash_path(capture)
    result = subprocess.run(
        [_bash(), str(SCRIPT)],
        cwd=digest_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result


def test_two_digests_become_two_complete_references(tmp_path):
    capture = tmp_path / "args.txt"
    digest_dir = tmp_path / "digests"
    digest_dir.mkdir()
    result = _run(
        digest_dir,
        capture,
        ["aaa111", "bbb222"],
        [
            "ghcr.io/dreamdana88/aistudio-api:sha-abc",
            "ghcr.io/dreamdana88/aistudio-api:latest",
        ],
    )
    assert result.returncode == 0, result.stderr
    args = [line for line in capture.read_text(encoding="utf-8").splitlines() if line]
    assert args[:4] == [
        "-t",
        "ghcr.io/dreamdana88/aistudio-api:sha-abc",
        "-t",
        "ghcr.io/dreamdana88/aistudio-api:latest",
    ]
    sources = args[4:]
    assert sources == [
        "ghcr.io/dreamdana88/aistudio-api@sha256:aaa111",
        "ghcr.io/dreamdana88/aistudio-api@sha256:bbb222",
    ]
    assert all(source.count("@sha256:") == 1 for source in sources)
    assert not any(source.endswith("@sha256:") for source in sources)


def test_digest_count_other_than_two_fails(tmp_path):
    digest_dir = tmp_path / "digests"
    digest_dir.mkdir()
    one = _run(digest_dir, None, ["aaa111"], ["ghcr.io/example/api:latest"])
    assert one.returncode != 0
    assert "expected 2 architecture digests, found 1" in one.stderr

    for name in ("bbb222", "ccc333"):
        (digest_dir / name).write_text("", encoding="utf-8")
    three = _run(digest_dir, None, ["aaa111", "bbb222", "ccc333"], ["ghcr.io/example/api:latest"])
    assert three.returncode != 0
    assert "expected 2 architecture digests, found 3" in three.stderr
