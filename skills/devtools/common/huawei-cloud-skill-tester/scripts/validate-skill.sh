#!/bin/bash
set -euo pipefail

SKILL_PATH=""
PHASE="all-install"
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
RESULTS=()

usage() {
  echo "Usage: bash validate-skill.sh <skill-path> [--phase <phase>]"
  echo "Phases: install, frontmatter, dependency, language, sections, i18n, security, uninstall, all-install"
  exit 1
}

if [ $# -lt 1 ]; then usage; fi

SKILL_PATH="$1"
shift

while [ $# -gt 0 ]; do
  case "$1" in
    --phase) PHASE="$2"; shift 2 ;;
    *) usage ;;
  esac
done

if [ ! -d "$SKILL_PATH" ]; then
  echo "[FAIL] Skill path does not exist"
  exit 1
fi

check_pass() {
  echo "[PASS] $1"
  PASS_COUNT=$((PASS_COUNT + 1))
  RESULTS+=("PASS|$1")
}

check_fail() {
  echo "[FAIL] $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  RESULTS+=("FAIL|$1")
}

check_warn() {
  echo "[WARN] $1"
  WARN_COUNT=$((WARN_COUNT + 1))
  RESULTS+=("WARN|$1")
}

check_install() {
  echo "=== Installation Check ==="

  if [ -f "$SKILL_PATH/SKILL.md" ]; then
    check_pass "SKILL.md exists [required]"
  else
    check_fail "SKILL.md exists [required]"
  fi

  if [ -d "$SKILL_PATH/references" ]; then
    check_pass "references/ directory exists [recommended]"
  else
    check_warn "references/ directory missing [recommended]"
  fi

  if [ -d "$SKILL_PATH/scripts" ]; then
    check_pass "scripts/ directory exists [recommended]"
  else
    check_warn "scripts/ directory missing [recommended]"
  fi

  if [ -d "$SKILL_PATH/templates" ]; then
    check_pass "templates/ directory exists [recommended]"
  else
    check_warn "templates/ directory missing [recommended]"
  fi

  if [ -d "$SKILL_PATH/demo" ]; then
    check_pass "demo/ directory exists [recommended]"
  else
    check_warn "demo/ directory missing [recommended]"
  fi

  if [ -d "$SKILL_PATH/scripts" ]; then
    for script in "$SKILL_PATH/scripts"/*; do
      if [ -f "$script" ]; then
        basename=$(basename "$script")
        if [ -x "$script" ]; then
          check_pass "Script $basename is executable [recommended]"
        else
          check_warn "Script $basename is not executable [recommended]"
        fi
      fi
    done
  fi
}

check_frontmatter() {
  echo "=== Frontmatter Check ==="

  SKILL_MD="$SKILL_PATH/SKILL.md"

  if [ ! -f "$SKILL_MD" ]; then
    check_fail "SKILL.md exists (required for frontmatter check)"
    return
  fi

  if grep -q '^name:' "$SKILL_MD"; then
    check_pass "Frontmatter 'name' field exists"
  else
    check_fail "Frontmatter 'name' field exists"
  fi

  if grep -q '^description:' "$SKILL_MD"; then
    check_pass "Frontmatter 'description' field exists"
  else
    check_fail "Frontmatter 'description' field exists"
  fi

  if grep -q '^version:' "$SKILL_MD"; then
    check_pass "Frontmatter 'version' field exists"
  else
    check_fail "Frontmatter 'version' field exists"
  fi

  if grep -q '^tags:' "$SKILL_MD"; then
    check_pass "Frontmatter 'tags' field exists"
  else
    check_fail "Frontmatter 'tags' field exists"
  fi

  if grep -qE '^version: [0-9]+\.[0-9]+\.[0-9]+' "$SKILL_MD"; then
    check_pass "Version follows SemVer"
  else
    check_fail "Version follows SemVer"
  fi
}

check_dependency() {
  echo "=== Dependency Check ==="

  if command -v hcloud &>/dev/null; then
    check_pass "hcloud CLI is installed"
  else
    check_fail "hcloud CLI is installed"
  fi

  if command -v hcloud &>/dev/null && hcloud configure list &>/dev/null 2>&1; then
    check_pass "hcloud CLI is authenticated"
  else
    check_fail "hcloud CLI is authenticated"
  fi

  if command -v node &>/dev/null; then
    check_pass "Node.js is installed"
  else
    check_fail "Node.js is installed"
  fi

  if command -v npx &>/dev/null; then
    check_pass "npx is available"
  else
    check_fail "npx is available"
  fi
}

check_language() {
  echo "=== Language Check (English-primary) ==="

  SKILL_MD="$SKILL_PATH/SKILL.md"

  if [ ! -f "$SKILL_MD" ]; then
    check_fail "SKILL.md exists (required for language check)"
    return
  fi

  local body_start
  body_start=$(grep -n '^---' "$SKILL_MD" | tail -1 | cut -d: -f1)
  if [ -z "$body_start" ]; then
    check_fail "SKILL.md frontmatter closing '---' found"
    return
  fi

  local body_lines=0
  local cjk_lines=0
  body_lines=$(tail -n +"$((body_start + 1))" "$SKILL_MD" | grep -c '.' || true)
  cjk_lines=$(tail -n +"$((body_start + 1))" "$SKILL_MD" | grep -cP '[\x{4e00}-\x{9fff}\x{3400}-\x{4dbf}]' || true)

  if [ "$body_lines" -eq 0 ]; then
    check_fail "SKILL.md body is empty"
    return
  fi

  local cjk_ratio
  cjk_ratio=$(echo "scale=2; $cjk_lines / $body_lines" | bc 2>/dev/null || echo "0")

  if [ "$(echo "$cjk_ratio < 0.30" | bc 2>/dev/null || echo "1")" -eq 1 ]; then
    check_pass "SKILL.md body is English-primary (CJK ratio: $cjk_ratio)"
  else
    check_fail "SKILL.md body CJK ratio too high: $cjk_ratio (threshold: < 0.30)"
  fi

  if [ -d "$SKILL_PATH/references" ]; then
    local ref_cjk=0
    local ref_total=0
    for ref_file in "$SKILL_PATH/references"/*.md; do
      if [ -f "$ref_file" ]; then
        local f_total f_cjk
        f_total=$(grep -c '.' "$ref_file" || true)
        f_cjk=$(grep -cP '[\x{4e00}-\x{9fff}\x{3400}-\x{4dbf}]' "$ref_file" || true)
        ref_total=$((ref_total + f_total))
        ref_cjk=$((ref_cjk + f_cjk))
      fi
    done
    if [ "$ref_total" -gt 0 ]; then
      local ref_ratio
      ref_ratio=$(echo "scale=2; $ref_cjk / $ref_total" | bc 2>/dev/null || echo "0")
      if [ "$(echo "$ref_ratio < 0.30" | bc 2>/dev/null || echo "1")" -eq 1 ]; then
        check_pass "Reference docs are English-primary (CJK ratio: $ref_ratio)"
      else
        check_fail "Reference docs CJK ratio too high: $ref_ratio (threshold: < 0.30)"
      fi
    fi
  fi
}

check_sections() {
  echo "=== SKILL.md Section Check ==="

  SKILL_MD="$SKILL_PATH/SKILL.md"

  if [ ! -f "$SKILL_MD" ]; then
    check_fail "SKILL.md exists (required for section check)"
    return
  fi

  local has_cli_ops=false
  if grep -qE 'hcloud\s+[A-Z]|npx\s+skills' "$SKILL_MD"; then
    has_cli_ops=true
  fi

  local section_defs=(
    "概述|Overview:required"
    "前置条件|Prerequisites:required"
    "工作流|Workflow:required"
    "核心命令|Core Commands:required"
    "参数确认|Parameters:required"
    "参考文档|References:required"
    "KooCLI命令格式标准|KooCLI Command Format|Huawei Cloud CLI Command Format:cli_required"
  )

  for def in "${section_defs[@]}"; do
    local names_level="${def%%:*}"
    local level="${def##*:}"

    local IFS_old="$IFS"
    IFS='|'
    local names=($names_level)
    IFS="$IFS_old"

    if [ "$level" = "cli_required" ] && [ "$has_cli_ops" = false ]; then
      continue
    fi

    local found=false
    local matched_name=""
    for name in "${names[@]}"; do
      if grep -qP "^##\s+\Q${name}\E" "$SKILL_MD"; then
        found=true
        matched_name="$name"
        break
      fi
    done

    local display_names="${names[0]}"
    for ((i=1; i<${#names[@]}; i++)); do
      display_names="$display_names / ${names[$i]}"
    done

    if [ "$found" = true ]; then
      if [ "$level" = "required" ] || [ "$level" = "cli_required" ]; then
        check_pass "Has $display_names section (matched: '$matched_name') [required]"
      else
        check_pass "Has $display_names section (matched: '$matched_name') [recommended]"
      fi
    else
      if [ "$level" = "required" ]; then
        check_fail "Has $display_names section [required]"
      elif [ "$level" = "cli_required" ]; then
        check_fail "Has $display_names section (CLI operations detected) [required]"
      else
        check_warn "Has $display_names section [recommended]"
      fi
    fi
  done

  local ref_section_found=false
  for name in "参考文档" "References" "Reference Documents"; do
    if grep -qP "^##\s+\Q${name}\E" "$SKILL_MD"; then
      ref_section_found=true
      break
    fi
  done

  if [ "$ref_section_found" = true ] && [ -d "$SKILL_PATH/references" ]; then
    local expected_refs=(
      "verification-method.md:recommended"
      "iam-policies.md:recommended"
      "cli-installation-guide.md:recommended"
      "related-commands.md:recommended"
    )
    for ref_def in "${expected_refs[@]}"; do
      local ref_file="${ref_def%%:*}"
      local ref_level="${ref_def##*:}"
      if [ -f "$SKILL_PATH/references/$ref_file" ]; then
        check_pass "Reference doc references/$ref_file exists [$ref_level]"
      else
        if [ "$ref_level" = "required" ]; then
          check_fail "Reference doc references/$ref_file exists [required]"
        else
          check_warn "Reference doc references/$ref_file missing [$ref_level]"
        fi
      fi
    done
  fi

  local cross_ref_skills
  cross_ref_skills=$(grep -oP 'huawei-cloud-[a-z0-9]+(-[a-z0-9]+)+' "$SKILL_MD" 2>/dev/null || true)
  if [ -n "$cross_ref_skills" ]; then
    local skill_name=""
    if grep -q '^name:' "$SKILL_MD"; then
      skill_name=$(grep '^name:' "$SKILL_MD" | head -1 | awk '{print $2}')
    fi
    local filtered_refs=""
    if [ -n "$skill_name" ]; then
      filtered_refs=$(grep -oP 'huawei-cloud-[a-z0-9]+(-[a-z0-9]+)+' "$SKILL_MD" 2>/dev/null | grep -v "^${skill_name}$" || true)
    else
      filtered_refs="$cross_ref_skills"
    fi
    if [ -n "$filtered_refs" ]; then
      check_warn "SKILL.md references other Skills (Skills should be orchestrated by Agent, not directly invoked)"
    fi
  fi
}

check_i18n() {
  echo "=== i18n Check ==="

  if [ ! -d "$SKILL_PATH/i18n" ]; then
    check_warn "i18n/ directory missing [recommended]"
    return
  fi

  check_pass "i18n/ directory exists [recommended]"

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
      check_pass "Locale follows BCP 47 format (xx-XX) [recommended]"
      locale_valid=$((locale_valid + 1))
    else
      check_warn "Locale does not follow BCP 47 format (expected xx-XX like zh-CN, en-US) [recommended]"
    fi

    local skill_files=()
    for f in "$locale_dir"SKILL*.md; do
      if [ -f "$f" ]; then
        skill_files+=("$f")
      fi
    done

    if [ ${#skill_files[@]} -gt 0 ]; then
      check_pass "Locale contains ${#skill_files[@]} SKILL translation file(s) [recommended]"

      for skill_file in "${skill_files[@]}"; do
        local skill_basename
        skill_basename=$(basename "$skill_file")

        local fm_fields_ok=true
        for field in name description version tags; do
          if grep -q "^${field}:" "$skill_file"; then
            :
          else
            check_warn "i18n file: frontmatter field '$field' missing [recommended]"
            fm_fields_ok=false
          fi
        done

        if [ "$fm_fields_ok" = true ]; then
          check_pass "i18n file: frontmatter fields complete [recommended]"
        fi

        if [ -f "$SKILL_PATH/SKILL.md" ]; then
          local orig_name i18n_name
          orig_name=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
          i18n_name=$(grep '^name:' "$skill_file" | head -1 | awk '{print $2}')
          if [ -n "$orig_name" ] && [ -n "$i18n_name" ]; then
            if [ "$orig_name" = "$i18n_name" ]; then
              check_pass "i18n file: name field matches original SKILL.md [recommended]"
            else
              check_warn "i18n file: name differs from original [recommended]"
            fi
          fi
        fi
      done
    else
      check_warn "Locale has no SKILL translation files (expected SKILL_XX.md) [recommended]"
    fi
  done

  if [ "$locale_count" -gt 0 ]; then
    check_info "i18n: $locale_valid/$locale_count locales valid"
  else
    check_warn "i18n/ directory exists but contains no locale subdirectories [recommended]"
  fi
}

check_security() {
  echo "=== Security Check (sec.secret.leak) ==="

  if [ ! -d "$SKILL_PATH/scripts" ]; then
    check_warn "scripts/ directory missing, skipping security check [recommended]"
    return
  fi

  local total_issues=0

  for script_file in "$SKILL_PATH/scripts"/*.sh; do
    if [ ! -f "$script_file" ]; then
      continue
    fi

    local script_basename
    script_basename=$(basename "$script_file")

    local echo_pipe_count=0
    echo_pipe_count=$(grep -cE 'echo\s+"?\$\{?[A-Za-z_][A-Za-z0-9_]*\}?' "$script_file" 2>/dev/null || true)
    if [ "$echo_pipe_count" -gt 0 ]; then
      local pipe_to_cmd=0
      pipe_to_cmd=$(grep -cE 'echo\s+"?\$\{?[A-Za-z_][A-Za-z0-9_]*\}?.*\|\s*(grep|sed|awk|cut)' "$script_file" 2>/dev/null || true)
      if [ "$pipe_to_cmd" -gt 0 ]; then
        check_fail "$script_basename: echo \$var | grep pattern detected ($pipe_to_cmd occurrences) - use 'grep ... file' instead [required]"
        total_issues=$((total_issues + pipe_to_cmd))
      fi
    fi

    local herestr_count=0
    herestr_count=$(grep -cE '<<<\s*"\$' "$script_file" 2>/dev/null || true)
    if [ "$herestr_count" -gt 0 ]; then
      check_fail "$script_basename: grep <<< \$var pattern detected ($herestr_count occurrences) - use 'grep ... file' instead [required]"
      total_issues=$((total_issues + herestr_count))
    fi

    local printf_param_count=0
    printf_param_count=$(grep -cE 'printf\s+.*\$\{?1\}?' "$script_file" 2>/dev/null || true)
    if [ "$printf_param_count" -gt 0 ]; then
      local in_sanitize=0
      in_sanitize=$(grep -cE '^\s*printf\s+.*\$1.*\|.*sed' "$script_file" 2>/dev/null || true)
      if [ "$in_sanitize" -gt 0 ]; then
        check_fail "$script_basename: sanitize-like function with printf \$1 detected - avoid outputting function params [required]"
        total_issues=$((total_issues + in_sanitize))
      fi
    fi

    local hardcoded_secret=0
    hardcoded_secret=$(grep -cE '(AK|SK|access_key|secret_key|api_key|apikey|token|password|passwd|credential)\s*[=:]\s*[^$\s]' "$script_file" 2>/dev/null || true)
    if [ "$hardcoded_secret" -gt 0 ]; then
      check_fail "$script_basename: hardcoded secret pattern detected ($hardcoded_secret occurrences) - use env vars instead [required]"
      total_issues=$((total_issues + hardcoded_secret))
    fi

    local long_literal=0
    long_literal=$(grep -cE '[A-Za-z0-9+/=]{40,}' "$script_file" 2>/dev/null || true)
    if [ "$long_literal" -gt 0 ]; then
      local in_keyword=0
      in_keyword=$(grep -cE '(trigger_keywords|negative_keywords|known_services|section_defs|keywords)=.*\[.*\]' "$script_file" 2>/dev/null || true)
      local suspect_count=$((long_literal - in_keyword))
      if [ "$suspect_count" -gt 0 ]; then
        check_warn "$script_basename: long literal string detected ($suspect_count suspects) - verify not leaked secrets [recommended]"
      fi
    fi
  done

  if [ "$total_issues" -eq 0 ]; then
    check_pass "No sec.secret.leak patterns detected in scripts/ [required]"
  else
    check_fail "Security issues detected: $total_issues total sec.secret.leak violations [required]"
  fi
}

check_uninstall() {
  echo "=== Uninstall Check ==="

  if ! command -v npx &>/dev/null; then
    check_fail "npx is available (required for uninstall test)"
    return
  fi

  local skill_name_field=""
  if [ -f "$SKILL_PATH/SKILL.md" ] && grep -q '^name:' "$SKILL_PATH/SKILL.md"; then
    skill_name_field=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
  fi

  if [ -z "$skill_name_field" ]; then
    check_warn "Cannot determine skill name for uninstall test [recommended]"
    return
  fi

  local pre_uninstall_exists=false
  if [ -d "$SKILL_PATH" ]; then
    pre_uninstall_exists=true
  fi

  if [ "$pre_uninstall_exists" = false ]; then
    check_warn "Skill directory not present, skipping uninstall test [recommended]"
    return
  fi

  echo "  Testing uninstall via npx skills remove..."
  if npx skills remove "$skill_name_field" &>/dev/null 2>&1; then
    check_pass "npx skills remove executed successfully [required]"
  else
    check_fail "npx skills remove failed [required]"
    return
  fi

  if [ ! -d "$SKILL_PATH" ]; then
    check_pass "Skill directory removed after uninstall [required]"
  else
    check_fail "Skill directory still exists after uninstall [required]"
  fi

  echo "  Testing reinstall via npx skills add..."
  local skill_repo=""
  if [ -f "$SKILL_PATH/../package.json" ]; then
    skill_repo=$(dirname "$(dirname "$SKILL_PATH")")
  fi

  if [ -n "$skill_repo" ] && [ -d "$skill_repo" ]; then
    if npx skills add "$skill_repo" --skill "$skill_name_field" &>/dev/null 2>&1; then
      check_pass "Skill reinstalled successfully [required]"
    else
      check_fail "Skill reinstall failed [required]"
      return
    fi

    if [ -d "$SKILL_PATH" ] && [ -f "$SKILL_PATH/SKILL.md" ]; then
      check_pass "Reinstalled skill structure intact [required]"
    else
      check_fail "Reinstalled skill structure broken [required]"
    fi
  else
    check_warn "Cannot determine skill repo for reinstall test [recommended]"
  fi
}

case "$PHASE" in
  install)       check_install ;;
  frontmatter)   check_frontmatter ;;
  dependency)    check_dependency ;;
  language)      check_language ;;
  sections)      check_sections ;;
  i18n)          check_i18n ;;
  security)      check_security ;;
  uninstall)     check_uninstall ;;
  all-install)
    check_install
    check_frontmatter
    check_dependency
    check_language
    check_sections
    check_i18n
    check_security
    check_uninstall
    ;;
  *) echo "Unknown phase: $PHASE"; usage ;;
esac

echo ""
echo "=== Summary ==="
echo "PASS: $PASS_COUNT"
echo "FAIL: $FAIL_COUNT"
echo "WARN: $WARN_COUNT (recommended items missing)"
echo "Total: $((PASS_COUNT + FAIL_COUNT + WARN_COUNT))"
echo ""
echo "Required checks: $((PASS_COUNT + FAIL_COUNT)) (PASS: $PASS_COUNT, FAIL: $FAIL_COUNT)"
echo "Recommended checks: $WARN_COUNT (missing but non-blocking)"

if [ $FAIL_COUNT -gt 0 ]; then
  echo ""
  echo "Failed required checks:"
  for r in "${RESULTS[@]}"; do
    if [[ "$r" == FAIL* ]]; then
      echo "  - ${r#FAIL|}"
    fi
  done
  exit 1
else
  echo ""
  if [ $WARN_COUNT -gt 0 ]; then
    echo "[PASS] All required checks passed (with $WARN_COUNT recommended item warnings)"
  else
    echo "[PASS] All checks passed"
  fi
  exit 0
fi
