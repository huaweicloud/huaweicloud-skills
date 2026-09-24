#!/bin/bash
set -euo pipefail
# =============================================================================
# deploy_experiment.sh — Deploy ECS shutdown experiment
# =============================================================================
# Strategy:
#   Deploy as local config (experiment.json + README.md) and generate
#   rollback_experiment.sh for emergency rollback only.
#   Execution should be done via the dedicated execution workflow.
#
# Usage:
#   ./deploy_experiment.sh --experiment-dir ./experiments/2026-...-ecs-shutdown-xxx/
#   ./deploy_experiment.sh --experiment-dir ./experiments/.../ --dry-run
#   ./deploy_experiment.sh --experiment-dir ./experiments/.../ --cli-region cn-north-4
#
# Security note (HIGH):
#   EXPERIMENT_DIR is treated as DATA, never spliced into code. Paths that
#   reach the Python subprocess are passed via environment variables, so a
#   single quote or other metacharacter in a directory name (e.g. a crafted
#   path planted in a shared /tmp or workspace) cannot become Python code.
#   The rollback script's ROLLBACK_ARGS / ROLLBACK_REGION lines are
#   shell-quoted with printf %q so a single quote inside an instance ID or
#   region cannot break out of the generated script either.
# =============================================================================

# ---- Named argument parsing (while + case for long options) ----
EXPERIMENT_DIR=""
DRY_RUN=false
REGION="${HW_REGION_NAME:-cn-north-4}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --experiment-dir) EXPERIMENT_DIR="$2"; shift 2 ;;
        --dry-run)        DRY_RUN=true; shift ;;
        --cli-region)     REGION="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

if [[ -z "$EXPERIMENT_DIR" ]]; then
    echo "Error: --experiment-dir is required"
    exit 1
fi

EXPERIMENT_JSON="$EXPERIMENT_DIR/experiment.json"

if [[ ! -f "$EXPERIMENT_JSON" ]]; then
    echo "Error: experiment.json not found in $EXPERIMENT_DIR"
    exit 1
fi

echo "=============================================="
echo "  Deploying ECS Shutdown Experiment"
echo "=============================================="
echo "  Experiment dir: $EXPERIMENT_DIR"
echo "  Region:         $REGION"
echo "  Dry run:        $DRY_RUN"
echo ""

# ---- Extract target IDs from experiment.json ----
# EXPERIMENT_JSON is passed via env var, NOT interpolated into Python source.
TARGET_IDS=$(EXPERIMENT_JSON="$EXPERIMENT_JSON" python3 -c '
import json, os
with open(os.environ["EXPERIMENT_JSON"]) as f:
    exp = json.load(f)
ids = exp["targets"]["instance_ids"]
print(",".join(ids))
')

DURATION=$(EXPERIMENT_JSON="$EXPERIMENT_JSON" python3 -c '
import json, os
with open(os.environ["EXPERIMENT_JSON"]) as f:
    exp = json.load(f)
print(exp["actions"]["shutdown"]["duration_seconds"])
')

echo "  Target IDs:     $TARGET_IDS"
echo "  Duration:       ${DURATION}s"
echo ""

# ---- Deploy as local config + emergency rollback script ----
echo "[1/1] Generating emergency rollback script ..."

ROLLBACK_SCRIPT="$EXPERIMENT_DIR/rollback_experiment.sh"

# Build flat CLI params for ECS BatchStartServers.
# NOTE: hcloud 7.2.x does NOT support --body for this API (USE_ERROR); body
# fields must be passed as flat params: --os-start.servers.[N].id=ID.
# Data read from stdin, no path interpolation.
FLAT_ARGS=$(printf '%s' "$TARGET_IDS" | python3 -c '
import sys
ids = [i for i in sys.stdin.read().strip().split(",") if i]
print(" ".join(f"--os-start.servers.{n}.id={i}" for n, i in enumerate(ids, start=1)))
')
# NOTE: KooCLI 7.2.x requires --param=value syntax; space-separated
# `--cli-region <r>` is rejected with USE_ERROR.
REGION_ARG="--cli-region=$REGION"

# Generate rollback-only script (for emergency use)
cat > "$ROLLBACK_SCRIPT" << 'ROLLBACKHEADER'
#!/bin/bash
set -euo pipefail
# Auto-generated ECS shutdown experiment rollback script
# This script starts all target ECS instances to restore pre-experiment state
ROLLBACKHEADER

# Shell-quote args so a single quote inside an instance ID or region cannot
# break out of the generated script (same injection class, second sink).
printf 'ROLLBACK_ARGS=%q\n' "$FLAT_ARGS" >> "$ROLLBACK_SCRIPT"
printf 'ROLLBACK_REGION=%q\n' "$REGION_ARG" >> "$ROLLBACK_SCRIPT"
echo "" >> "$ROLLBACK_SCRIPT"
echo "echo '=== Rolling back: starting target ECS instances ==='" >> "$ROLLBACK_SCRIPT"
echo "hcloud ECS BatchStartServers --cli-output=json \$ROLLBACK_REGION \$ROLLBACK_ARGS" >> "$ROLLBACK_SCRIPT"
echo "echo '=== Rollback complete ==='" >> "$ROLLBACK_SCRIPT"

chmod +x "$ROLLBACK_SCRIPT"

echo "  [✓] Generated: $ROLLBACK_SCRIPT (emergency rollback only)"
echo ""

if [[ "$DRY_RUN" == true ]]; then
    echo "  [DRY RUN] Rollback script generated but not executed."
else
    echo "  Experiment is prepared. To execute:"
    echo "    Use the dedicated execution workflow that reads experiment.json"
    echo "    It performs the full execution flow:"
    echo "      pre-check → shutdown → poll status → wait → rollback → verify → report"
    echo ""
    echo "  Emergency rollback (if execution workflow is unavailable):"
    echo "    $ROLLBACK_SCRIPT"
fi

echo ""
echo "=============================================="
echo "  Deployment SUCCESS (local mode)"
echo "=============================================="
echo ""
echo "  ⚠️  The experiment has NOT been started."
echo "  Review the files in $EXPERIMENT_DIR before executing."
exit 0