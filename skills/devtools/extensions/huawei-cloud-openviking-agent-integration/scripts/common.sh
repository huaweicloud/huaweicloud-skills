#!/bin/bash
# common.sh — Backward-compatibility shim (re-exports lib/ modules)
set -euo pipefail
_COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_COMMON_DIR/lib/ui.sh"
source "$_COMMON_DIR/lib/json.sh"
source "$_COMMON_DIR/lib/plugins.sh"
source "$_COMMON_DIR/lib/base.sh"
unset _COMMON_DIR
