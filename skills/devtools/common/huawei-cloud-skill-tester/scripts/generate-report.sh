#!/bin/bash
#===============================================================================
# generate-report.sh — Test Report Generator (delegates to test-skill.sh)
#
# Usage: bash scripts/generate-report.sh <result-dir> [--output <path>]
#
# This is a convenience wrapper that delegates to test-skill.sh --phase report.
# For advanced usage, call test-skill.sh directly with --phase report.
#===============================================================================
set -euo pipefail

RESULT_DIR=""
OUTPUT="./test-report.yaml"

usage() {
  echo "Usage: bash generate-report.sh <result-dir> [options]"
  echo "Options:"
  echo "  --output <path>   Report output path (default: ./test-report.yaml)"
  echo ""
  echo "Note: Delegates to test-skill.sh --phase report. The <result-dir>"
  echo "is used as --skill-path for consistency."
  exit 1
}

if [ $# -lt 1 ]; then usage; fi

RESULT_DIR="$1"
shift

while [ $# -gt 0 ]; do
  case "$1" in
    --output) OUTPUT="$2"; shift 2 ;;
    *) usage ;;
  esac
done

echo "=== Generating Test Report ==="
echo "Result directory: $RESULT_DIR"
echo "Output path: $OUTPUT"

# Delegate to test-skill.sh --phase report
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_SKILL="$SCRIPT_DIR/test-skill.sh"

if [ -f "$TEST_SKILL" ] && [ -x "$TEST_SKILL" ]; then
  exec bash "$TEST_SKILL" "report-gen" \
    --skill-path "$RESULT_DIR" \
    --phase report \
    --output "$OUTPUT"
else
  echo "[ERROR] test-skill.sh not found at $TEST_SKILL"
  echo "Falling back to standalone report generation..."

  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  p1_status="PENDING"
  p2_status="PENDING"
  p3_status="PENDING"
  p4_status="PENDING"
  overall_status="PENDING"
  total_cases=0
  passed=0
  failed=0
  warned=0
  hallucination_status="false"

  if [ -d "$RESULT_DIR" ]; then
    for phase_file in "$RESULT_DIR"/phase_*.log; do
      if [ -f "$phase_file" ]; then
        local_pass=0; local_fail=0; local_warn=0
        if grep -q '\[PASS\]' "$phase_file" 2>/dev/null; then
          local_pass=$(grep -c '\[PASS\]' "$phase_file" 2>/dev/null || echo "0")
        fi
        if grep -q '\[FAIL\]' "$phase_file" 2>/dev/null; then
          local_fail=$(grep -c '\[FAIL\]' "$phase_file" 2>/dev/null || echo "0")
        fi
        if grep -q '\[WARN\]' "$phase_file" 2>/dev/null; then
          local_warn=$(grep -c '\[WARN\]' "$phase_file" 2>/dev/null || echo "0")
        fi
        passed=$((passed + local_pass))
        failed=$((failed + local_fail))
        warned=$((warned + local_warn))
        total_cases=$((total_cases + local_pass + local_fail + local_warn))

        local phase_name
        phase_name=$(basename "$phase_file" .log)
        case "$phase_name" in
          phase_1*) p1_status=$([ "$local_fail" -eq 0 ] && echo "PASS" || echo "FAIL") ;;
          phase_2*) p2_status=$([ "$local_fail" -eq 0 ] && echo "PASS" || echo "FAIL") ;;
          phase_3*)
            p3_status=$([ "$local_fail" -eq 0 ] && echo "PASS" || echo "FAIL")
            if grep -qi 'HALLUCINATION_DETECTED' "$phase_file" 2>/dev/null; then
              hallucination_status="true"
            fi
            ;;
          phase_4*) p4_status=$([ "$local_fail" -eq 0 ] && echo "PASS" || echo "FAIL") ;;
        esac
      fi
    done

    if [ "$failed" -eq 0 ]; then
      overall_status="PASS"
    else
      overall_status="FAIL"
    fi
  fi

  cat > "$OUTPUT" << EOF
test_report:
  generated_by: generate-report.sh (standalone fallback)
  timestamp: $TIMESTAMP
  summary:
    total_cases: $total_cases
    passed: $passed
    failed: $failed
    warned: $warned
    hallucination_detected: $hallucination_status
  phases:
    phase_1:
      status: $p1_status
    phase_2:
      status: $p2_status
    phase_3:
      status: $p3_status
      hallucination_detected: $hallucination_status
    phase_4:
      status: $p4_status
  overall:
    status: $overall_status
EOF

  echo "Report generated at $OUTPUT"
fi
