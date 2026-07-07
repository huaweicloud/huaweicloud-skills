#!/bin/bash
# CodeArts CLI environment check and setup script (non-interactive)
# Designed for automated Agent execution
#
# Exit codes:
#   0  - Environment ready, can execute code generation
#   10 - AK/SK configuration required
#   20 - User consent required for permission configuration
#   30 - CLI installation failed (auto-resolution attempted)
#   40 - Network connection failed (auto-resolution attempted)
#   50 - Authentication failed (invalid AK/SK)
#
# Output convention:
#   All structured output goes to stdout, logs to stderr
#   Agent parses stdout for status markers
#
# Usage:
#   ./setup.sh                      # Check environment
#   ./setup.sh --save-aksk AK SK    # Save AK/SK to ~/.bashrc and continue
#   ./setup.sh --ak AK --sk SK      # Use AK/SK temporarily (without saving)

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
MAX_RETRY=3
RETRY_DELAY=5
CLI_PATH="$HOME/.codeartsdoer/installers/codearts"
INSTALL_URL="https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.sh"
CONFIG_FILE="$HOME/.bashrc"

# Output functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1" >&2; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Detect operating system
detect_os() {
    case "$(uname -s)" in
        Linux*)     echo "Linux";;
        Darwin*)    echo "macOS";;
        CYGWIN*|MINGW*|MSYS*)    echo "Windows";;
        *)          echo "Unknown";;
    esac
}

OS=$(detect_os)
ARCH=$(uname -m)

# ============================================
# Parse command line arguments
# ============================================
PARSE_ARGS_AK=""
PARSE_ARGS_SK=""
SAVE_AKSK=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --save-aksk)
            SAVE_AKSK=true
            PARSE_ARGS_AK="$2"
            PARSE_ARGS_SK="$3"
            shift 3
            ;;
        --ak)
            PARSE_ARGS_AK="$2"
            shift 2
            ;;
        --sk)
            PARSE_ARGS_SK="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# ============================================
# Save AK/SK to ~/.bashrc
# ============================================
save_aksk() {
    local ak="$1"
    local sk="$2"

    log_info "Saving AK/SK to ~/.bashrc"

    # Remove old AK/SK lines
    sed -i "/^export CODEARTS_CLI_AK=/d; /^export CODEARTS_CLI_SK=/d" "$CONFIG_FILE" 2>/dev/null

    # Append new configuration
    printf "\nexport CODEARTS_CLI_AK=\"%s\"\nexport CODEARTS_CLI_SK=\"%s\"\n" "$ak" "$sk" >> "$CONFIG_FILE"

    log_info "AK/SK saved to ~/.bashrc"
}

# ============================================
# Load AK/SK (priority: args > env vars > ~/.bashrc)
# ============================================
load_aksk() {
    # Priority 1: command line args
    if [ -n "$PARSE_ARGS_AK" ] && [ -n "$PARSE_ARGS_SK" ]; then
        export CODEARTS_CLI_AK="$PARSE_ARGS_AK"
        export CODEARTS_CLI_SK="$PARSE_ARGS_SK"

        if [ "$SAVE_AKSK" = true ]; then
            save_aksk "$PARSE_ARGS_AK" "$PARSE_ARGS_SK"
        fi
        return 0
    fi

    # Priority 2: environment variables
    if [ -n "$CODEARTS_CLI_AK" ] && [ -n "$CODEARTS_CLI_SK" ]; then
        return 0
    fi

    # Priority 3: extract from ~/.bashrc (grep+eval avoids interactive guard)
    if [ -f "$CONFIG_FILE" ]; then
        log_info "Loading AK/SK from ~/.bashrc"
        eval "$(grep '^export CODEARTS_CLI_AK=\|^export CODEARTS_CLI_SK=' "$CONFIG_FILE")"
        if [ -n "$CODEARTS_CLI_AK" ] && [ -n "$CODEARTS_CLI_SK" ]; then
            return 0
        fi
    fi

    return 1
}

