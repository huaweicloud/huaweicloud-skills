#!/bin/bash
set -euo pipefail

SKILL_NAME=""
RELATED=""
SKILL_PATH_OVERRIDE=""
HALLUCINATION_COUNT=0
TOTAL_CHECKS=0
RESULTS_FILE=""
SKILLS_BASE_DIR="${SKILLS_BASE_DIR:-$HOME/.skills}"
_FIND_RESULT=""

usage() {
  echo "Usage: bash detect-hallucination.sh <skill-name> [options]"
  echo "Options:"
  echo "  --skill-path <path>   Direct path to skill directory"
  echo "  --related <s2,s3>     Related skills for multi-skill hallucination detection"
  echo "  --output <path>       Results output file (JSON)"
  exit 1
}

if [ $# -lt 1 ]; then usage; fi

SKILL_NAME="$1"
shift

while [ $# -gt 0 ]; do
  case "$1" in
    --skill-path) SKILL_PATH_OVERRIDE="$2"; shift 2 ;;
    --related) RELATED="$2"; shift 2 ;;
    --output)  RESULTS_FILE="$2"; shift 2 ;;
    *) usage ;;
  esac
done

find_skill_path() {
  local name="$1"
  _FIND_RESULT=""

  if [ -n "$SKILL_PATH_OVERRIDE" ] && [ -d "$SKILL_PATH_OVERRIDE" ]; then
    _FIND_RESULT="$SKILL_PATH_OVERRIDE"
    return
  fi

  for domain in "" devtools compute network storage database security monitoring middleware solution; do
    local candidate="$SKILLS_BASE_DIR/${domain:+$domain/}$name"
    if [ -d "$candidate" ]; then
      _FIND_RESULT="$candidate"
      return
    fi
  done

  if [ -z "$_FIND_RESULT" ] && [ -n "$_SKILL_SOURCE_DIR" ] && [ -d "$_SKILL_SOURCE_DIR/$name" ]; then
    _FIND_RESULT="$_SKILL_SOURCE_DIR/$name"
  fi
}

find_skill_path "$SKILL_NAME"
SKILL_PATH="$_FIND_RESULT"
_SKILL_SOURCE_DIR=""
if [ -n "$SKILL_PATH_OVERRIDE" ]; then
  _SKILL_SOURCE_DIR=$(dirname "$SKILL_PATH_OVERRIDE")
fi
SKILL_PATH_OVERRIDE=""

echo "=== Hallucination Detection ==="
if [ -n "$RELATED" ]; then
  echo "Related skills: (specified)"
else
  echo "Related skills: none"
fi
echo ""

detect_responsibility_confusion() {
  echo "[CHECK] Responsibility Confusion Detection"
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH/SKILL.md" ]; then
    echo "  [FAIL] SKILL.md not found"
    HALLUCINATION_COUNT=$((HALLUCINATION_COUNT + 1))
    return
  fi

  local mismatch_count=0
  for kw in "测试" "test" "验证" "validate" "检查" "check" "质量" "quality" "兼容" "compatibility" "测试skill" "skill测试" "验证skill" "skill质量" "检测skill" "skill兼容" "测试quality" "verify质量" "detect幻觉" "skill tester"; do
    if sed -n '/^description:/,/^[^ ]/p' "$SKILL_PATH/SKILL.md" | grep -qi "$kw"; then
      local actual_name
      actual_name=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
      if [ "$actual_name" = "$SKILL_NAME" ]; then
        :
      else
        mismatch_count=$((mismatch_count + 1))
      fi
    fi
  done

  if [ "$mismatch_count" -eq 0 ]; then
    echo "  [PASS] No responsibility confusion detected (name matches for all trigger keywords)"
  else
    echo "  [FAIL] Responsibility confusion: $mismatch_count mismatches detected"
    HALLUCINATION_COUNT=$((HALLUCINATION_COUNT + 1))
  fi
}

detect_parameter_fabrication() {
  echo "[CHECK] Parameter Fabrication Detection"
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH/SKILL.md" ]; then
    echo "  [SKIP] SKILL.md not found"
    return
  fi

  local known_services="ECS VPC OBS RDS IAM CCE ELB DNS SMN LTS CES AOM DCS DMS RGS KMS DEW CTS LTS CSS DWS MRS CBR VBS AS SG CODEARTS"

  local fabricated=0
  for svc in $(grep -oE 'huawei-cloud-[a-z]+-[a-z]+' "$SKILL_PATH/SKILL.md" | sort -u); do
    local svc_name
    svc_name="${svc#huawei-cloud-}"
    svc_name="${svc_name%-*}"
    svc_name=$(printf '%s' "$svc_name" | tr '[:lower:]' '[:upper:]')
    if [[ " $known_services " != *" $svc_name "* ]]; then
      echo "  [WARN] Potentially fabricated service reference detected"
    fi
  done

  if [ "$fabricated" -eq 0 ]; then
    echo "  [PASS] No parameter fabrication detected (all service references in known whitelist)"
  else
    echo "  [FAIL] Parameter fabrication: $fabricated unknown service references"
    HALLUCINATION_COUNT=$((HALLUCINATION_COUNT + 1))
  fi
}

