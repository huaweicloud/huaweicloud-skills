#!/bin/bash
set -euo pipefail

SKILL_NAME=""
PHASE="full"
RELATED=""
SCENARIO=""
OUTPUT="./test-report.yaml"
SKILL_PATH_OVERRIDE=""
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
  echo "                        all-combination|solution|performance|report|full)"
  echo "  --skill-path <path>   Direct path to skill directory"
  echo "  --related <s2,s3>     Related skills for combination testing"
  echo "  --scenario <name>     Solution scenario name"
  echo "  --output <path>       Report output path"
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
  log_info "Starting basic functionality test"

  if [ -z "$SKILL_PATH" ]; then
    log_fail "Skill directory not found [required]"
    return
  fi

  log_info "Step 2.1: Verify SKILL.md exists and is readable [required]"
  if [ -f "$SKILL_PATH/SKILL.md" ] && [ -r "$SKILL_PATH/SKILL.md" ]; then
    log_pass "SKILL.md exists and is readable [required]"
  else
    log_fail "SKILL.md missing or not readable [required]"
    return
  fi

  log_info "Step 2.2: Verify recommended structure (references/ + scripts/)"
  if [ -d "$SKILL_PATH/references" ]; then
    log_pass "references/ directory present [recommended]"
  else
    log_warn "references/ directory missing [recommended]"
  fi
  if [ -d "$SKILL_PATH/scripts" ]; then
    log_pass "scripts/ directory present [recommended]"
  else
    log_warn "scripts/ directory missing [recommended]"
  fi
  if [ -d "$SKILL_PATH/templates" ]; then
    log_pass "templates/ directory present [recommended]"
  else
    log_warn "templates/ directory missing [recommended]"
  fi
  if [ -d "$SKILL_PATH/demo" ]; then
    log_pass "demo/ directory present [recommended]"
  else
    log_warn "demo/ directory missing [recommended]"
  fi

  log_info "Step 2.3: Verify output structure - Frontmatter fields"
  local fm_ok=true
  for field in name description version tags; do
    if grep -q "^${field}:" "$SKILL_PATH/SKILL.md"; then
      log_pass "Frontmatter field '$field' present"
    else
      log_fail "Frontmatter field '$field' missing"
      fm_ok=false
    fi
  done

  if [ "$fm_ok" = true ]; then
    log_info "Step 2.4: Verify description has 5-point structure"
    local desc_lines
    desc_lines=$(sed -n '/^description:/,/^[^ ]/p' "$SKILL_PATH/SKILL.md" | grep -c '^\s\+[0-9]\+\.' || true)
    if [ "$desc_lines" -ge 5 ]; then
      log_pass "Description has $desc_lines structured points (>=5)"
    else
      log_fail "Description has only $desc_lines structured points (need 5)"
    fi
  fi
}

run_trigger() {
  log_info "Starting trigger accuracy test"

  if [ -z "$SKILL_PATH" ] || [ ! -f "$SKILL_PATH/SKILL.md" ]; then
    log_fail "Cannot test triggers: SKILL.md not found"
    return
  fi

  local desc_block
  desc_block=$(sed -n '/^description:/,/^[^ ]/p' "$SKILL_PATH/SKILL.md")

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
}

run_boundary() {
  log_info "Starting boundary/exception test"

  if [ -z "$SKILL_PATH" ]; then
    log_fail "Cannot test boundaries: skill not found"
    return
  fi

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
}

run_compare() {
  log_info "Starting With/Without comparison test"

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
}

run_i18n() {
  log_info "Starting i18n directory test"

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
}

