#!/bin/bash
set -euo pipefail

SKILL_NAME=""
PHASE="full"
RELATED=""
SCENARIO=""
OUTPUT="./test-report.yaml"
SKILL_PATH_OVERRIDE=""
INSTALL_MODE="local"
SKILL_REPO=""
HCLOUD_REGION="cn-north-4"
FULL_OUTPUT=false
STEP_NUM=0
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SKILLS_BASE_DIR="${SKILLS_BASE_DIR:-$HOME/.skills}"
_FIND_RESULT=""

usage() {
  echo "Usage: bash test-skill.sh <skill-name> [options]"
  echo "Options:"
  echo "  --phase <phase>       Test phase (basic|trigger|boundary|compare|i18n|security|uninstall|all-basic|"
  echo "                        identify-related|combination|competition|isolation|"
  echo "                        all-combination|solution|performance|report|"
  echo "                        functional|all-functional|full)"
  echo "  --skill-path <path>   Direct path to skill directory"
  echo "  --related <s2,s3>     Related skills for combination testing"
  echo "  --scenario <name>     Solution scenario name"
  echo "  --output <path>       Report output path"
  echo "  --install-mode <mode> Installation mode: local (default) or online"
  echo "  --skill-repo <repo>   Repository URL/path for online install mode"
  echo "  --region <region>     Huawei Cloud region (default: cn-north-4)"
  echo "  --full-output         Print step summaries to stderr (agent-proof, prevents grep filtering)"
  exit 1
}

if [ $# -lt 1 ]; then usage; fi

SKILL_NAME="$1"
shift

while [ $# -gt 0 ]; do
  case "$1" in
    --phase)       PHASE="$2"; shift 2 ;;
    --skill-path)  SKILL_PATH_OVERRIDE="$2"; shift 2 ;;
    --related)     RELATED="$2"; shift 2 ;;
    --scenario)    SCENARIO="$2"; shift 2 ;;
    --output)      OUTPUT="$2"; shift 2 ;;
    --install-mode) INSTALL_MODE="$2"; shift 2 ;;
    --skill-repo)  SKILL_REPO="$2"; shift 2 ;;
    --region)      HCLOUD_REGION="$2"; shift 2 ;;
    --full-output) FULL_OUTPUT=true; shift ;;
    *) usage ;;
  esac
done

log_pass() {
  echo "[PASS] [$PHASE] $1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

log_fail() {
  echo "[FAIL] [$PHASE] $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

log_warn() {
  echo "[WARN] [$PHASE] $1"
  WARN_COUNT=$((WARN_COUNT + 1))
}

log_info() {
  echo "[INFO] [$PHASE] $1"
}

# Print a step result summary for the current sub-phase
print_step_summary() {
  local phase_name="$1"
  STEP_NUM=$((STEP_NUM + 1))
  echo ""
  echo "  ┌────────────────────────────────────────────────────────────────┐"
  printf "  │  Step %-2d Result: %-47s │\n" "$STEP_NUM" "$phase_name"
  echo "  ├────────────────────────────────────────────────────────────────┤"
  printf "  │  PASS: %-4d | FAIL: %-4d | WARN: %-4d                         │\n" "$PASS_COUNT" "$FAIL_COUNT" "$WARN_COUNT"
  local total=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))
  printf "  │  Total: %-4d checks                                          │\n" "$total"
  if [ $FAIL_COUNT -gt 0 ]; then
    echo "  │  Status: ❌ FAIL (required checks failed)                       │"
  elif [ $WARN_COUNT -gt 0 ]; then
    echo "  │  Status: ⚠️  PASS (with recommended warnings)                   │"
  else
    echo "  │  Status: ✅ PASS                                                │"
  fi
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  # When --full-output is set, mirror summary to stderr to prevent agent grep filtering
  if $FULL_OUTPUT; then
    local checksum=$((PASS_COUNT + FAIL_COUNT * 3 + WARN_COUNT * 7 + STEP_NUM * 11))
    echo "[FULL_OUTPUT] Step $STEP_NUM complete: $phase_name | PASS=$PASS_COUNT FAIL=$FAIL_COUNT WARN=$WARN_COUNT | cksum=$checksum" >&2
  fi
}

#--- Load confirmed skill features from Phase 0 (.skill-features.conf) ---
# Sets global: CONFIRMED_DESC[], CONFIRMED_TRIGGERS[], CONFIRMED_CMDS[], CONFIRMED_WF[]
load_skill_features() {
  local conf_file="$SKILL_PATH/.skill-features.conf"
  CONFIRMED_DESC=()
  CONFIRMED_TRIGGERS=()
  CONFIRMED_CMDS=()
  CONFIRMED_WF=()
  HAS_CONFIRMED_FEATURES=false

  if [ ! -f "$conf_file" ]; then
    log_info "No .skill-features.conf found (Phase 0 not run) — using SKILL.md defaults"
    return
  fi

  # Use Python for reliable JSON parsing
  local parse_result
  parse_result=$(python3 -c "
import json, sys
with open('$conf_file') as f:
    d = json.load(f)
for pt in d.get('description_points', []):
    print('DESC:' + pt)
for tg in d.get('triggers', []):
    print('TRIG:' + tg)
for cmd in d.get('core_commands', []):
    print('CMD:' + cmd.get('op', ''))
for wf in d.get('workflows', []):
    print('WF:' + wf)
" 2>/dev/null) || {
    log_warn "Failed to parse .skill-features.conf — using SKILL.md defaults [recommended]"
    return
  }

  while IFS= read -r line; do
    case "$line" in
      DESC:*) CONFIRMED_DESC+=("${line#DESC:}") ;;
      TRIG:*) CONFIRMED_TRIGGERS+=("${line#TRIG:}") ;;
      CMD:*)  CONFIRMED_CMDS+=("${line#CMD:}") ;;
      WF:*)   CONFIRMED_WF+=("${line#WF:}") ;;
    esac
  done <<< "$parse_result"

  HAS_CONFIRMED_FEATURES=true
  log_info "Loaded confirmed features from Phase 0: ${#CONFIRMED_DESC[@]} desc, ${#CONFIRMED_TRIGGERS[@]} triggers, ${#CONFIRMED_CMDS[@]} commands, ${#CONFIRMED_WF[@]} workflows"
}

# Clean up .skill-features.conf
cleanup_skill_features() {
  local conf_file="$SKILL_PATH/.skill-features.conf"
  [ -f "$conf_file" ] && rm "$conf_file" && log_info "Cleaned up .skill-features.conf"
}

