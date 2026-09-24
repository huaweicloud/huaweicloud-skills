#!/bin/bash
set -euo pipefail
# =============================================================================
# check_env.sh — Environment check for ECS shutdown experiment (full lifecycle)
# =============================================================================
# Verifies: Python3, hcloud CLI, AK/SK env vars, hcloud configure, region, jq
# Exit codes: 0 = pass, 1 = fail
#
# Usage:
#   bash scripts/check_env.sh
#   bash scripts/check_env.sh --cli-region cn-north-4
#   bash scripts/check_env.sh --region cn-north-4
# =============================================================================

# ---- Named argument parsing (accepts both --cli-region and --region) ----
REGION="${HW_REGION_NAME:-cn-north-4}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --cli-region)  REGION="$2"; shift 2 ;;
        --cli-region=*) REGION="${1#*=}"; shift ;;
        --region)      REGION="$2"; shift 2 ;;
        --region=*)    REGION="${1#*=}"; shift ;;
        --help|-h)     echo "Usage: check_env.sh [--cli-region <region> | --region <region>]"; exit 0 ;;
        *)             echo "Unknown arg: $1"; echo "Usage: check_env.sh [--cli-region <region>]"; exit 1 ;;
    esac
done

PASS=0
FAIL=0
WARN=0

ok()   { echo "  [✓] $1"; PASS=$((PASS+1)); }
fail() { echo "  [✗] $1"; FAIL=$((FAIL+1)); }
warn() { echo "  [!] $1"; WARN=$((WARN+1)); }

echo "=============================================="
echo "  ECS Shutdown Experiment — Environment Check"
echo "  Region: $REGION"
echo "=============================================="
echo ""

# ---- 1. Python3 ----
echo "[1/6] Checking Python3 ..."
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1)
    ok "Python3 found: $PY_VER"
else
    fail "Python3 not found. Install with: apt-get install -y python3"
fi
echo ""

# ---- 2. hcloud CLI ----
echo "[2/6] Checking hcloud CLI ..."
if command -v hcloud &>/dev/null; then
    HC_VER=$(hcloud version 2>&1 | head -1)
    ok "hcloud CLI found: $HC_VER"
else
    fail "hcloud CLI not found. See references/cli-installation-guide.md"
fi
echo ""

# ---- 3. AK/SK environment variables ----
echo "[3/6] Checking credentials ..."
if [[ -n "${HW_ACCESS_KEY:-}" ]]; then
    ok "HW_ACCESS_KEY is set"
else
    warn "HW_ACCESS_KEY is not set. Export it: export HW_ACCESS_KEY=your_ak"
fi

if [[ -n "${HW_SECRET_KEY:-}" ]]; then
    ok "HW_SECRET_KEY is set"
else
    warn "HW_SECRET_KEY is not set. Export it: export HW_SECRET_KEY=your_sk"
fi
echo ""

# ---- 4. hcloud CLI configuration (user-configured) ----
echo "[4/6] Checking hcloud CLI configuration ..."
if hcloud configure list &>/dev/null; then
    ok "hcloud CLI is configured (run 'hcloud configure list' to view profiles)"
else
    warn "hcloud CLI not configured. Run: hcloud configure init"
fi
echo ""

# ---- 5. Region ----
echo "[5/6] Checking region ..."
if [[ -n "${HW_REGION_NAME:-}" ]]; then
    ok "HW_REGION_NAME is set: $HW_REGION_NAME"
else
    warn "HW_REGION_NAME not set. Using --cli-region=$REGION for API calls."
fi
echo ""

# ---- 6. jq (optional) ----
echo "[6/6] Checking optional tools ..."
if command -v jq &>/dev/null; then
    ok "jq found (for JSON processing)"
else
    warn "jq not found. Install for better JSON output: apt-get install -y jq"
fi
echo ""

# ---- Summary ----
echo "=============================================="
echo "  Summary: $PASS passed, $WARN warnings, $FAIL failed"
echo "=============================================="

if [[ $FAIL -gt 0 ]]; then
    echo "  Environment check FAILED. Fix the errors above before continuing."
    exit 1
else
    echo "  Environment check PASSED."
    exit 0
fi
