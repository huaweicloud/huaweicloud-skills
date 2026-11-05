#!/bin/bash
# VLA NPU training script (located in the migrate_to_cloudrobo/ directory)
# — pass-through mode
#
# Pass-through mode: no longer probes for train.py / run_train.py /
# finetune.py, and does not parse --npus/--output/--port/--accelerate
# arguments. It forwards "$@" unchanged to the model project's own launch
# command (e.g. examples/finetune.sh,
# python gr00t/experiment/launch_finetune.py). This script only: sources
# env_npu.sh (NPU env vars) + sets PYTHONPATH + redirects logs.
#
# Usage: cd <project root> && bash migrate_to_cloudrobo/train.sh [--foreground] <any launch command...>
#
# Examples:
#   ASCEND_RT_VISIBLE_DEVICES=0,1 bash migrate_to_cloudrobo/train.sh \
#       bash examples/finetune.sh --base-model-path <path> --dataset-path <path>
#   ASCEND_RT_VISIBLE_DEVICES=0 bash migrate_to_cloudrobo/train.sh \
#       python gr00t/experiment/launch_finetune.py --config config.json
#
# Note: the command runs from the project root (migrate_to_cloudrobo/'s
# parent). NPU training initialization takes a while. By default it runs in
# the background via nohup: training logs are written to
# output/train/train.log AND streamed to this terminal in real time. Add
# --foreground to run in the foreground (logs straight to the terminal,
# handy for debugging fast failures).

set -e

# =============================================================================
# Path setup (train.sh lives in migrate_to_cloudrobo/, the project root is
# its parent)
# =============================================================================
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

# Load the NPU environment (critical for performance)
source "${SCRIPT_DIR}/env_npu.sh"

# Set PYTHONPATH (project root + migrate_to_cloudrobo/)
export PYTHONPATH="${PROJECT_ROOT}:${SCRIPT_DIR}:${PYTHONPATH}"

# =============================================================================
# Parse the --foreground option
# =============================================================================
FOREGROUND=0
if [[ "${1:-}" == "--foreground" ]]; then
    FOREGROUND=1
    shift
fi

# =============================================================================
# Check the pass-through command
# =============================================================================
if [[ $# -eq 0 ]]; then
    echo "Usage: bash migrate_to_cloudrobo/train.sh [--foreground] <any launch command...>"
    echo "Examples:"
    echo "  bash migrate_to_cloudrobo/train.sh bash examples/finetune.sh --base-model-path <path> --dataset-path <path>"
    echo "  bash migrate_to_cloudrobo/train.sh python gr00t/experiment/launch_finetune.py --config config.json"
    exit 1
fi

# =============================================================================
# Output directory and logs
# =============================================================================
OUTPUT_DIR="${PROJECT_ROOT}/output/train"
mkdir -p "${OUTPUT_DIR}"

echo "============================================================"
echo "VLA NPU training (pass-through mode)"
echo "============================================================"
echo "command:      $*"
echo "work dir:     ${PROJECT_ROOT}"
echo "NPU:          ASCEND_RT_VISIBLE_DEVICES=${ASCEND_RT_VISIBLE_DEVICES:-unset}"
echo "log:          ${OUTPUT_DIR}/train.log"
echo "============================================================"

# Clear Python caches (critical after code edits)
find "${PROJECT_ROOT}" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# =============================================================================
# Start training (pass through "$@")
#   --foreground: run in the foreground (logs straight to the terminal)
#   default: nohup background run; logs tee'd to OUTPUT_DIR/train.log AND
#            streamed to this terminal in real time
# =============================================================================
cd "${PROJECT_ROOT}"
if [[ "${FOREGROUND}" -eq 1 ]]; then
    "$@"
else
    # Process substitution: training stdout/stderr go through `tee`, so logs
    # are written to train.log AND echoed to the terminal. `$!` is the
    # training process PID (not tee's), so `kill $(cat train.pid)` still
    # stops training.
    nohup "$@" > >(tee "${OUTPUT_DIR}/train.log") 2>&1 &

    PID=$!
    echo "${PID}" > "${OUTPUT_DIR}/train.pid"
    echo "PID: ${PID}"
    echo "Log:  ${OUTPUT_DIR}/train.log (also streamed to this terminal)"
    echo "Stop: kill ${PID}"
    echo ""
fi
