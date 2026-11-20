#!/usr/bin/env bash
# Run the full alarm-reduce-noise pipeline in one shared workspace:
#   generate_instance.py -> alarm.py -> analyze_alarm.py
#
# Usage:
#   bash scripts/run_all.sh              # collect the last 1 day (default)
#   bash scripts/run_all.sh --days 7     # extra args are passed to alarm.py
#
# If ALARM_REDUCE_NOISE_WORKSPACE_DIR is already exported, it is reused;
# otherwise a timestamped directory under /root/workspace is created.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "${ALARM_REDUCE_NOISE_WORKSPACE_DIR:-}" ]; then
  ALARM_REDUCE_NOISE_WORKSPACE_DIR="/root/workspace/alarm-reduce-noise-workspace_$(date +%Y%m%d_%H%M%S)"
fi
mkdir -p "$ALARM_REDUCE_NOISE_WORKSPACE_DIR"
export ALARM_REDUCE_NOISE_WORKSPACE_DIR

echo "=== Shared workspace: $ALARM_REDUCE_NOISE_WORKSPACE_DIR ==="

echo "=== Step 1/3: fetch instances via RMS API ==="
python3 "$SCRIPT_DIR/generate_instance.py"

echo "=== Step 2/3: collect CES+AOM alarm data ==="
python3 "$SCRIPT_DIR/alarm.py" "$@"

echo "=== Step 3/3: analyze alarms and generate HTML report ==="
python3 "$SCRIPT_DIR/analyze_alarm.py"

echo "=== Pipeline finished: $ALARM_REDUCE_NOISE_WORKSPACE_DIR ==="