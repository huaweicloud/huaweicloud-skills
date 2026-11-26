#!/usr/bin/env bash
# DevBox CLI end-to-end quickstart: auth -> template -> create -> exec -> kill.
# Requires: devbox CLI installed and HW_DEVBOX_API_KEY (or a stored key).
set -euo pipefail

TPL="${1:-tpl-devbox-base-4g}"
LIFETIME="${2:-300}"

if ! command -v devbox >/dev/null 2>&1; then
    if [ -x "$HOME/.huawei/bin/devbox" ]; then
        export PATH="$HOME/.huawei/bin:$PATH"
    else
        echo "[FAIL] devbox CLI not installed — run scripts/devbox_check.py first" >&2
        exit 1
    fi
fi

echo "== auth =="
# auth status only reflects the LOCAL key store and prints to stderr; when it
# reports "Not logged in" but HW_DEVBOX_API_KEY is set, commands still
# authenticate via the environment — say so instead of alarming the user.
AUTH_OUT=$(devbox auth status 2>&1 || true)
if echo "$AUTH_OUT" | grep -qi "not logged in" && [ -n "${HW_DEVBOX_API_KEY:-}" ]; then
    echo "note: no stored key; using HW_DEVBOX_API_KEY from the environment"
else
    echo "$AUTH_OUT"
fi

echo "== template =="
TPL_ID="${DEVBOX_CLI_TEMPLATE:-}"
if [ -z "$TPL_ID" ]; then
    # CLI -f json uses Go-style tags: templateID (capital ID)
    TPL_ID=$(devbox tpl ls -f json 2>/dev/null \
        | grep -oP '"(?:templateId|templateID|template_id)"\s*:\s*"\K[^"]+' | head -1)
    TPL_ID="${TPL_ID:-$TPL}"
fi
echo "using template: $TPL_ID"

echo "== create (detached, ${LIFETIME}s) =="
SBX=$(devbox sbx create "$TPL_ID" -d -t "$LIFETIME")
echo "sandbox: $SBX"

cleanup() {
    echo "== kill =="
    devbox sbx kl "$SBX" && echo "sandbox deleted: $SBX"
}
trap cleanup EXIT

echo "== exec =="
OUT=$(devbox sbx ex "$SBX" -- printf 'hello from DevBox CLI')
echo "output: $OUT"
if [ "$OUT" != "hello from DevBox CLI" ]; then
    echo "[FAIL] unexpected exec output" >&2
    exit 1
fi

echo "CLI QUICKSTART PASSED"
