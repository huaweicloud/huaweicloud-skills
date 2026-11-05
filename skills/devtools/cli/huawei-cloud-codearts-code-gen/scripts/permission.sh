#!/bin/bash
# CodeArts CLI permission configuration script
# Safely configures file write permissions, requires explicit user consent
#
# Usage:
#   ./permission.sh                    # Interactive, prompts user
#   ./permission.sh --agree /workspace  # Non-interactive, user agreed, restricted
#   ./permission.sh --agree             # Non-interactive, user agreed, global
#
# Exit codes:
#   0 - Configuration successful
#   1 - User declined or parameter error
#
# Output convention:
#   stdout carries only the machine-readable result (`PERMISSION_CONFIGURED`
#   followed by the absolute path of global.json); every log line goes to stderr.
#
# Portability notes:
#   * bash 3.2 (macOS) compatible: no mapfile / no ${var,,} / no associative arrays.
#   * global.json is written to a temp file in the same directory and then moved
#     into place, so a crashed run can never leave a truncated JSON file.
#   * Workspace paths (and any `"` or `\` inside them) are JSON-escaped.

set -e

PERMISSION_FILE="$HOME/.codeartsdoer/cli-data/storage/permission/global.json"
TMP_FILE=""

# ============================================
# JSON helpers
# ============================================
json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\t'/\\t}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    printf '%s' "$s"
}

cleanup_tmp() {
    if [ -n "$TMP_FILE" ] && [ -f "$TMP_FILE" ]; then
        rm -f "$TMP_FILE" 2>/dev/null || true
    fi
}

ENTRY_COUNT=0
perm_entry() {
    if [ "$ENTRY_COUNT" -gt 0 ]; then
        printf ',\n'
    fi
    ENTRY_COUNT=$((ENTRY_COUNT + 1))
    printf '  {"permission": "%s", "pattern": "%s", "action": "%s"}' \
        "$(json_escape "$1")" "$(json_escape "$2")" "$(json_escape "$3")"
}

# ============================================
# Parse arguments
# ============================================
AGREE_MODE=false
WORKSPACE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --agree)
            AGREE_MODE=true
            shift
            ;;
        *)
            WORKSPACE="$1"
            shift
            ;;
    esac
done

echo "=== CodeArts CLI Permission Configuration ===" >&2
echo "" >&2

# Show current config if exists
if [ -f "$PERMISSION_FILE" ]; then
    echo "Current permission configuration:" >&2
    cat "$PERMISSION_FILE" >&2
    echo "" >&2
fi

# Without --agree mode, require user confirmation
if [ "$AGREE_MODE" = false ]; then
    if [ ! -t 0 ]; then
        echo "Error: non-interactive environment requires --agree parameter" >&2
        echo "Usage: $0 --agree [workspace]" >&2
        exit 1
    fi

    echo "Permission configuration details:" >&2
    echo "   - CodeArts CLI needs file read/write permission to generate code" >&2
    echo "   - After configuration, CLI can create and modify files in the specified directory" >&2
    echo "   - Recommend limiting to the workspace directory" >&2
    echo "" >&2

    read -r -p "Authorize permission configuration? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "User declined authorization" >&2
        exit 1
    fi

    read -r -p "Restrict to directory (leave blank for global): " WORKSPACE
fi

# Generate permission configuration
if [ -z "$WORKSPACE" ]; then
    PATTERN="*"
    echo "Configuring global permissions..." >&2
else
    PATTERN="$WORKSPACE/*"
    echo "Restricting permissions to: $PATTERN" >&2
fi

# Ensure directory exists
mkdir -p "$(dirname "$PERMISSION_FILE")"

# Write permission configuration atomically (temp file in the same directory,
# then an atomic rename). Never truncate global.json in place.
TMP_FILE=$(mktemp "${PERMISSION_FILE}.tmp.XXXXXX")
trap 'cleanup_tmp' EXIT INT TERM HUP

{
    printf '[\n'
    ENTRY_COUNT=0

    if [ -z "$WORKSPACE" ]; then
        perm_entry "browser" "*" "ask"
        perm_entry "edit" "$PATTERN" "allow"
        perm_entry "write" "$PATTERN" "allow"
        perm_entry "webfetch" "*" "ask"
        perm_entry "websearch" "*" "allow"
        perm_entry "external_directory_write" "*" "ask"
        perm_entry "external_directory_read" "*" "allow"
        perm_entry "dotfile" "*" "ask"
        perm_entry "sandbox_risk_command" "ls *" "allow"
        perm_entry "sandbox_risk_command" "mkdir *" "allow"
        perm_entry "sandbox_risk_command" "cat *" "allow"
        perm_entry "sandbox_risk_command" "test *" "allow"
        perm_entry "sandbox_risk_command" "pwd" "allow"
        perm_entry "sandbox_risk_command" "which *" "allow"
    else
        perm_entry "browser" "*" "ask"
        perm_entry "edit" "$PATTERN" "allow"
        perm_entry "write" "$PATTERN" "allow"
        perm_entry "webfetch" "*" "ask"
        perm_entry "websearch" "*" "allow"
        perm_entry "external_directory_write" "*" "ask"
        perm_entry "external_directory_read" "*" "allow"
        perm_entry "dotfile" "*" "ask"
        perm_entry "sandbox_risk_command" "ls $WORKSPACE/*" "allow"
        perm_entry "sandbox_risk_command" "mkdir $WORKSPACE/*" "allow"
        perm_entry "sandbox_risk_command" "mkdir -p $WORKSPACE/*" "allow"
        perm_entry "sandbox_risk_command" "cat $WORKSPACE/*" "allow"
        perm_entry "sandbox_risk_command" "test *" "allow"
        perm_entry "sandbox_risk_command" "pwd" "allow"
        perm_entry "sandbox_risk_command" "which *" "allow"
    fi

    printf '\n]\n'
} > "$TMP_FILE"

mv "$TMP_FILE" "$PERMISSION_FILE"

echo "" >&2
echo "Permission configuration complete" >&2

# Output config file path (for Agent use)
echo "PERMISSION_CONFIGURED"
echo "$PERMISSION_FILE"
