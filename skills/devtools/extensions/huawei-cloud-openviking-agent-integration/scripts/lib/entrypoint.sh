#!/bin/bash
# lib/entrypoint.sh — Common entry point initialization (R18: ov_entrypoint_init)
# Source this file at the top of entry point scripts after set -euo pipefail:
#   #!/bin/bash
#   set -euo pipefail
#   source "$(cd "$(dirname "$0")" && pwd)/lib/entrypoint.sh"
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$SCRIPT_DIR/lib/ui.sh"
source "$SCRIPT_DIR/lib/json.sh"
source "$SCRIPT_DIR/lib/plugins.sh"
source "$SCRIPT_DIR/lib/base.sh"
source "$SCRIPT_DIR/lib/registry.sh"
# (tmp cleanup trap removed: ov_tmp_register had no callers — dead chain)
OV_ENDPOINT="${OV_ENDPOINT:-http://127.0.0.1:1933}"
# P1-8: Validate endpoint — warn on plaintext http:// for non-loopback hosts
ov_validate_endpoint() {
  local ep="$1"
  [[ "$ep" == http://127.* || "$ep" == http://localhost* ]] && return 0
  if [[ "$ep" == http://* ]]; then
    log_warn "Endpoint uses plaintext HTTP for non-loopback host: $ep — traffic is unencrypted"
  fi
}
ov_validate_endpoint "$OV_ENDPOINT"
