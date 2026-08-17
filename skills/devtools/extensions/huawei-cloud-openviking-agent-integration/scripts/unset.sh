#!/bin/bash
# =============================================================================
# Wrapper: unset.sh → unbind.sh (backward compatibility alias)
# Usage: ./unset.sh --agent <name> [--dry-run] [--yes]
#        ./unset.sh --all [--dry-run] [--yes]
# =============================================================================
exec "$(dirname "$0")/unbind.sh" "$@"
