#!/usr/bin/env bash
# poll-task.sh - poll a CloudRobo proc-task until it reaches a terminal state,
# printing a timestamped progress heartbeat.
#
# Fallback for when the platform-native `wait-task` cannot stream output (an agent
# tool may abort a long blocking call). See
# references/custom-operator/custom-operator-workflow.md section "Progress Feedback".
#
# Usage: bash poll-task.sh <task-id> [max-polls 120] [sleep-secs 30]
#   e.g. bash poll-task.sh "$TASK_ID" 120 30

set -u

TASK_ID="${1:-}"
MAX_POLLS="${2:-120}"
SLEEP_SECS="${3:-30}"

if [ -z "$TASK_ID" ]; then
  echo "usage: bash poll-task.sh <task-id> [max-polls 120] [sleep-secs 30]" >&2
  exit 2
fi

START_TS=$(date +%s)
poll=0

while [ "$poll" -lt "$MAX_POLLS" ]; do
  poll=$((poll + 1))
  out=$(cloudrobo dataset proc show-task --task-id "$TASK_ID" 2>&1)
  status=$(printf '%s' "$out" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("UNKNOWN"); sys.exit(0)
payload = data.get("payload", data)
print(payload.get("status") or data.get("status") or "UNKNOWN")
')
  now=$(date +%s)
  elapsed=$((now - START_TS))
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] poll#${poll} status=${status} elapsed=${elapsed}s"

  case "$status" in
    SUCCEEDED|FAILED|DELETED)
      exit 0
      ;;
  esac

  sleep "$SLEEP_SECS"
done

echo "poll-task: timed out after ${MAX_POLLS} polls; the task may still be running" >&2
echo "poll-task: re-run poll-task.sh - do NOT create a new task" >&2
exit 1
