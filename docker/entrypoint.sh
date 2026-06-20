#!/bin/sh
set -eu

if [ "${AISTUDIO_REQUIRE_API_KEY:-0}" = "1" ]; then
    configured_keys="${AISTUDIO_API_KEY:-}${AISTUDIO_API_KEYS:-}"
    if [ "${#configured_keys}" -lt 32 ]; then
        echo "Refusing to start: production deployment requires AISTUDIO_API_KEY (or AISTUDIO_API_KEYS) with at least 32 characters." >&2
        exit 1
    fi
fi

mkdir -p /app/data/accounts /root/.cloakbrowser /tmp

exec "$@"
