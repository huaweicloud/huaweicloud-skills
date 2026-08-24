#!/bin/bash
# =============================================================================
# common.sh — Backward-compatibility shim
# =============================================================================
# After the OO refactoring, the original shared functions live in:
#   lib/ui.sh      — logging, authorization, dry-run, i18n
#   lib/json.sh    — JSON utilities
#   lib/plugins.sh — plugin provisioning system
#   lib/base.sh    — Agent base class (sandbox discovery, backup, markers, health)
#
# This shim re-exports everything so existing code that does
#   source "$(dirname "$0")/common.sh"
# continues to work without modification.
# =============================================================================
set -euo pipefail

_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source all lib modules in dependency order
source "$_COMMON_DIR/lib/ui.sh"
source "$_COMMON_DIR/lib/json.sh"
source "$_COMMON_DIR/lib/plugins.sh"
source "$_COMMON_DIR/lib/base.sh"

# Clean up the temp variable
unset _COMMON_DIR
