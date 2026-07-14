#!/bin/bash
set -euo pipefail

RESULT_DIR=""
OUTPUT="./test-report.yaml"

usage() {
  echo "Usage: bash generate-report.sh <result-dir> [options]"
  echo "Options:"
  echo "  --output <path>   Report output path (default: ./test-report.yaml)"
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
      local_pass=0
      local_fail=0
      local_warn=0
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

pass_rate=0.0
if [ "$total_cases" -gt 0 ]; then
  pass_rate=$(echo "scale=2; $passed / $total_cases" | bc 2>/dev/null || echo "0.0")
fi

cat > "$OUTPUT" <<EOF
test_report:
  generated_at: $TIMESTAMP
  result_dir: $RESULT_DIR

  phase_1_installation:
    status: $p1_status
    details: {}

  phase_2_basic:
    status: $p2_status
    details: {}

  phase_3_combination:
    status: $p3_status
    hallucination_detected: $hallucination_status
    details: {}

  phase_4_solution:
    status: $p4_status
    performance: {}
    details: {}

  required_checks:
    pass: $passed
    fail: $failed
    status: $(if [ "$failed" -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi)

  recommended_checks:
    warn: $warned
    status: $(if [ "$warned" -eq 0 ]; then echo "ALL_PRESENT"; else echo "PARTIAL ($warned items missing)"; fi)

  overall:
    status: $overall_status
    total_cases: $total_cases
    passed: $passed
    failed: $failed
    warned: $warned
    pass_rate: $pass_rate
    hallucination_rate: 0.0
    recommendation: "$([ "$overall_status" = "PASS" ] && echo 'Ready for release' || echo 'Fix required check failures before release')"
EOF

echo "[PASS] Test report generated: $OUTPUT"
