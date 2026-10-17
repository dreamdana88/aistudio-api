"""The Oracle compose and Caddy example stay on the reviewed deployment shape."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _compose():
    return yaml.safe_load((ROOT / "docker" / "docker-compose.deploy.yml").read_text(encoding="utf-8"))


def test_oracle_compose_publishes_loopback_only():
    service = _compose()["services"]["aistudio-api"]
    ports = service["ports"]
    assert ports == [
        "127.0.0.1:${AISTUDIO_BIND_PORT:-18081}:8080",
        "127.0.0.1:${AISTUDIO_NOVNC_BIND_PORT:-6080}:6080",
    ]
    assert service.get("network_mode") is None
    published = "\n".join(ports)
    for forbidden in ("0.0.0.0", "[::]", ":5900", ":9222", ":9223"):
        assert forbidden not in published
    assert service["environment"]["AISTUDIO_MAX_CONCURRENCY"] == "3"
    assert "AISTUDIO_NOVNC_PUBLIC_URL" in service["environment"]["AISTUDIO_NOVNC_PUBLIC_URL"]
    assert "sha256:" in service["image"]
    assert ":latest" not in service["image"]
    assert "mem_limit" not in service
    assert service["volumes"][1].endswith(":/root/.cloakbrowser")
    names = _compose()["volumes"]
    assert names["aistudio-oracle-data"]["name"] == "aistudio-oracle-data"
    assert names["aistudio-oracle-browser-cache"]["name"] == "aistudio-oracle-browser-cache"


def test_caddy_example_authenticates_the_whole_login_site():
    text = (ROOT / "docker" / "caddy" / "aistudio-oracle.caddy.example").read_text(encoding="utf-8")
    api, login = text.split("LOGIN_DOMAIN:8443", 1)
    assert "basic_auth" not in api.split("API_DOMAIN:8443", 1)[1]
    assert "127.0.0.1:18081" in api
    assert "basic_auth" in login
    assert "127.0.0.1:6080" in login
    assert "handle" not in login
    assert "websockify" not in login
    assert "$2b$14$eg.cSmX9xIiEMLINOSoPpuARyuUwTIvKMvXVsub/FmSVyJg7pXhgS" in login


def _manifest_module():
    import importlib.util

    path = ROOT / "docker" / "verify_image_manifest.py"
    spec = importlib.util.spec_from_file_location("verify_image_manifest", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_checker_requires_both_platforms(tmp_path, monkeypatch):
    module = _manifest_module()
    found = module.platforms_in(
        {
            "manifests": [
                {"platform": {"os": "linux", "architecture": "amd64"}},
                {"platform": {"os": "linux", "architecture": "arm64"}},
                {"platform": {"os": "unknown", "architecture": "unknown"}},
            ]
        }
    )
    assert found == ["linux/amd64", "linux/arm64", "unknown/unknown"]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"manifests":[{"platform":{"os":"linux","architecture":"amd64"}}]}',
        encoding="utf-8",
    )
    monkeypatch.setenv("MANIFEST_FILE", str(manifest))
    monkeypatch.setenv("IMAGE_TAG", "ghcr.io/example/app:sha-test")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    assert module.main() == 1
    manifest.write_text(
        '{"manifests":['
        '{"platform":{"os":"linux","architecture":"amd64"}},'
        '{"platform":{"os":"linux","architecture":"arm64"}}'
        "]}",
        encoding="utf-8",
    )
    assert module.main() == 0