# ============================================
# Error handling: output structured JSON for Agent
# ============================================
output_error() {
    local error_code="$1"
    local error_type="$2"
    local error_msg="$3"
    local fix_hint="$4"

    cat << EOF
{
  "status": "error",
  "code": $error_code,
  "type": "$error_type",
  "message": "$error_msg",
  "fix_hint": "$fix_hint",
  "options": [
    {"id": 1, "label": "Continue fixing", "description": "Try to fix the issue manually"},
    {"id": 2, "label": "Write code directly", "description": "Abandon CodeArts, agent writes code directly"}
  ]
}
EOF
    exit "$error_code"
}

# ============================================
# Download with retry
# ============================================
download_with_retry() {
    local url="$1"
    local attempt=1

    while [ $attempt -le $MAX_RETRY ]; do
        log_info "Download attempt $attempt/$MAX_RETRY..."

        if command -v curl >/dev/null 2>&1; then
            if curl -fsSL --connect-timeout 30 "$url"; then
                return 0
            fi
        elif command -v wget >/dev/null 2>&1; then
            if wget -qO- --timeout=30 "$url"; then
                return 0
            fi
        fi

        if [ $attempt -lt $MAX_RETRY ]; then
            log_warn "Download failed, retrying in ${RETRY_DELAY}s..."
            sleep $RETRY_DELAY
        fi

        attempt=$((attempt + 1))
    done

    return 1
}

# ============================================
# Step 1: CLI check and install
# ============================================
check_and_install_cli() {
    log_info "Step 1: Checking CLI..."

    if [ -f "$CLI_PATH" ]; then
        log_info "CLI installed: $CLI_PATH"
        return 0
    fi

    log_info "CLI not installed, auto-installing..."
    log_info "System: $OS ($ARCH)"

    case "$OS" in
        Linux|macOS)
            if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
                output_error 30 "dependency_missing" \
                    "curl or wget is required to download the install script" \
                    "Install curl: apt install curl or yum install curl"
            fi

            INSTALL_SCRIPT=$(download_with_retry "$INSTALL_URL")
            if [ $? -ne 0 ]; then
                output_error 30 "download_failed" \
                    "CLI install script download failed (retried $MAX_RETRY times)" \
                    "Check network, or manually download: $INSTALL_URL"
            fi

            if ! echo "$INSTALL_SCRIPT" | sh 2>&1; then
                output_error 30 "install_failed" \
                    "CLI install script execution failed" \
                    "Check system permissions, or review install logs"
            fi
            ;;
        Windows)
            output_error 30 "unsupported_os" \
                "Windows systems should use PowerShell to install" \
                "irm https://cnnorth4-cloudide-marketplace.obs.cn-north-4.myhuaweicloud.com/codearts/cli_tui/install_script/install.ps1 | iex"
            ;;
        *)
            output_error 30 "unsupported_os" \
                "Unsupported system: $OS" \
                "Currently supported: Linux, macOS, Windows"
            ;;
    esac

    # Verify installation
    if [ -f "$CLI_PATH" ]; then
        log_info "CLI installation complete"
        return 0
    else
        output_error 30 "install_verify_failed" \
            "CLI executable not found after installation" \
            "Check ~/.codeartsdoer/installers/ directory"
    fi
}