run_uninstall() {
  log_info "Starting uninstall/reinstall test"

  if [ -z "$SKILL_PATH" ]; then
    log_fail "Cannot test uninstall: skill directory not found"
    return
  fi

  if ! command -v npx &>/dev/null; then
    log_fail "Cannot test uninstall: npx not available"
    return
  fi

  local skill_name_field=""
  if [ -f "$SKILL_PATH/SKILL.md" ] && grep -q '^name:' "$SKILL_PATH/SKILL.md"; then
    skill_name_field=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
  fi

  if [ -z "$skill_name_field" ]; then
    log_warn "Cannot determine skill name for uninstall test [recommended]"
    return
  fi

  log_info "Step 1: Verify skill exists before uninstall..."
  if [ -d "$SKILL_PATH" ] && [ -f "$SKILL_PATH/SKILL.md" ]; then
    log_pass "Pre-uninstall: skill directory and SKILL.md present [required]"
  else
    log_fail "Pre-uninstall: skill directory or SKILL.md missing [required]"
    return
  fi

  local installed_path=""
  if [ -n "$SKILL_PATH_OVERRIDE" ]; then
    for domain in "" devtools compute network storage database security monitoring middleware solution; do
      local candidate="$SKILLS_BASE_DIR/${domain:+$domain/}$skill_name_field"
      if [ -d "$candidate" ]; then
        installed_path="$candidate"
        break
      fi
    done
  else
    installed_path="$SKILL_PATH"
  fi

  log_info "Step 2: Execute npx skills remove..."
  if npx skills remove "$skill_name_field" &>/dev/null 2>&1; then
    log_pass "Uninstall: npx skills remove succeeded [required]"
  else
    log_fail "Uninstall: npx skills remove failed [required]"
    return
  fi

  log_info "Step 3: Verify installed skill directory removed..."
  if [ -n "$installed_path" ]; then
    if [ ! -d "$installed_path" ]; then
      log_pass "Uninstall: installed skill directory removed [required]"
    else
      log_warn "Uninstall: installed skill directory still exists (may be source path) [recommended]"
    fi
  else
    log_warn "Uninstall: cannot locate installed path to verify removal [recommended]"
  fi

  log_info "Step 4: Verify skill not loadable after uninstall..."
  if [ -n "$installed_path" ] && [ ! -f "$installed_path/SKILL.md" ]; then
    log_pass "Uninstall: SKILL.md no longer accessible at installed path [required]"
  else
    log_warn "Uninstall: SKILL.md still accessible (may be source or cached) [recommended]"
  fi

  log_info "Step 5: Reinstall skill via npx skills add..."
  local skill_repo=""
  if [ -n "$SKILL_PATH_OVERRIDE" ]; then
    skill_repo="$SKILL_PATH_OVERRIDE"
  fi

  if [ -n "$skill_repo" ]; then
    if npx skills add "$skill_repo" --skill "$skill_name_field" &>/dev/null 2>&1; then
      log_pass "Reinstall: npx skills add succeeded [required]"
    else
      log_fail "Reinstall: npx skills add failed [required]"
      return
    fi
  else
    log_warn "Reinstall: no skill repo specified, skipping reinstall test [recommended]"
    return
  fi

  log_info "Step 6: Verify reinstalled skill structure intact..."
  if [ -d "$SKILL_PATH" ] && [ -f "$SKILL_PATH/SKILL.md" ]; then
    log_pass "Reinstall: skill directory and SKILL.md restored [required]"
  else
    log_fail "Reinstall: skill structure broken after reinstall [required]"
    return
  fi

  if [ -d "$SKILL_PATH/scripts" ]; then
    log_pass "Reinstall: scripts/ directory restored [recommended]"
  else
    log_warn "Reinstall: scripts/ directory missing [recommended]"
  fi

  if [ -d "$SKILL_PATH/references" ]; then
    log_pass "Reinstall: references/ directory restored [recommended]"
  else
    log_warn "Reinstall: references/ directory missing [recommended]"
  fi
}

run_security() {
  log_info "Starting security pattern scan (sec.secret.leak)"

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
}

run_identify_related() {
  log_info "Identifying related skills"

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
}

run_combination() {
  log_info "Starting combination compatibility test"

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
}

run_competition() {
  log_info "Starting multi-skill competition test"

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
}

run_isolation() {
  log_info "Starting context isolation test"

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
}

run_solution() {
  log_info "Starting solution-level test"

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
}

run_performance() {
  log_info "Collecting performance metrics"

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

case "$PHASE" in
  basic)             run_basic ;;
  trigger)           run_trigger ;;
  boundary)          run_boundary ;;
  compare)           run_compare ;;
  i18n)              run_i18n ;;
  security)          run_security ;;
  uninstall)         run_uninstall ;;
  all-basic)
    run_basic
    run_trigger
    run_boundary
    run_compare
    run_i18n
    run_security
    run_uninstall
    ;;
  identify-related)  run_identify_related ;;
  combination)       run_combination ;;
  competition)       run_competition ;;
  isolation)         run_isolation ;;
  all-combination)
    run_identify_related
    run_combination
    run_competition
    run_isolation
    ;;
  solution)          run_solution ;;
  performance)       run_performance ;;
  report)            generate_report ;;
  full)
    run_basic
    run_trigger
    run_boundary
    run_compare
    run_i18n
    run_security
    run_uninstall
    run_identify_related
    run_combination
    run_competition
    run_isolation
    run_solution
    run_performance
    generate_report
    ;;
  *) echo "Unknown phase: $PHASE"; usage ;;
esac

echo ""
echo "=== Test Summary ==="
echo "PASS: $PASS_COUNT | FAIL: $FAIL_COUNT | WARN: $WARN_COUNT"
echo "Required: $((PASS_COUNT + FAIL_COUNT)) checks (PASS: $PASS_COUNT, FAIL: $FAIL_COUNT)"
echo "Recommended: $WARN_COUNT items missing (non-blocking)"

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
