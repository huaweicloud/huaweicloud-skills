#!/usr/bin/env bash
# -*- coding: utf-8 -*-
#
# Environment check script - validate hcloud CLI and auth configuration
#
# Features:
#   1. Check hcloud CLI is installed and version >= 7.2.2
#   2. Check auth configuration (supports HW_*, HUAWEI_CLOUD_*, hcloud configure)
#   3. Verify network connectivity and API reachability
#
# Usage:
#   ./scripts/check_env.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[WARN]  $1${NC}"
}

print_error() {
    echo -e "${RED}[FAIL] $1${NC}"
}

echo "=========================================="
echo "huawei-cloud-ecs-alert Environment Check"
echo "=========================================="
echo ""

# Step 1: Check Python environment
print_step "Step 1/4: Check Python environment"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_success "Python installed: $PYTHON_VERSION"
else
    print_error "Python3 not installed"
    echo "Please install Python 3.6+ and retry"
    exit 1
fi
echo ""

# Step 2: Check hcloud CLI
print_step "Step 2/4: Check hcloud CLI"
if command -v hcloud &> /dev/null; then
    HCLOUD_VERSION=$(hcloud version 2>&1 | grep -oP '\d+\.\d+\.\d+' | head -1)
    if [ -n "$HCLOUD_VERSION" ]; then
        # Version comparison
        REQUIRED_VERSION="7.2.2"
        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$HCLOUD_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_success "hcloud CLI installed: $HCLOUD_VERSION (>= $REQUIRED_VERSION)"
        else
            print_warning "hcloud CLI version too low: $HCLOUD_VERSION (requires >= $REQUIRED_VERSION)"
            echo "Suggest upgrade: pip install --upgrade hcloud"
            exit 1
        fi
    else
        print_warning "hcloud version detection failed, trying to continue..."
    fi
else
    print_error "hcloud CLI not installed"
    echo "Please install Huawei Cloud CLI (KooCLI) >= 7.2.2"
    echo "Install command: pip install hcloud"
    exit 1
fi
echo ""

# Step 3: Check auth configuration
print_step "Step 3/4: Check auth configuration"

# Detect auth source
CRED_SOURCE=""
if [ -n "$HW_ACCESS_KEY" ] && [ -n "$HW_SECRET_KEY" ]; then
    CRED_SOURCE="HW_* env vars"
    print_success "HW_* env vars detected (recommended)"
elif [ -n "$HUAWEI_CLOUD_AK" ] && [ -n "$HUAWEI_CLOUD_SK" ]; then
    CRED_SOURCE="HUAWEI_CLOUD_* env vars"
    print_success "HUAWEI_CLOUD_* env vars detected (compatible)"
else
    # Try hcloud configure
    if hcloud configure list &> /dev/null; then
        CRED_SOURCE="hcloud configure"
        print_success "hcloud configure detected"
    else
        print_error "No valid auth detected"
        echo ""
        echo "Please configure authentication."
        echo "Run 'hcloud configure' or set environment variables."
        echo "See SKILL.md for detailed setup instructions."
        echo ""
        exit 1
    fi
fi

# Check region configuration
if [ -n "$HW_REGION_NAME" ]; then
    REGION="$HW_REGION_NAME"
elif [ -n "$HUAWEI_CLOUD_REGION" ]; then
    REGION="$HUAWEI_CLOUD_REGION"
else
    # Get from hcloud configure
    REGION=$(hcloud configure list 2>/dev/null | grep "^region" | cut -d'=' -f2 | tr -d ' ' || echo "cn-north-4")
fi

print_success "Region: $REGION"
echo ""

# Step 4: Verify API connectivity
print_step "Step 4/4: Verify API connectivity"

# Set temporary env vars for hcloud
if [ "$CRED_SOURCE" = "HW_* env vars" ]; then
    # Map HW_* to HUAWEI_CLOUD_* for hcloud CLI compatibility
    export HUAWEI_CLOUD_AK="$HW_ACCESS_KEY"
    export HUAWEI_CLOUD_SK="$HW_SECRET_KEY"
    export HUAWEI_CLOUD_REGION="$REGION"
elif [ "$CRED_SOURCE" = "HUAWEI_CLOUD_* env vars" ]; then
    export HUAWEI_CLOUD_REGION="$REGION"
fi

# Test CES API connectivity
if hcloud CES ListAlarms --cli-region="$REGION" --limit=1 &> /dev/null; then
    print_success "CES API connection normal"
else
    print_warning "CES API connection test failed (may be permission or network issue)"
    echo "Continuing with other checks..."
fi

# Test SMN API connectivity
if hcloud SMN ListTopics --cli-region="$REGION" &> /dev/null; then
    print_success "SMN API connection normal"
else
    print_warning "SMN API connection test failed (may be permission or network issue)"
fi

echo ""
echo "=========================================="
echo "[OK] Environment check complete"
echo "=========================================="
echo ""
echo "Auth source: $CRED_SOURCE"
echo "Region: $REGION"
echo ""
echo "Next steps:"
echo "  - Create alert rules: ./scripts/create_alert_rules.sh --template web --ecs-ids <ecs-id>"
echo "  - List ECS: ./scripts/list_ecs.sh"
echo "  - List alarms: ./scripts/list_alarms.sh"
echo ""