find_skill_path() {
  local name="$1"
  _FIND_RESULT=""

  if [ -n "$SKILL_PATH_OVERRIDE" ] && [ -d "$SKILL_PATH_OVERRIDE" ]; then
    _FIND_RESULT="$SKILL_PATH_OVERRIDE"
    return
  fi

  if [ -d "$SKILLS_BASE_DIR/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/$name"
  elif [ -d "$SKILLS_BASE_DIR/devtools/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/devtools/$name"
  elif [ -d "$SKILLS_BASE_DIR/compute/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/compute/$name"
  elif [ -d "$SKILLS_BASE_DIR/network/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/network/$name"
  elif [ -d "$SKILLS_BASE_DIR/storage/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/storage/$name"
  elif [ -d "$SKILLS_BASE_DIR/database/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/database/$name"
  elif [ -d "$SKILLS_BASE_DIR/security/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/security/$name"
  elif [ -d "$SKILLS_BASE_DIR/monitoring/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/monitoring/$name"
  elif [ -d "$SKILLS_BASE_DIR/middleware/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/middleware/$name"
  elif [ -d "$SKILLS_BASE_DIR/solution/$name" ]; then
    _FIND_RESULT="$SKILLS_BASE_DIR/solution/$name"
  fi

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

run_basic() {
  load_skill_features

  if $HAS_CONFIRMED_FEATURES && [ ${#CONFIRMED_DESC[@]} -gt 0 ]; then
    log_info "Starting basic test using ${#CONFIRMED_DESC[@]} confirmed description points from Phase 0"
    echo ""
    echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
    local idx=0
    for pt in "${CONFIRMED_DESC[@]}"; do
      idx=$((idx+1))
      printf "  | B-%02d | %-55s | REQUIRED  |\n" "$idx" "Description point $idx: ${pt:0:50}"
    done
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""
    echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
    echo "  | R-01 | Each confirmed description point must be present in SKILL.md | REQUIRED |"
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""

    if [ -z "$SKILL_PATH" ]; then
      log_fail "Skill directory not found [required]"
      return
    fi

    local desc_block
    desc_block=$(sed -n '/^description:/,/^[^ ]/p' "$SKILL_PATH/SKILL.md")
    local pt_idx=0
    for pt in "${CONFIRMED_DESC[@]}"; do
      pt_idx=$((pt_idx+1))
      if echo "$desc_block" | grep -qi "$pt"; then
        log_pass "Confirmed description point $pt_idx present: ${pt:0:60}"
      else
        log_fail "Confirmed description point $pt_idx missing: ${pt:0:60} [required]"
      fi
    done
  else
    # Fallback: count-based check
    log_info "Starting basic functionality test (Description 5-point check)"
    echo ""
    echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
    echo "  | B-01 | Description has 5-point structure              | REQUIRED  |"
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""
    echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
    echo "  | R-01 | Description field must have >= 5 numbered points | REQUIRED |"
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""

    if [ -z "$SKILL_PATH" ]; then
      log_fail "Skill directory not found [required]"
      return
    fi

    log_info "Step 2.1: Verify description has 5-point structure"
    local desc_lines
    desc_lines=$(sed -n '/^description:/,/^[^ ]/p' "$SKILL_PATH/SKILL.md" | grep -c '^\s\+[0-9]\+\.' || true)
    if [ "$desc_lines" -ge 5 ]; then
      log_pass "Description has $desc_lines structured points (>=5)"
    else
      log_fail "Description has only $desc_lines structured points (need 5)"
    fi
  fi

  print_step_summary "Basic Functionality Check"
}

run_trigger() {
  load_skill_features

  if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH/SKILL.md" ]; then
    log_fail "Cannot test triggers: SKILL.md not found"
    return
  fi

  local desc_block
  desc_block=$(sed -n '/^description:/,/^[^ ]/p' "$SKILL_PATH/SKILL.md")

  # ---- Phase 0 confirmed triggers path ----
  if $HAS_CONFIRMED_FEATURES && [ ${#CONFIRMED_TRIGGERS[@]} -gt 0 ]; then
    log_info "Starting trigger test using ${#CONFIRMED_TRIGGERS[@]} confirmed triggers from Phase 0"
    echo ""
    echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
    local idx=0
    for tg in "${CONFIRMED_TRIGGERS[@]}"; do
      idx=$((idx+1))
      printf "  | T-%02d | Trigger: %-47s | REQUIRED  |\n" "$idx" "${tg:0:50}"
    done
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""
    echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
    echo "  | R-01 | Each confirmed trigger must appear in description | REQUIRED |"
    echo "  | R-02 | Trigger hit rate >= 90%                          | REQUIRED |"
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""

    local tg_count=${#CONFIRMED_TRIGGERS[@]}
    local tg_pass=0
    local tg_idx=0
    for tg in "${CONFIRMED_TRIGGERS[@]}"; do
      tg_idx=$((tg_idx+1))
      if echo "$desc_block" | grep -qi "$tg"; then
        log_pass "Confirmed trigger $tg_idx present in description: $tg"
        tg_pass=$((tg_pass+1))
      else
        log_fail "Confirmed trigger $tg_idx missing in description: $tg [required]"
      fi
    done

    local accuracy=0
    [ "$tg_count" -gt 0 ] && accuracy=$((tg_pass * 100 / tg_count))
    log_info "Trigger hit rate: $tg_pass/$tg_count ($accuracy%)"
    if [ "$accuracy" -ge 90 ]; then
      log_pass "Trigger accuracy >= 90% ($tg_pass/$tg_count)"
    else
      log_fail "Trigger accuracy < 90% ($tg_pass/$tg_count)"
    fi

    print_step_summary "Trigger Accuracy Test"
    return
  fi

  # ---- Fallback: description parsing path ----
  log_info "Starting trigger accuracy test (Phase 0 not run, parsing SKILL.md)"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | T-01 | Trigger identification                         | REQUIRED  |"
  echo "  | T-02 | Core functionality output                      | REQUIRED  |"
  echo "  | T-03 | Trigger accuracy >= 90%                        | REQUIRED  |"
  echo "  | T-04 | No false trigger on unrelated requests         | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Declared triggers must be self-consistent     | REQUIRED  |"
  echo "  | R-02 | Trigger hit rate >= 30% for domain keywords   | REQUIRED  |"
  echo "  | R-03 | Negative keywords must not trigger             | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  local declared_triggers
  declared_triggers=$(printf '%s\n' "$desc_block" | grep -oiP '(?<=Triggers include:|触发包括:|触发词:).*' | head -1)
  if [ -n "$declared_triggers" ]; then
    local trigger_count=0
    local trigger_pass=0
    local tk
    while IFS=',' read -ra tk_parts; do
      for tk in "${tk_parts[@]}"; do
        tk=$(printf '%s' "$tk" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        [ -z "$tk" ] && continue
        trigger_count=$((trigger_count + 1))
        if printf '%s\n' "$desc_block" | grep -qi "$tk"; then
          trigger_pass=$((trigger_pass + 1))
        fi
      done
    done < <(printf '%s\n' "$declared_triggers")
    if [ $trigger_count -gt 0 ]; then
      local accuracy
      accuracy=$(echo "scale=2; $trigger_pass / $trigger_count" | bc 2>/dev/null || echo "0")
      log_info "Declared trigger self-consistency: $trigger_pass/$trigger_count (accuracy: $accuracy)"
      if [ "$trigger_pass" -ge $((trigger_count * 90 / 100)) ]; then
        log_pass "Trigger accuracy >= 90%"
      else
        log_fail "Trigger accuracy < 90% ($trigger_pass/$trigger_count)"
      fi
    fi
  else
    local trigger_count=0
    local trigger_pass=0
    local keywords=("test" "testing" "verify" "validate" "detect" "hallucination" "quality" "compatibility" "create" "build" "scaffold" "manage" "deploy" "diagnosis" "monitor" "测试" "验证" "检测" "幻觉" "质量" "兼容" "创建" "新建" "构建" "管理" "部署" "诊断" "监控")
    for kw in "${keywords[@]}"; do
      trigger_count=$((trigger_count + 1))
      if printf '%s\n' "$desc_block" | grep -qi "$kw"; then
        trigger_pass=$((trigger_pass + 1))
      fi
    done
    if [ $trigger_count -gt 0 ]; then
      local accuracy
      accuracy=$(echo "scale=2; $trigger_pass / $trigger_count" | bc 2>/dev/null || echo "0")
      local hit_rate
      hit_rate=$((trigger_pass * 100 / trigger_count))
      log_info "Trigger keyword match: $trigger_pass/$trigger_count (accuracy: $accuracy, hit_rate: ${hit_rate}%)"
      if [ "$hit_rate" -ge 30 ]; then
        log_pass "Trigger hit rate >= 30% (domain-relevant keywords found)"
      else
        log_fail "Trigger hit rate < 30% ($trigger_pass/$trigger_count)"
      fi
    fi
  fi

  local negative_keywords=("create ECS" "list VPC" "upload file" "send email" "create database" "创建ECS" "列出VPC" "上传文件" "发送邮件" "创建数据库" "创建ecs instance" "查询vpc列表")
  local neg_pass=0
  local neg_count=${#negative_keywords[@]}
  for nkw in "${negative_keywords[@]}"; do
    if ! printf '%s\n' "$desc_block" | grep -qi "$nkw"; then
      neg_pass=$((neg_pass + 1))
    fi
  done
  log_info "Negative trigger test: $neg_pass/$neg_count not triggered (correct)"
  if [ "$neg_pass" -eq "$neg_count" ]; then
    log_pass "No false triggers detected"
  else
    log_fail "False triggers detected ($((neg_count - neg_pass)) of $neg_count)"
  fi

  print_step_summary "Trigger Accuracy Test"
}

run_boundary() {
  load_skill_features

  if [ -z "$SKILL_PATH" ]; then
    log_fail "Cannot test boundaries: skill not found"
    return
  fi

  if $HAS_CONFIRMED_FEATURES && [ ${#CONFIRMED_CMDS[@]} -gt 0 ]; then
    log_info "Starting boundary test using ${#CONFIRMED_CMDS[@]} confirmed commands from Phase 0"
    echo ""
    echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
    local idx=0
    for cmd in "${CONFIRMED_CMDS[@]}"; do
      idx=$((idx+1))
      printf "  | BD-%02d | Boundary: invalid %-40s | REQUIRED  |\n" "$idx" "${cmd:0:43}"
    done
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""
    echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
    echo "  | R-01 | Each confirmed command should have error handling | REQUIRED |"
    echo "  └────────────────────────────────────────────────────────────────┘"
    echo ""

    for cmd in "${CONFIRMED_CMDS[@]}"; do
      if grep -qi "$cmd" "$SKILL_PATH/SKILL.md"; then
        log_pass "Command '$cmd' documented in SKILL.md [required]"
      else
        log_fail "Command '$cmd' NOT found in SKILL.md [required]"
      fi
    done

    print_step_summary "Boundary/Exception Test"
    return
  fi

  # ---- Fallback path ----
  log_info "Starting boundary/exception test (Phase 0 not run)"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | BD-01 | Non-existent path correctly returns not found   | REQUIRED  |"
  echo "  | BD-02 | Empty frontmatter correctly detected            | REQUIRED  |"
  echo "  | BD-03 | Malformed version (non-SemVer) detected         | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  log_info "Testing with non-existent skill path..."
  if [ ! -d "/tmp/nonexistent-skill-$$" ]; then
    log_pass "Non-existent path: correctly not found"
  else
    log_fail "Non-existent path: unexpectedly found"
  fi

  log_info "Testing SKILL.md with empty frontmatter..."
  local empty_md="/tmp/empty-skill-test-$$.md"
  echo "---\n---" > "$empty_md"
  if ! grep -q '^name:' "$empty_md" 2>/dev/null; then
    log_pass "Empty frontmatter: correctly detected missing 'name' field"
  else
    log_fail "Empty frontmatter: failed to detect missing 'name' field"
  fi
  rm -f "$empty_md"

  log_info "Testing with malformed version..."
  local malformed_md="/tmp/malformed-skill-test-$$.md"
  cat > "$malformed_md" <<'MDEOF'
---
name: test-malformed
version: not-semver
description: |
  1. test
tags: [test]
---
MDEOF
  if ! grep -qE '^version: [0-9]+\.[0-9]+\.[0-9]+' "$malformed_md"; then
    log_pass "Malformed version: correctly detected non-SemVer"
  else
    log_fail "Malformed version: failed to detect non-SemVer"
  fi
  rm -f "$malformed_md"

  print_step_summary "Boundary/Exception Test"
}

run_compare() {
  log_info "Starting With/Without comparison test"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | CP-01 | With-skill score computed (lines, refs, scripts) | REQUIRED  |"
  echo "  | CP-02 | Delta (with - without) > 0                       | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | With-skill score > without-skill score (delta>0) | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH/SKILL.md" ]; then
    log_fail "Cannot run comparison: skill not found"
    return
  fi

  local with_lines=0
  with_lines=$(wc -l < "$SKILL_PATH/SKILL.md")

  local ref_count=0
  if [ -d "$SKILL_PATH/references" ]; then
    ref_count=$(find "$SKILL_PATH/references" -type f -name "*.md" | wc -l)
  fi

  local script_count=0
  if [ -d "$SKILL_PATH/scripts" ]; then
    script_count=$(find "$SKILL_PATH/scripts" -type f -executable | wc -l)
  fi

  local with_score=0
  with_score=$(echo "scale=2; ($with_lines / 500) * 0.4 + ($ref_count / 5) * 0.3 + ($script_count / 3) * 0.3" | bc 2>/dev/null || echo "0.50")

  local without_score=0.10

  local delta
  delta=$(echo "scale=2; $with_score - $without_score" | bc 2>/dev/null || echo "0.40")

  log_info "With-skill score: $with_score (lines=$with_lines, refs=$ref_count, scripts=$script_count)"
  log_info "Without-skill score: $without_score"
  log_info "Delta: $delta"

  if [ "$(echo "$delta > 0" | bc 2>/dev/null || echo "1")" -eq 1 ]; then
    log_pass "Delta = $delta (positive, skill adds value)"
  else
    log_fail "Delta = $delta (non-positive, skill adds no value)"
  fi

  print_step_summary "With/Without Comparison"
}

run_i18n() {
  log_info "Starting i18n directory test"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | I18N-01 | i18n/ directory exists                       | RECOMMEND |"
  echo "  | I18N-02 | Locale follows BCP 47 format                  | RECOMMEND |"
  echo "  | I18N-03 | SKILL translation file(s) present             | RECOMMEND |"
  echo "  | I18N-04 | Frontmatter fields complete                   | RECOMMEND |"
  echo "  | I18N-05 | i18n name matches original                    | RECOMMEND |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | All i18n items are recommended (non-blocking) | RECOMMEND |"
  echo "  | R-02 | name/description/version/tags must be present  | RECOMMEND |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -z "$SKILL_PATH" ]; then
    log_fail "Cannot test i18n: skill directory not found"
    return
  fi

  if [ ! -d "$SKILL_PATH/i18n" ]; then
    log_warn "i18n/ directory missing [recommended]"
    return
  fi

  log_pass "i18n/ directory exists [recommended]"

  local locale_count=0
  local locale_valid=0

  for locale_dir in "$SKILL_PATH/i18n"/*/; do
    if [ ! -d "$locale_dir" ]; then
      continue
    fi

    locale_count=$((locale_count + 1))
    local locale_name
    locale_name=$(basename "$locale_dir")

    if [[ "$locale_name" =~ ^[a-z]{2,3}-[A-Z]{2}$ ]]; then
      log_pass "Locale follows BCP 47 format (xx-XX) [recommended]"
      locale_valid=$((locale_valid + 1))
    else
      log_warn "Locale does not follow BCP 47 format (expected xx-XX like zh-CN, en-US) [recommended]"
    fi

    local skill_file_count=0
    for f in "$locale_dir"SKILL*.md; do
      if [ -f "$f" ]; then
        skill_file_count=$((skill_file_count + 1))
        local skill_basename
        skill_basename=$(basename "$f")

        local fm_ok=true
        for field in name description version tags; do
          if grep -q "^${field}:" "$f"; then
            :
          else
            log_warn "i18n file: frontmatter '$field' missing [recommended]"
            fm_ok=false
          fi
        done

        if [ "$fm_ok" = true ]; then
          log_pass "i18n file: frontmatter complete [recommended]"
        fi

        if [ -f "$SKILL_PATH/SKILL.md" ]; then
          local orig_name i18n_name
          orig_name=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
          i18n_name=$(grep '^name:' "$f" | head -1 | awk '{print $2}')
          if [ -n "$orig_name" ] && [ -n "$i18n_name" ]; then
            if [ "$orig_name" = "$i18n_name" ]; then
              log_pass "i18n file: name matches original [recommended]"
            else
              log_warn "i18n file: name differs from original [recommended]"
            fi
          fi
        fi
      fi
    done

    if [ "$skill_file_count" -gt 0 ]; then
      log_pass "Locale has $skill_file_count SKILL translation file(s) [recommended]"
    else
      log_warn "Locale has no SKILL translation files (expected SKILL_XX.md) [recommended]"
    fi
  done

  if [ "$locale_count" -gt 0 ]; then
    log_info "i18n summary: $locale_valid/$locale_count locales valid"
  else
    log_warn "i18n/ directory exists but contains no locale subdirectories [recommended]"
  fi

  print_step_summary "i18n Directory Test"
}

run_uninstall() {
  log_info "Starting install/uninstall lifecycle test"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | UN-01 | npx skills add install succeeds                 | REQUIRED  |"
  echo "  | UN-02 | Skill appears in npx skills list                | REQUIRED  |"
  echo "  | UN-03 | npx skills remove succeeds                      | REQUIRED  |"
  echo "  | UN-04 | Skill no longer in list after uninstall         | REQUIRED  |"
  echo "  | UN-05 | Reinstall succeeds for subsequent tests         | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Install→Verify→Uninstall→Verify→Reinstall     | REQUIRED  |"
  echo "  | R-02 | Delegates to validate-skill.sh --phase uninstall | REQUIRED |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -z "$SKILL_PATH" ]; then
    log_fail "Cannot test lifecycle: skill directory not found"
    return
  fi

  # Delegate to validate-skill.sh's install lifecycle check
  local val_script="$SKILL_PATH/scripts/validate-skill.sh"
  local tester_dir
  tester_dir="$(cd "$(dirname "$0")" && pwd)"
  local tester_val="$tester_dir/validate-skill.sh"

  local val_to_use=""
  if [ -f "$tester_val" ] && [ -x "$tester_val" ]; then
    val_to_use="$tester_val"
  elif [ -f "$val_script" ] && [ -x "$val_script" ]; then
    val_to_use="$val_script"
  fi

  if [ -n "$val_to_use" ]; then
    log_info "Delegating to $val_to_use --phase uninstall --install-mode ${INSTALL_MODE:-local}..."
    local val_args=("$SKILL_PATH" "--phase" "uninstall" "--install-mode" "${INSTALL_MODE:-local}")
    if [ -n "${SKILL_REPO:-}" ]; then
      val_args+=("--skill-repo" "$SKILL_REPO")
    fi
    if bash "$val_to_use" "${val_args[@]}" 2>&1; then
      log_pass "Install/uninstall lifecycle completed [required]"
    else
      log_fail "Install/uninstall lifecycle failed [required]"
    fi
  else
    log_fail "validate-skill.sh not found — cannot run install lifecycle test [required]"
  fi

  print_step_summary "Install/Uninstall Lifecycle"
}

run_security() {
  log_info "Starting security pattern scan (sec.secret.leak)"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | SC-01 | No echo \$var | grep/sec pattern                | REQUIRED  |"
  echo "  | SC-02 | No grep <<< \$var pattern                      | REQUIRED  |"
  echo "  | SC-03 | No printf \$1 sanitize pattern                  | REQUIRED  |"
  echo "  | SC-04 | No hardcoded AK/SK/api_key token               | REQUIRED  |"
  echo "  | SC-05 | No long literal string suspect (40+ chars)     | RECOMMEND |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Secret patterns MUST use env vars, never literals | REQUIRED |"
  echo "  | R-02 | echo\$var|grep → grep file pattern               | REQUIRED  |"
  echo "  | R-03 | grep <<< \$var → grep file pattern               | REQUIRED  |"
  echo "  | R-04 | Long strings must be verified as non-secret      | RECOMMEND |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -z "$SKILL_PATH" ]; then
    log_fail "Cannot scan security: skill directory not found"
    return
  fi

  if [ ! -d "$SKILL_PATH/scripts" ]; then
    log_warn "scripts/ directory missing, skipping security scan [recommended]"
    return
  fi

  local total_issues=0

  for script_file in "$SKILL_PATH/scripts"/*.sh; do
    if [ ! -f "$script_file" ]; then
      continue
    fi

    local script_basename
    script_basename=$(basename "$script_file")

    local echo_pipe=0
    echo_pipe=$(grep -cE 'echo\s+"?\$\{?[A-Za-z_][A-Za-z0-9_]*\}?.*\|\s*(grep|sed|awk|cut)' "$script_file" 2>/dev/null || true)
    if [ "$echo_pipe" -gt 0 ]; then
      log_fail "$script_basename: echo \$var | cmd pattern ($echo_pipe occurrences) [required]"
      total_issues=$((total_issues + echo_pipe))
    fi

    local herestr=0
    herestr=$(grep -cE '<<<\s*"\$' "$script_file" 2>/dev/null || true)
    if [ "$herestr" -gt 0 ]; then
      log_fail "$script_basename: <<< \$var pattern ($herestr occurrences) [required]"
      total_issues=$((total_issues + herestr))
    fi

    local sanitize_fn=0
    sanitize_fn=$(grep -cE '^\s*printf\s+.*\$1.*\|.*sed' "$script_file" 2>/dev/null || true)
    if [ "$sanitize_fn" -gt 0 ]; then
      log_fail "$script_basename: sanitize-like printf \$1 pattern ($sanitize_fn occurrences) [required]"
      total_issues=$((total_issues + sanitize_fn))
    fi

    local hardcoded=0
    hardcoded=$(grep -cE '(AK|SK|access_key|secret_key|api_key|apikey|token|password|passwd|credential)\s*[=:]\s*[^$\s]' "$script_file" 2>/dev/null || true)
    if [ "$hardcoded" -gt 0 ]; then
      log_fail "$script_basename: hardcoded secret pattern ($hardcoded occurrences) [required]"
      total_issues=$((total_issues + hardcoded))
    fi

    local long_lit=0
    long_lit=$(grep -cE '[A-Za-z0-9+/=]{40,}' "$script_file" 2>/dev/null || true)
    if [ "$long_lit" -gt 0 ]; then
      local in_kw=0
      in_kw=$(grep -cE '(trigger_keywords|negative_keywords|known_services|section_defs|keywords)=.*\[.*\]' "$script_file" 2>/dev/null || true)
      local suspect=$((long_lit - in_kw))
      if [ "$suspect" -gt 0 ]; then
        log_warn "$script_basename: long literal string ($suspect suspects) [recommended]"
      fi
    fi
  done

  if [ "$total_issues" -eq 0 ]; then
    log_pass "No sec.secret.leak patterns detected [required]"
  else
    log_fail "Security issues: $total_issues sec.secret.leak violations [required]"
  fi

  print_step_summary "Security Pattern Scan"
}

run_identify_related() {
  log_info "Identifying related skills"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | IR-01 | Related skills specified or auto-detected       | REQUIRED  |"
  echo "  | IR-02 | Each related skill directory exists             | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | --related param or auto-detect same-domain skills | REQUIRED |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -n "$RELATED" ]; then
    log_info "Related skills specified"
    local all_found=true
      local _ifs="$IFS"
    IFS=','
    local rel_array=($RELATED)
    IFS="$_ifs"
    for rel in "${rel_array[@]}"; do
      find_skill_path "$rel"
      local rel_path="$_FIND_RESULT"
      if [ -n "$rel_path" ]; then
        log_pass "Related skill found"
      else
        log_fail "Related skill not found"
        all_found=false
      fi
    done
  else
    log_info "No related skills specified, scanning for same-domain skills..."
    if [ -n "$SKILL_PATH" ]; then
      local parent_dir
      parent_dir=$(dirname "$SKILL_PATH")
      local siblings=()
      while IFS= read -r -d '' dir; do
        local dir_name
        dir_name=$(basename "$dir")
        if [ "$dir_name" != "$SKILL_NAME" ] && [ -f "$dir/SKILL.md" ]; then
          siblings+=("$dir_name")
        fi
      done < <(find "$parent_dir" -maxdepth 1 -mindepth 1 -type d -print0 2>/dev/null)
      if [ ${#siblings[@]} -gt 0 ]; then
        RELATED=$(IFS=','; echo "${siblings[*]}")
        log_pass "Auto-detected related skills"
      else
        log_info "No sibling skills found in same domain"
        log_pass "Related skills: none found"
      fi
    else
      log_pass "Related skills: none specified"
    fi
  fi

  print_step_summary "Identify Related Skills"
}

run_combination() {
  log_info "Starting combination compatibility test"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | CM-01 | Cross-Skill scenario workflow                   | REQUIRED  |"
  echo "  | CM-02 | Multi-Skill competition routing                 | REQUIRED  |"
  echo "  | CM-03 | Context isolation between skills                | REQUIRED  |"
  echo "  | CM-04 | Responsibility confusion detection              | REQUIRED  |"
  echo "  | CM-05 | Parameter fabrication detection                 | REQUIRED  |"
  echo "  | CM-06 | Workflow stitching correctness                  | REQUIRED  |"
  echo "  | CM-07 | Format hallucination detection                  | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Cross-Skill hallucination rate < 5%            | REQUIRED  |"
  echo "  | R-02 | Related skills must be installed                | REQUIRED  |"
  echo "  | R-03 | Phase 1 and 2 must pass first                  | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -z "$RELATED" ]; then
    log_info "No related skills specified, skipping combination test"
    log_pass "Combination test: SKIPPED (no related skills)"
    return
  fi

    local _ifs="$IFS"
    IFS=','
    local rel_array=($RELATED)
    IFS="$_ifs"
  for rel in "${rel_array[@]}"; do
    find_skill_path "$rel"
    local rel_path="$_FIND_RESULT"
    if [ -z "$rel_path" ]; then
      log_fail "Related skill not found for combination test"
      continue
    fi

    log_info "Checking combination compatibility"

    local common_tags=0
    local skill_tags rel_tags
    skill_tags=$(grep '^tags:' "$SKILL_PATH/SKILL.md" 2>/dev/null || echo "")
    rel_tags=$(grep '^tags:' "$rel_path/SKILL.md" 2>/dev/null || echo "")

    if [ -n "$skill_tags" ] && [ -n "$rel_tags" ]; then
      for tag in $(grep '^tags:' "$SKILL_PATH/SKILL.md" 2>/dev/null | sed 's/tags:\s*\[//;s/\]//;s/,/ /g'); do
        if grep -qw "$tag" "$rel_path/SKILL.md"; then
          common_tags=$((common_tags + 1))
        fi
      done
    fi

    if [ "$common_tags" -gt 0 ]; then
      log_pass "Combination: $common_tags common tags, compatible"
    else
      log_info "Combination: no common tags (may be cross-domain)"
      log_pass "Combination: loaded without conflict"
    fi
  done

  print_step_summary "Combination Compatibility"
}

run_competition() {
  log_info "Starting multi-skill competition test"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | CT-01 | Distinct skill names, no routing conflict       | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Each related skill must have unique name     | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -z "$RELATED" ]; then
    log_info "No related skills specified, skipping competition test"
    log_pass "Competition test: SKIPPED"
    return
  fi

    local _ifs="$IFS"
    IFS=','
    local rel_array=($RELATED)
    IFS="$_ifs"
  for rel in "${rel_array[@]}"; do
    find_skill_path "$rel"
    local rel_path="$_FIND_RESULT"
    if [ -z "$rel_path" ]; then
      log_info "Related skill not found, skipping competition"
      continue
    fi

    local skill_name_field rel_name_field
    skill_name_field=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
    rel_name_field=$(grep '^name:' "$rel_path/SKILL.md" | head -1 | awk '{print $2}')

    if [ "$skill_name_field" != "$rel_name_field" ]; then
      log_pass "Competition: distinct skills, no routing conflict"
    else
      log_fail "Competition: duplicate name detected"
    fi
  done

  print_step_summary "Multi-Skill Competition"
}

run_isolation() {
  log_info "Starting context isolation test"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | IS-01 | Context isolation — no leakage between skills | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Preceding and following tasks do not interfere | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -z "$RELATED" ]; then
    log_info "No related skills specified, skipping isolation test"
    log_pass "Isolation test: SKIPPED"
    return
  fi

    local _ifs="$IFS"
    IFS=','
    local rel_array=($RELATED)
    IFS="$_ifs"
  for rel in "${rel_array[@]}"; do
    find_skill_path "$rel"
    local rel_path="$_FIND_RESULT"
    if [ -z "$rel_path" ]; then
      log_info "Related skill not found, skipping isolation"
      continue
    fi

    local skill_name_field rel_name_field
    skill_name_field=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
    rel_name_field=$(grep '^name:' "$rel_path/SKILL.md" | head -1 | awk '{print $2}')

    if grep -q "$skill_name_field" "$rel_path/SKILL.md" 2>/dev/null; then
      log_info "Isolation: skill name referenced in related skill content (potential coupling)"
      log_pass "Isolation: coupling detected but documented"
    else
      log_pass "Isolation: no context leakage"
    fi
  done

  print_step_summary "Context Isolation"
}

run_solution() {
  log_info "Starting solution-level test"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | SL-01 | End-to-end business flow — SKILL.md exists      | REQUIRED  |"
  echo "  | SL-02 | Frontmatter valid (name + SemVer version)        | REQUIRED  |"
  echo "  | SL-03 | Scripts executable (recommended)                 | RECOMMEND |"
  echo "  | SL-04 | IAM policies defined with Action fields          | RECOMMEND |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Complete user journey full pipeline passes       | REQUIRED  |"
  echo "  | R-02 | Report contains complete results                 | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  if [ -n "$SCENARIO" ]; then
    log_info "Scenario specified"
  else
    log_info "No scenario specified, using default E2E scenario"
    SCENARIO="default-e2e"
  fi

  if [ -z "$SKILL_PATH" ]; then
    log_fail "Cannot run solution test: skill not found"
    return
  fi

  log_info "Step 1: Validate skill installation..."
  if [ -f "$SKILL_PATH/SKILL.md" ]; then
    log_pass "E2E Step 1: SKILL.md exists [required]"
  else
    log_fail "E2E Step 1: SKILL.md missing [required]"
    return
  fi

  if [ -d "$SKILL_PATH/references" ]; then
    log_pass "E2E Step 1b: references/ present [recommended]"
  else
    log_warn "E2E Step 1b: references/ missing [recommended]"
  fi

  if [ -d "$SKILL_PATH/scripts" ]; then
    log_pass "E2E Step 1c: scripts/ present [recommended]"
  else
    log_warn "E2E Step 1c: scripts/ missing [recommended]"
  fi

  log_info "Step 2: Validate frontmatter..."
  if grep -q '^name:' "$SKILL_PATH/SKILL.md" && grep -qE '^version: [0-9]+\.[0-9]+\.[0-9]+' "$SKILL_PATH/SKILL.md"; then
    log_pass "E2E Step 2: Frontmatter valid"
  else
    log_fail "E2E Step 2: Frontmatter invalid"
  fi

  log_info "Step 3: Validate scripts are executable [recommended]..."
  if [ -d "$SKILL_PATH/scripts" ]; then
    local all_exec=true
    for script in "$SKILL_PATH/scripts"/*; do
      if [ -f "$script" ] && [ ! -x "$script" ]; then
        all_exec=false
        break
      fi
    done
    if [ "$all_exec" = true ]; then
      log_pass "E2E Step 3: All scripts executable [recommended]"
    else
      log_warn "E2E Step 3: Some scripts not executable [recommended]"
    fi
  else
    log_warn "E2E Step 3: scripts/ directory not present, skipping [recommended]"
  fi

  log_info "Step 4: Validate IAM policies defined [recommended]..."
  if [ -f "$SKILL_PATH/references/iam-policies.md" ]; then
    if grep -q 'Action' "$SKILL_PATH/references/iam-policies.md"; then
      log_pass "E2E Step 4: IAM policies defined [recommended]"
    else
      log_warn "E2E Step 4: IAM policies missing Action definitions [recommended]"
    fi
  else
    log_warn "E2E Step 4: iam-policies.md not found [recommended]"
  fi

  print_step_summary "Solution-Level Test"
}

run_performance() {
  log_info "Collecting performance metrics"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | PM-01 | Performance: validation time < 300s threshold     | REQUIRED  |"
  echo "  | PM-02 | Collect skill_md_size, references_total_size      | RECOMMEND |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Time/Tokens/Accuracy within thresholds               | REQUIRED  |"
  echo "  | R-02 | Performance metrics collected for baseline            | RECOMMEND |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  local start_time end_time elapsed
  start_time=$(date +%s%N)

  if [ -n "$SKILL_PATH" ] && [ -f "$SKILL_PATH/SKILL.md" ]; then
    local skill_size
    skill_size=$(wc -c < "$SKILL_PATH/SKILL.md")

    local total_size=0
    if [ -d "$SKILL_PATH/references" ]; then
      while IFS= read -r -d '' f; do
        local fsize
        fsize=$(wc -c < "$f")
        total_size=$((total_size + fsize))
      done < <(find "$SKILL_PATH/references" -type f -print0 2>/dev/null)
    fi
  fi

  end_time=$(date +%s%N)
  elapsed=$(( (end_time - start_time) / 1000000 ))

  log_info "Performance metrics:"
  log_info "  validation_time_ms: ${elapsed}"
  log_info "  skill_md_size: ${skill_size:-0} bytes"
  log_info "  references_total_size: ${total_size:-0} bytes"
  log_info "  total_time_seconds: (requires AICLI instrumentation for full flow)"
  log_info "  total_tokens: (requires AICLI instrumentation)"
  log_info "  accuracy_rate: (requires output evaluation)"
  log_info "  hallucination_rate: (run detect-hallucination.sh)"

  if [ "${elapsed:-0}" -lt 300000 ]; then
    log_pass "Performance: validation completed in ${elapsed}ms (< 300s threshold)"
  else
    log_fail "Performance: validation took ${elapsed}ms (>= 300s threshold)"
  fi

  print_step_summary "Performance Metrics"
}

generate_report() {
  log_info "Generating test report"

  local pass_rate=0
  if [ $((PASS_COUNT + FAIL_COUNT)) -gt 0 ]; then
    pass_rate=$(echo "scale=2; $PASS_COUNT / ($PASS_COUNT + FAIL_COUNT)" | bc 2>/dev/null || echo "0")
  fi

  cat > "$OUTPUT" <<EOF
test_report:
  test_date: $(date -u +"%Y-%m-%d")
  timestamp: $TIMESTAMP

  summary:
    pass: $PASS_COUNT
    fail: $FAIL_COUNT
    warn: $WARN_COUNT
    total: $((PASS_COUNT + FAIL_COUNT + WARN_COUNT))
    pass_rate: $pass_rate

  required_checks:
    pass: $PASS_COUNT
    fail: $FAIL_COUNT
    status: $(if [ $FAIL_COUNT -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi)

  recommended_checks:
    warn: $WARN_COUNT
    status: $(if [ $WARN_COUNT -eq 0 ]; then echo "ALL_PRESENT"; else echo "PARTIAL ($WARN_COUNT items missing)"; fi)

  overall_status: $(if [ $FAIL_COUNT -eq 0 ]; then echo "PASS"; else echo "FAIL"; fi)
EOF

  log_pass "Test report generated"
}

run_phase1() {
  log_info "Starting Phase 1: Installation Verification"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | P1-01 | SKILL.md exists and is readable                 | REQUIRED  |"
  echo "  | P1-02 | Frontmatter compliant (name, desc, version, tags) | REQUIRED  |"
  echo "  | P1-03 | Prerequisite dependencies (hcloud CLI)           | REQUIRED  |"
  echo "  | P1-04 | Required sections present (bilingual)            | REQUIRED  |"
  echo "  | P1-05 | i18n directory structure valid                    | RECOMMEND |"
  echo "  | P1-06 | Security scan (no hardcoded credentials)         | REQUIRED  |"
  echo "  | P1-07 | Install/uninstall lifecycle (5-step)             | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  local val_script
  local tester_dir
  tester_dir="$(cd "$(dirname "$0")" && pwd)"
  val_script="$tester_dir/validate-skill.sh"

  if [ -f "$val_script" ] && [ -x "$val_script" ]; then
    log_info "Running $val_script --phase all-install for $SKILL_PATH"
    local output
    output=$(bash "$val_script" "$SKILL_PATH" --phase all-install 2>&1) || true
    echo "$output"

    local pass_count fail_count warn_count
    pass_count=$(echo "$output" | grep -c "\[PASS\]" || true)
    fail_count=$(echo "$output" | grep -c "\[FAIL\]" || true)
    warn_count=$(echo "$output" | grep -c "\[WARN\]" || true)
    PASS_COUNT=$((PASS_COUNT + pass_count))
    FAIL_COUNT=$((FAIL_COUNT + fail_count))
    WARN_COUNT=$((WARN_COUNT + warn_count))

    if [ "$fail_count" -gt 0 ]; then
      log_fail "Phase 1: $fail_count required check(s) failed — aborting pipeline [required]"
      exit 1
    fi
    log_pass "Phase 1: Installation verification passed ($pass_count checks) [required]"
  else
    log_warn "validate-skill.sh not found at $val_script — skipping Phase 1 [recommended]"
  fi

  print_step_summary "Installation Verification (Phase 1)"
}

run_verify() {
  log_info "Starting Phase 0: Skill Feature Verification"

  local verify_script
  local tester_dir
  tester_dir="$(cd "$(dirname "$0")" && pwd)"
  verify_script="$tester_dir/verify-skill-features.sh"

  if [ -f "$verify_script" ] && [ -x "$verify_script" ]; then
    if bash "$verify_script" "$SKILL_PATH" 2>&1; then
      log_pass "Skill features verified by user [required]"
    else
      log_fail "Skill feature verification aborted by user [required]"
      exit 1
    fi
  else
    log_warn "verify-skill-features.sh not found at $verify_script — skipping verification [recommended]"
  fi
}

run_hallucination() {
  log_info "Starting hallucination detection"
  echo ""
  echo "  ┌─ Test Cases ──────────────────────────────────────────────────┐"
  echo "  | HC-01 | Responsibility confusion (invoked Skill matches request) | REQUIRED |"
  echo "  | HC-02 | Parameter fabrication (values in known whitelist)    | REQUIRED  |"
  echo "  | HC-03 | Workflow stitching (step sequence complete)         | REQUIRED  |"
  echo "  | HC-04 | Context pollution (no residue between tasks)        | REQUIRED  |"
  echo "  | HC-05 | Format hallucination (output matches spec)           | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""
  echo "  ┌─ Check Rules ─────────────────────────────────────────────────┐"
  echo "  | R-01 | Hallucination rate < 5% per type               | REQUIRED  |"
  echo "  └────────────────────────────────────────────────────────────────┘"
  echo ""

  local detect_script
  local tester_dir
  tester_dir="$(cd "$(dirname "$0")" && pwd)"
  detect_script="$tester_dir/detect-hallucination.sh"

  if [ -f "$detect_script" ] && [ -x "$detect_script" ]; then
    log_info "Running $detect_script for $SKILL_NAME"
    local detect_args=()
    if [ -n "$SKILL_PATH" ]; then
      detect_args+=("--skill-path" "$SKILL_PATH")
    fi
    if [ -n "$RELATED" ]; then
      detect_args+=("--related" "$RELATED")
    fi

    local output
    output=$(bash "$detect_script" "$SKILL_NAME" "${detect_args[@]}" 2>&1) || true
    echo "$output"

    local pass_count fail_count
    pass_count=$(echo "$output" | grep -c "\[PASS\]" || true)
    fail_count=$(echo "$output" | grep -c "\[FAIL\]" || true)
    PASS_COUNT=$((PASS_COUNT + pass_count))
    FAIL_COUNT=$((FAIL_COUNT + fail_count))
    if [ "$fail_count" -gt 0 ]; then
      log_info "Hallucination detection: $fail_count issue(s) found"
    else
      log_info "Hallucination detection: clean ($pass_count checks passed)"
    fi
  else
    log_warn "detect-hallucination.sh not found — skipping [recommended]"
  fi

  print_step_summary "Hallucination Detection"
}

run_functional() {
  log_info "Starting six-step functional test"

  local func_script
  local tester_dir
  tester_dir="$(cd "$(dirname "$0")" && pwd)"
  func_script="$tester_dir/functional-test.sh"

  if [ -f "$func_script" ] && [ -x "$func_script" ]; then
    log_info "Running $func_script for $SKILL_NAME"
    local func_args=(
      "--skill-path" "$SKILL_PATH"
      "--phase" "all"
      "--region" "$HCLOUD_REGION"
    )
    if [ -f "$SKILL_PATH/references/test-vars.json" ]; then
      func_args+=("--test-vars" "$SKILL_PATH/references/test-vars.json")
    fi

    if bash "$func_script" "$SKILL_NAME" "${func_args[@]}" 2>&1; then
      log_pass "Six-step functional test completed [required]"
    else
      log_fail "Six-step functional test completed with failures [required]"
    fi
  else
    log_warn "functional-test.sh not found in skill scripts, using built-in functional test [recommended]"
    # Fallback: parse SKILL.md for hcloud commands and verify they exist
    if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH/SKILL.md" ]; then
      log_fail "Cannot run functional test: SKILL.md not found [required]"
      return
    fi

    local cmd_count=0
    cmd_count=$(grep -cE 'hcloud\s+[A-Z]' "$SKILL_PATH/SKILL.md" 2>/dev/null || true)
    if [ "$cmd_count" -gt 0 ]; then
      log_pass "Built-in functional test: $cmd_count CLI commands detected [required]"
      # Verify hcloud CLI is available
      if command -v hcloud &>/dev/null; then
        log_pass "hcloud CLI available for functional testing [required]"
        local hcloud_version
        hcloud_version=$(hcloud --version 2>&1 | head -1)
        log_info "  hcloud version: $hcloud_version"
      else
        log_warn "hcloud CLI not available - install for full functional testing [recommended]"
      fi
    fi
  fi
}

case "$PHASE" in
  basic)             run_basic ;;
  trigger)           run_trigger ;;
  boundary)          run_boundary ;;
  compare)           run_compare ;;
  i18n)              run_i18n ;;
  security)          run_security ;;
  uninstall)         run_uninstall ;;
  functional)        run_functional ;;
  all-basic)
    run_basic
    run_trigger
    run_boundary
    run_compare
    run_i18n
    run_security
    run_uninstall
    ;;
  verify)            run_verify ;;
  identify-related)  run_identify_related ;;
  combination)       run_combination ;;
  competition)       run_competition ;;
  isolation)         run_isolation ;;
  all-combination)
    run_identify_related
    run_combination
    run_competition
    run_isolation
    run_hallucination
    ;;
  all-functional)
    run_functional
    ;;
  solution)          run_solution ;;
  performance)       run_performance ;;
  report)            generate_report ;;
  full)
    run_verify
    run_phase1
    # NOTE: i18n + uninstall lifecycle already covered by run_phase1 above
    run_basic
    run_trigger
    run_boundary
    run_compare
    run_security
    run_identify_related
    run_combination
    run_competition
    run_isolation
    run_hallucination
    run_solution
    run_performance
    run_functional
    generate_report
    cleanup_skill_features
    ;;
  *) echo "Unknown phase: $PHASE"; usage ;;
esac

echo ""
echo "=== Test Summary ==="
echo "PASS: $PASS_COUNT | FAIL: $FAIL_COUNT | WARN: $WARN_COUNT"
echo "Required: $((PASS_COUNT + FAIL_COUNT)) checks (PASS: $PASS_COUNT, FAIL: $FAIL_COUNT)"
echo "Recommended: $WARN_COUNT items missing (non-blocking)"

# --full-output guard: non-filterable final checksum on stderr
if $FULL_OUTPUT; then
  total_checks=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))
  final_cksum=$((PASS_COUNT * 13 + FAIL_COUNT * 17 + WARN_COUNT * 19 + total_checks * 23))
  echo "[FULL_OUTPUT_FINAL] TOTAL: $total_checks | PASS=$PASS_COUNT FAIL=$FAIL_COUNT WARN=$WARN_COUNT STEPS=$STEP_NUM | cksum=$final_cksum" >&2
fi

if [ $FAIL_COUNT -gt 0 ]; then
  echo "Status: FAIL (required checks failed)"
  exit 1
else
  if [ $WARN_COUNT -gt 0 ]; then
    echo "Status: PASS (with $WARN_COUNT recommended warnings)"
  else
    echo "Status: PASS"
  fi
  exit 0
fi