# ============================================
# Step 2: AK/SK check
# ============================================
check_aksk() {
    log_info "Step 2: Checking AK/SK..."

    if ! load_aksk; then
        log_warn "AK/SK not configured"
        cat << 'EOF'
{
  "status": "need_input",
  "code": 10,
  "type": "aksk_required",
  "message": "Huawei Cloud Access Key required",
  "help": {
    "description": "Access Key is used to authenticate CodeArts CLI",
    "tutorial_url": "https://support.huaweicloud.com/usermanual-iam/iam_02_0003.html",
    "console_url": "https://console.huaweicloud.com/iam/?#/mine/accessKey",
    "env_vars": [
      {
        "name": "CODEARTS_CLI_AK",
        "label": "Access Key ID",
        "description": "Huawei Cloud Access Key ID",
        "required": true
      },
      {
        "name": "CODEARTS_CLI_SK",
        "label": "Secret Access Key",
        "description": "Huawei Cloud Secret Access Key",
        "required": true,
        "secret": true
      }
    ],
    "hint": "After providing AK/SK, the agent will save them. No need to re-enter. AK/SK are stored only in the local AI Shell environment variables and will NOT be uploaded to any external services, and you can either clear them manually or wait for them to be automatically released when the environment resources are reclaimed to delete them.",
    "save_command": "setup.sh --save-aksk AK SK"
  }
}
EOF
        exit 10
    fi

    log_info "AK/SK configured"
    return 0
}

# ============================================
# Step 3: Permission check
# ============================================
check_permission() {
    log_info "Step 3: Checking permissions..."

    local PERMISSION_FILE="$HOME/.codeartsdoer/cli-data/storage/permission/global.json"

    need_permission_config() {
        if [ ! -f "$PERMISSION_FILE" ]; then
            return 0
        fi

        if grep -q '"permission": "edit"' "$PERMISSION_FILE" && \
           grep -q '"permission": "write"' "$PERMISSION_FILE"; then
            if grep -A1 '"permission": "edit"' "$PERMISSION_FILE" | grep -q '"action": "allow"'; then
                if grep -A1 '"permission": "write"' "$PERMISSION_FILE" | grep -q '"action": "allow"'; then
                    return 1
                fi
            fi
        fi

        return 0
    }

    if need_permission_config; then
        log_warn "Permissions not configured or insufficient"
        cat << EOF
{
  "status": "need_consent",
  "code": 20,
  "type": "permission_required",
  "message": "CodeArts CLI needs file read/write permission to generate code",
  "consent": {
    "description": "After configuration, CLI can create and modify files in the specified directory",
    "risk": "Recommend limiting to the workspace directory, avoid global permissions",
    "workspace": "$PWD"
  }
}
EOF
        exit 20
    fi

    log_info "Permissions configured"
    return 0
}

# ============================================
# Step 4: Verify connection
# ============================================
verify_connection() {
    log_info "Step 4: Verifying connection..."

    local attempt=1

    while [ $attempt -le $MAX_RETRY ]; do
        local OUTPUT
        OUTPUT=$("$CLI_PATH" models 2>&1)

        if [ $? -eq 0 ]; then
            log_info "Connection successful"
            return 0
        fi

        # Check error type
        if echo "$OUTPUT" | grep -qiE "unauthorized|authentication|invalid.*key"; then
            output_error 50 "auth_failed" \
                "Authentication failed, AK/SK is invalid" \
                "Please verify AK/SK is correct, or regenerate"
        fi

        if [ $attempt -lt $MAX_RETRY ]; then
            log_warn "Connection failed, retrying in ${RETRY_DELAY}s..."
            sleep $RETRY_DELAY
        fi

        attempt=$((attempt + 1))
    done

    output_error 40 "network_failed" \
        "Network connection failed (retried $MAX_RETRY times)" \
        "Check network connection and proxy settings"
}

# ============================================
# Main
# ============================================
main() {
    log_info "=== CodeArts CLI Environment Check ==="
    log_info "System: $OS ($ARCH)"

    # Set PATH
    export PATH="$HOME/.codeartsdoer/installers:$PATH"

    check_and_install_cli
    check_aksk
    check_permission
    verify_connection

    # Environment ready
    log_info "Environment ready, can execute code generation"
    cat << 'EOF'
{
  "status": "ready",
  "code": 0,
  "message": "Environment setup complete, ready for code generation"
}
EOF
    exit 0
}

main