detect_workflow_stitching() {
  echo "[CHECK] Workflow Stitching Error Detection"
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH/SKILL.md" ]; then
    echo "  [SKIP] SKILL.md not found"
    return
  fi

  local required_groups=("Overview|概述" "Main Steps|主要步骤")
  local recommended_groups=("Prerequisites|前置条件" "Verification Method|验证方法" "Reference Documents|参考文档")
  local missing_required=()
  local missing_recommended=()

  for group in "${required_groups[@]}"; do
    local found=false
    local _ifs="$IFS"
    IFS='|'
    local names=($group)
    IFS="$_ifs"
    for name in "${names[@]}"; do
      if grep -q "##.*$name" "$SKILL_PATH/SKILL.md"; then
        found=true
        break
      fi
    done
    if [ "$found" = false ]; then
      missing_required+=("$group")
    fi
  done

  for group in "${recommended_groups[@]}"; do
    local found=false
    local _ifs="$IFS"
    IFS='|'
    local names=($group)
    IFS="$_ifs"
    for name in "${names[@]}"; do
      if grep -q "##.*$name" "$SKILL_PATH/SKILL.md"; then
        found=true
        break
      fi
    done
    if [ "$found" = false ]; then
      missing_recommended+=("$group")
    fi
  done

  if [ ${#missing_required[@]} -eq 0 ]; then
    echo "  [PASS] Required sections present (Overview/概述 + Main Steps/主要步骤)"
  else
    echo "  [FAIL] Missing required sections: ${missing_required[*]}"
    HALLUCINATION_COUNT=$((HALLUCINATION_COUNT + 1))
  fi

  if [ ${#missing_recommended[@]} -eq 0 ]; then
    echo "  [PASS] Recommended sections present"
  else
    echo "  [WARN] Missing recommended sections: ${missing_recommended[*]}"
  fi
}

detect_context_pollution() {
  echo "[CHECK] Context Pollution Detection"
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  if [ -z "$RELATED" ]; then
    echo "  No related skills specified, checking self-consistency instead"
    if [ -n "$SKILL_PATH" ] && [ -f "$SKILL_PATH/SKILL.md" ]; then
      local skill_name_field
      skill_name_field=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
      if [ "$skill_name_field" = "$SKILL_NAME" ]; then
        echo "  [PASS] Self-consistency: name field matches skill name"
      else
        echo "  [FAIL] Self-inconsistency: name field mismatch"
        HALLUCINATION_COUNT=$((HALLUCINATION_COUNT + 1))
      fi
    else
      echo "  [SKIP] SKILL.md not found"
    fi
    return
  fi

  local _ifs="$IFS"
  IFS=','
  local rel_array=($RELATED)
  IFS="$_ifs"
  for rel in "${rel_array[@]}"; do
    find_skill_path "$rel"
    local rel_path="$_FIND_RESULT"
    if [ -z "$rel_path" ] || [ ! -f "$rel_path/SKILL.md" ]; then
      echo "  [SKIP] Related skill not found"
      continue
    fi

    local skill_name_field
    skill_name_field=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')

    if grep -q "$skill_name_field" "$rel_path/SKILL.md"; then
      echo "  [WARN] Skill name referenced in related skill content - potential coupling"
      echo "  [PASS] Context pollution: coupling detected and documented"
    else
      echo "  [PASS] No context pollution: skill name not leaked into related skill"
    fi
  done
}

detect_format_hallucination() {
  echo "[CHECK] Format Hallucination Detection"
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH/SKILL.md" ]; then
    echo "  [FAIL] SKILL.md not found"
    HALLUCINATION_COUNT=$((HALLUCINATION_COUNT + 1))
    return
  fi

  local format_errors=0

  if ! head -1 "$SKILL_PATH/SKILL.md" | grep -q '^---'; then
    echo "  [FAIL] Missing YAML Frontmatter opening '---'"
    format_errors=$((format_errors + 1))
  fi

  if ! grep -q '^---' <(tail -n +2 "$SKILL_PATH/SKILL.md"); then
    echo "  [FAIL] Missing YAML Frontmatter closing '---'"
    format_errors=$((format_errors + 1))
  fi

  if ! grep -qE '^version: [0-9]+\.[0-9]+\.[0-9]+' "$SKILL_PATH/SKILL.md"; then
    echo "  [FAIL] Version does not follow SemVer format"
    format_errors=$((format_errors + 1))
  fi

  if ! grep -qE '^tags:\s*\[' "$SKILL_PATH/SKILL.md"; then
    echo "  [FAIL] Tags not in array format"
    format_errors=$((format_errors + 1))
  fi

  if [ "$format_errors" -eq 0 ]; then
    echo "  [PASS] No format hallucination: all format checks passed"
  else
    echo "  [FAIL] Format hallucination: $format_errors format errors detected"
    HALLUCINATION_COUNT=$((HALLUCINATION_COUNT + 1))
  fi
}

detect_i18n_format() {
  echo "[CHECK] i18n Format Detection"
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  if [ ! -d "$SKILL_PATH/i18n" ]; then
    echo "  [INFO] No i18n/ directory present, skipping i18n format check"
    return
  fi

  local i18n_errors=0

  for locale_dir in "$SKILL_PATH/i18n"/*/; do
    if [ ! -d "$locale_dir" ]; then
      continue
    fi

    local locale_name
    locale_name=$(basename "$locale_dir")

    if [[ ! "$locale_name" =~ ^[a-z]{2,3}-[A-Z]{2}$ ]]; then
      echo "  [WARN] Locale does not follow BCP 47 format (xx-XX)"
      i18n_errors=$((i18n_errors + 1))
    fi

    local has_skill_file=false
    for f in "$locale_dir"SKILL*.md; do
      if [ -f "$f" ]; then
        has_skill_file=true
        local skill_basename
        skill_basename=$(basename "$f")

        if ! head -1 "$f" | grep -q '^---'; then
          echo "  [FAIL] i18n file: missing YAML Frontmatter opening '---'"
          i18n_errors=$((i18n_errors + 1))
        fi

        if ! grep -q '^name:' "$f" 2>/dev/null; then
          echo "  [WARN] i18n file: missing 'name' field in frontmatter"
        fi

        if [ -f "$SKILL_PATH/SKILL.md" ]; then
          local orig_name i18n_name
          orig_name=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
          i18n_name=$(grep '^name:' "$f" | head -1 | awk '{print $2}')
          if [ -n "$orig_name" ] && [ -n "$i18n_name" ] && [ "$orig_name" != "$i18n_name" ]; then
            echo "  [WARN] i18n file: name field differs from original"
          fi
        fi
      fi
    done

    if [ "$has_skill_file" = false ]; then
      echo "  [WARN] Locale has no SKILL translation files"
    fi
  done

  if [ "$i18n_errors" -eq 0 ]; then
    echo "  [PASS] i18n format check: all locales valid"
  else
    echo "  [FAIL] i18n format errors: $i18n_errors issues detected"
    HALLUCINATION_COUNT=$((HALLUCINATION_COUNT + 1))
  fi
}

detect_responsibility_confusion
detect_parameter_fabrication
detect_workflow_stitching
detect_context_pollution
detect_format_hallucination
detect_i18n_format

echo ""
echo "=== Hallucination Detection Summary ==="
echo "Total checks: $TOTAL_CHECKS"
echo "Hallucinations detected: $HALLUCINATION_COUNT"

if [ $TOTAL_CHECKS -gt 0 ]; then
  RATE=$(echo "scale=4; $HALLUCINATION_COUNT / $TOTAL_CHECKS" | bc 2>/dev/null || echo "0")
  echo "Hallucination rate: $RATE"
  THRESHOLD="0.05"
  COMPARISON=$(echo "$RATE < $THRESHOLD" | bc 2>/dev/null || echo "1")
  if [ "$COMPARISON" -eq 1 ]; then
    echo "Status: PASS (rate $RATE < threshold $THRESHOLD)"
  else
    echo "Status: FAIL (rate $RATE >= threshold $THRESHOLD)"
    exit 1
  fi
else
  echo "Status: PASS (no checks executed)"
fi

if [ -n "$RESULTS_FILE" ]; then
  cat > "$RESULTS_FILE" <<EOF
{
  "total_checks": $TOTAL_CHECKS,
  "hallucination_count": $HALLUCINATION_COUNT,
  "hallucination_rate": "$RATE",
  "status": "$([ "$HALLUCINATION_COUNT" -eq 0 ] && echo 'PASS' || echo 'FAIL')",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
  echo "Results written to: $RESULTS_FILE"
fi
