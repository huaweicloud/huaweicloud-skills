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

set -e

PERMISSION_FILE="$HOME/.codeartsdoer/cli-data/storage/permission/global.json"

# Parse arguments
AGREE_MODE=false
WORKSPACE=""

while [[ $# -gt 0 ]]; do
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

    read -p "Authorize permission configuration? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "User declined authorization" >&2
        exit 1
    fi

    read -p "Restrict to directory (leave blank for global): " WORKSPACE
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

# Write permission configuration
if [ -z "$WORKSPACE" ]; then
    # Global configuration
    cat > "$PERMISSION_FILE" << 'EOF'
[
  {"permission": "browser", "pattern": "*", "action": "ask"},
  {"permission": "edit", "pattern": "*", "action": "allow"},
  {"permission": "write", "pattern": "*", "action": "allow"},
  {"permission": "webfetch", "pattern": "*", "action": "ask"},
  {"permission": "websearch", "pattern": "*", "action": "allow"},
  {"permission": "external_directory_write", "pattern": "*", "action": "ask"},
  {"permission": "external_directory_read", "pattern": "*", "action": "allow"},
  {"permission": "dotfile", "pattern": "*", "action": "ask"},
  {"permission": "sandbox_risk_command", "pattern": "ls *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "mkdir *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "cat *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "test *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "pwd", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "which *", "action": "allow"}
]
EOF
else
    # Workspace-restricted configuration
    cat > "$PERMISSION_FILE" << EOF
[
  {"permission": "browser", "pattern": "*", "action": "ask"},
  {"permission": "edit", "pattern": "$PATTERN", "action": "allow"},
  {"permission": "write", "pattern": "$PATTERN", "action": "allow"},
  {"permission": "webfetch", "pattern": "*", "action": "ask"},
  {"permission": "websearch", "pattern": "*", "action": "allow"},
  {"permission": "external_directory_write", "pattern": "*", "action": "ask"},
  {"permission": "external_directory_read", "pattern": "*", "action": "allow"},
  {"permission": "dotfile", "pattern": "*", "action": "ask"},
  {"permission": "sandbox_risk_command", "pattern": "ls $WORKSPACE/*", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "mkdir $WORKSPACE/*", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "mkdir -p $WORKSPACE/*", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "cat $WORKSPACE/*", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "test *", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "pwd", "action": "allow"},
  {"permission": "sandbox_risk_command", "pattern": "which *", "action": "allow"}
]
EOF
fi

echo "" >&2
echo "Permission configuration complete" >&2

# Output config file path (for Agent use)
echo "PERMISSION_CONFIGURED"
echo "$PERMISSION_FILE"
