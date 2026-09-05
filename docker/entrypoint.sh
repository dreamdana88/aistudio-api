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

DISPLAY_NUM="${AISTUDIO_DISPLAY_NUM:-99}"
VNC_PORT="${AISTUDIO_VNC_PORT:-5900}"
NOVNC_PORT="${AISTUDIO_NOVNC_PORT:-6080}"
ENABLE_DISPLAY="${AISTUDIO_ENABLE_DISPLAY:-1}"
SCREEN_GEOM="${AISTUDIO_DISPLAY_GEOMETRY:-1280x720x24}"
NOVNC_WEB="${AISTUDIO_NOVNC_WEB:-/usr/share/novnc}"

CHILD_PIDS=""
APP_PID=""

term_children() {
    for pid in $CHILD_PIDS $APP_PID; do
        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
            kill -TERM "${pid}" 2>/dev/null || true
        fi
    done
    i=0
    while [ "${i}" -lt 10 ]; do
        alive=0
        for pid in $CHILD_PIDS $APP_PID; do
            if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
                alive=1
            fi
        done
        if [ "${alive}" -eq 0 ]; then
            break
        fi
        i=$((i + 1))
        sleep 0.3
    done
    for pid in $CHILD_PIDS $APP_PID; do
        if [ -n "${pid}" ] && kill -0 "${pid}" 2>/dev/null; then
            kill -KILL "${pid}" 2>/dev/null || true
        fi
    done
}

on_signal() {
    echo "entrypoint: received stop signal, shutting down display and app" >&2
    term_children
    exit 0
}

trap on_signal INT TERM

wait_for_socket() {
    path=$1
    i=0
    while [ "${i}" -lt 50 ]; do
        if [ -S "${path}" ]; then
            return 0
        fi
        i=$((i + 1))
        sleep 0.1
    done
    echo "entrypoint: timeout waiting for ${path}" >&2
    return 1
}

wait_for_port() {
    host=$1
    port=$2
    python3 -c "
import socket, sys, time
host, port = sys.argv[1], int(sys.argv[2])
deadline = time.time() + 8
while time.time() < deadline:
    sock = socket.socket()
    sock.settimeout(0.2)
    try:
        sock.connect((host, port))
        sock.close()
        raise SystemExit(0)
    except OSError:
        time.sleep(0.1)
    finally:
        try:
            sock.close()
        except OSError:
            pass
raise SystemExit(1)
" "${host}" "${port}"
}

if [ "${ENABLE_DISPLAY}" = "1" ]; then
    echo "entrypoint: starting Xvfb :${DISPLAY_NUM} ${SCREEN_GEOM}"
    Xvfb ":${DISPLAY_NUM}" -screen 0 "${SCREEN_GEOM}" -ac +extension RANDR +extension GLX -nolisten tcp &
    CHILD_PIDS="${CHILD_PIDS} $!"
    wait_for_socket "/tmp/.X11-unix/X${DISPLAY_NUM}"

    LOGIN_DISPLAY=":${DISPLAY_NUM}"
    {
        echo "AISTUDIO_LOGIN_DISPLAY=${LOGIN_DISPLAY}"
        echo "DISPLAY=${LOGIN_DISPLAY}"
    } > /tmp/aistudio-display.env
    export AISTUDIO_LOGIN_DISPLAY="${LOGIN_DISPLAY}"
    # Headed login browsers inherit DISPLAY. The working browser stays headless
    # via AISTUDIO_BROWSER_HEADLESS=1 and does not need this display.
    export DISPLAY="${LOGIN_DISPLAY}"

    if command -v dbus-launch >/dev/null 2>&1; then
        eval "$(dbus-launch --sh-syntax)"
        echo "entrypoint: dbus session started"
        if [ -n "${DBUS_SESSION_BUS_PID:-}" ]; then
            CHILD_PIDS="${CHILD_PIDS} ${DBUS_SESSION_BUS_PID}"
        fi
    fi

    echo "entrypoint: starting x11vnc on 127.0.0.1:${VNC_PORT}"
    # -xkb + -nomodtweak: default -modtweak fights XKB and drops Shift,
    # so VNC clients type "D" as "d". Clear leftover Caps/Shift on start.
    x11vnc -display "${LOGIN_DISPLAY}" -localhost -rfbport "${VNC_PORT}" \
        -forever -shared -nopw -xkb -nomodtweak -clear_mods -clear_keys \
        -repeat -noxdamage -ncache 0 -quiet &
    CHILD_PIDS="${CHILD_PIDS} $!"
    wait_for_port 127.0.0.1 "${VNC_PORT}"

    echo "entrypoint: starting noVNC/websockify on 0.0.0.0:${NOVNC_PORT} -> 127.0.0.1:${VNC_PORT}"
    websockify --web="${NOVNC_WEB}" "0.0.0.0:${NOVNC_PORT}" "127.0.0.1:${VNC_PORT}" &
    CHILD_PIDS="${CHILD_PIDS} $!"
    wait_for_port 127.0.0.1 "${NOVNC_PORT}"
    echo "entrypoint: display ready (Xvfb :${DISPLAY_NUM}, vnc 127.0.0.1:${VNC_PORT}, novnc :${NOVNC_PORT})"
fi

"$@" &
APP_PID=$!
set +e
wait "${APP_PID}"
STATUS=$?
set -e
term_children
exit "${STATUS}"
