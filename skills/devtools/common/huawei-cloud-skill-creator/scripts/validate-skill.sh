#!/bin/bash
set -euo pipefail

SKILL_PATH="${1:?Usage: bash validate-skill.sh <skill-path> [--phase <phase>]}"
PHASE="all"

shift || true
while [ $# -gt 0 ]; do
  case "$1" in
    --phase) PHASE="$2"; shift 2 ;;
    *) echo "Usage: bash validate-skill.sh <skill-path> [--phase <phase>]"; exit 1 ;;
  esac
done

if [ ! -d "$SKILL_PATH" ]; then
  echo "[FAIL] Skill path does not exist"
  exit 1
fi

PASS=0
FAIL=0
WARN=0

check_pass() { PASS=$((PASS+1)); echo "  [PASS] $1"; }
check_fail() { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }
check_warn() { WARN=$((WARN+1)); echo "  [WARN] $1"; }

echo "=========================================="
echo " Skill Quality Validation"
echo " Target: $SKILL_PATH"
echo " Phase: $PHASE"
echo "=========================================="
echo ""

check_install() {
  echo "=== Installation & Structure ==="

  if [ -f "$SKILL_PATH/SKILL.md" ]; then
    check_pass "SKILL.md exists [required]"
  else
    check_fail "SKILL.md exists [required]"
    echo "  >> Cannot continue without SKILL.md"
    exit 1
  fi

  for dir in references scripts templates demo; do
    if [ -d "$SKILL_PATH/$dir" ]; then
      check_pass "$dir/ directory exists [recommended]"
    else
      check_warn "$dir/ directory missing [recommended]"
    fi
  done

  if [ -d "$SKILL_PATH/scripts" ]; then
    for script in "$SKILL_PATH/scripts"/*; do
      if [ -f "$script" ]; then
        local sname
        sname=$(basename "$script")
        if [ -x "$script" ]; then
          check_pass "Script $sname is executable [recommended]"
        else
          check_warn "Script $sname is not executable [recommended]"
        fi
      fi
    done
  fi
}

check_frontmatter() {
  echo "=== Frontmatter ==="

  SKILL_MD="$SKILL_PATH/SKILL.md"

  if head -1 "$SKILL_MD" | grep -q '^---'; then
    check_pass "YAML Frontmatter opening --- [required]"
  else
    check_fail "YAML Frontmatter opening --- [required]"
  fi

  if grep -q '^name:' "$SKILL_MD"; then
    NAME_VAL=$(grep '^name:' "$SKILL_MD" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"' | tr -d "'")
    if [[ -n "$NAME_VAL" ]]; then
      check_pass "name field: $NAME_VAL [required]"
      if [[ "$NAME_VAL" =~ ^huawei-cloud-[a-z0-9]+-[a-z0-9-]+$ ]]; then
        check_pass "name follows huawei-cloud-{product}-{function} convention [recommended]"
      else
        check_warn "name does not follow naming convention [recommended]"
      fi
    else
      check_fail "name field is empty [required]"
    fi
  else
    check_fail "name field exists [required]"
  fi

  if grep -q '^description:' "$SKILL_MD"; then
    check_pass "description field exists [required]"
  else
    check_fail "description field exists [required]"
  fi

  if grep -qiE 'Triggers include' "$SKILL_MD"; then
    check_pass "description contains trigger words (Triggers include) [required]"
  else
    check_fail "description missing trigger words — must include 'Triggers include:' [required]"
  fi

  local desc_block
  desc_block=$(sed -n '/^description:/,/^[^ ]/p' "$SKILL_MD")
  local desc_lines
  desc_lines=$(printf '%s\n' "$desc_block" | grep -cE '^\s+[0-9]+\.' || true)
  if [ "$desc_lines" -ge 5 ]; then
    check_pass "description has 5-point structured format ($desc_lines points) [recommended]"
  else
    check_warn "description should have 5-point structured format (found $desc_lines points) [recommended]"
  fi

  if grep -q '^tags:' "$SKILL_MD"; then
    check_pass "tags field exists [recommended]"
  else
    check_warn "tags field missing [recommended]"
  fi

  if grep -q '^version:' "$SKILL_MD"; then
    VER=$(grep '^version:' "$SKILL_MD" | head -1 | sed 's/^version:[[:space:]]*//')
    if [[ "$VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      check_pass "version follows SemVer: $VER [required]"
    else
      check_fail "version does not follow SemVer: $VER [required]"
    fi
  else
    check_fail "version field exists [required]"
  fi
}

check_dependency() {
  echo "=== Dependency Check ==="

  if command -v hcloud &>/dev/null; then
    check_pass "hcloud CLI is installed [recommended]"
  else
    check_warn "hcloud CLI is not installed [recommended]"
  fi

  if command -v hcloud &>/dev/null && hcloud configure list &>/dev/null 2>&1; then
    check_pass "hcloud CLI is authenticated [recommended]"
  else
    check_warn "hcloud CLI is not authenticated [recommended]"
  fi

  if command -v node &>/dev/null; then
    check_pass "Node.js is installed [recommended]"
  else
    check_warn "Node.js is not installed [recommended]"
  fi

  if command -v npx &>/dev/null; then
    check_pass "npx is available [recommended]"
  else
    check_warn "npx is not available [recommended]"
  fi
}

check_language() {
  echo "=== Language Check (English-primary) ==="

  SKILL_MD="$SKILL_PATH/SKILL.md"
  if [ ! -f "$SKILL_MD" ]; then
    check_fail "SKILL.md exists [required]"
    return
  fi

  local body_start
  body_start=$(grep -n '^---' "$SKILL_MD" | sed -n '2p' | cut -d: -f1)
  if [ -z "$body_start" ]; then
    check_warn "Cannot determine body start [recommended]"
    return
  fi

  local body_lines=0
  local cjk_lines=0
  body_lines=$(tail -n +"$((body_start + 1))" "$SKILL_MD" | grep -c '.' || true)
  cjk_lines=$(tail -n +"$((body_start + 1))" "$SKILL_MD" | grep -cP '[\x{4e00}-\x{9fff}\x{3400}-\x{4dbf}]' || true)

  if [ "$body_lines" -eq 0 ]; then
    check_fail "SKILL.md body is empty [required]"
    return
  fi

  local cjk_ratio
  cjk_ratio=$(echo "scale=2; $cjk_lines / $body_lines" | bc 2>/dev/null || echo "0")

  if [ "$(echo "$cjk_ratio < 0.30" | bc 2>/dev/null || echo "1")" -eq 1 ]; then
    check_pass "SKILL.md body is English-primary (CJK ratio: $cjk_ratio) [recommended]"
  else
    check_fail "SKILL.md body CJK ratio too high: $cjk_ratio (threshold: < 0.30) [required]"
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
        check_pass "Reference docs are English-primary (CJK ratio: $ref_ratio) [recommended]"
      else
        check_warn "Reference docs CJK ratio high: $ref_ratio [recommended]"
      fi
    fi
  fi
}

check_sections() {
  echo "=== Body Sections ==="

  SKILL_MD="$SKILL_PATH/SKILL.md"
  if [ ! -f "$SKILL_MD" ]; then
    check_fail "SKILL.md exists [required]"
    return
  fi

  local has_cli_ops=false
  if grep -qE 'hcloud\s+[A-Z]|npx\s+skills' "$SKILL_MD"; then
    has_cli_ops=true
  fi

  local section_defs=(
    "Overview:required"
    "Prerequisites:required"
    "Main Steps:required"
    "Security Operations:recommended"
    "Cost Confirmation:recommended"
    "Authentication:recommended"
    "References:recommended"
  )

  for def in "${section_defs[@]}"; do
    local section_name="${def%%:*}"
    local level="${def##*:}"

    if grep -qP "^##\s+.*${section_name}" "$SKILL_MD"; then
      if [ "$level" = "required" ]; then
        check_pass "Has $section_name section [required]"
      else
        check_pass "Has $section_name section [recommended]"
      fi
    else
      if [ "$level" = "required" ]; then
        check_fail "Has $section_name section [required]"
      else
        check_warn "Has $section_name section missing [recommended]"
      fi
    fi
  done

  if [ "$has_cli_ops" = true ]; then
    for cli_section in "Core Commands" "Parameters"; do
      if grep -qP "^##\s+.*${cli_section}" "$SKILL_MD"; then
        check_pass "Has $cli_section section (CLI detected) [required]"
      else
        check_fail "Has $cli_section section (CLI detected) [required]"
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
      filtered_refs=$(printf '%s\n' "$cross_ref_skills" | grep -v "^${skill_name}$" || true)
    else
      filtered_refs="$cross_ref_skills"
    fi
    if [ -n "$filtered_refs" ]; then
      check_warn "SKILL.md references other Skills (should be orchestrated by Agent, not directly invoked) [recommended]"
    fi
  fi
}

check_cli_spec() {
  echo "=== CLI Command Spec ==="

  SKILL_MD="$SKILL_PATH/SKILL.md"

  extract_bash_blocks() {
    awk '/^```bash/{p=1;next} /^```/{p=0;next} p{print}' "$1" 2>/dev/null
  }

  if grep -qiE '(AK[A-Z0-9]{16,}|SK[A-Z0-9]{16,}|access.key[[:space:]]*=[[:space:]]*[A-Z0-9]{20,}|secret.key[[:space:]]*=[[:space:]]*[A-Z0-9]{20,})' "$SKILL_MD" 2>/dev/null; then
    check_fail "Possible hardcoded AK/SK in SKILL.md [required]"
  else
    check_pass "No hardcoded AK/SK in SKILL.md [required]"
  fi

  local HCS_FAIL=0
  for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
    [[ -f "$f" ]] || continue
    if grep -qE 'hcloud[[:space:]]+configure[[:space:]]+set.*--access-key' "$f" 2>/dev/null; then
      check_fail "CLI config with --access-key in $(basename "$f") [required]"
      HCS_FAIL=$((HCS_FAIL+1))
    fi
  done
  if [[ $HCS_FAIL -eq 0 ]]; then
    check_pass "No CLI config with plaintext credentials [required]"
  fi

  local CLI_REGION_FAIL=0
  for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
    [[ -f "$f" ]] || continue
    local FNAME
    FNAME=$(basename "$f")
    local MATCH
    MATCH=$(extract_bash_blocks "$f" | grep -E '^\s*hcloud [A-Z]' | grep -vE '(--help|configure)' | grep -vE '\-\-cli-region' || true)
    if [[ -n "$MATCH" ]]; then
      while IFS= read -r line; do
        check_fail "hcloud command missing --cli-region in $FNAME: $line [required]"
        CLI_REGION_FAIL=$((CLI_REGION_FAIL+1))
      done < <(printf '%s\n' "$MATCH")
    fi
  done
  if [[ $CLI_REGION_FAIL -eq 0 ]]; then
    check_pass "All hcloud commands in code blocks include --cli-region [required]"
  fi

  local SVC_FAIL=0
  for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
    [[ -f "$f" ]] || continue
    local FNAME
    FNAME=$(basename "$f")
    local SVC_LIST
    SVC_LIST=$(extract_bash_blocks "$f" | grep -oE 'hcloud [A-Za-z]+' | awk '{print $2}' | grep -vE '^[A-Z][A-Z0-9]*$' | grep -vE '^configure$' || true)
    if [[ -n "$SVC_LIST" ]]; then
      while IFS= read -r SVC; do
        check_fail "Service name not uppercase in $FNAME: '$SVC' [required]"
        SVC_FAIL=$((SVC_FAIL+1))
      done < <(printf '%s\n' "$SVC_LIST")
    fi
  done
  if [[ $SVC_FAIL -eq 0 ]]; then
    check_pass "All service names in code blocks are uppercase [required]"
  fi

  local OP_FAIL=0
  for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
    [[ -f "$f" ]] || continue
    local FNAME
    FNAME=$(basename "$f")
    local OP_LIST
    OP_LIST=$(extract_bash_blocks "$f" | grep -oE 'hcloud [A-Z]+ [A-Za-z]+' | awk '{print $3}' | grep -vE '^[A-Z][A-Za-z0-9]*$' || true)
    if [[ -n "$OP_LIST" ]]; then
      while IFS= read -r OP; do
        check_fail "Operation name not PascalCase in $FNAME: '$OP' [required]"
        OP_FAIL=$((OP_FAIL+1))
      done < <(printf '%s\n' "$OP_LIST")
    fi
  done
  if [[ $OP_FAIL -eq 0 ]]; then
    check_pass "All operation names in code blocks are PascalCase [required]"
  fi
}

check_references() {
  echo "=== Reference Docs ==="

  REF_DIR="$SKILL_PATH/references"
  if [[ -d "$REF_DIR" ]]; then
    check_pass "references/ directory exists [recommended]"
  else
    check_warn "references/ directory missing [recommended]"
    return
  fi

  if [[ -f "$REF_DIR/iam-policies.md" ]]; then
    check_pass "references/iam-policies.md exists [required]"
    if grep -qiE 'MFA' "$REF_DIR/iam-policies.md"; then
      check_pass "iam-policies.md includes MFA requirements [recommended]"
    else
      check_warn "iam-policies.md missing MFA requirements [recommended]"
    fi
  else
    check_fail "references/iam-policies.md exists [required]"
  fi

  local SKILL_MD="$SKILL_PATH/SKILL.md"
  if [[ -f "$SKILL_MD" ]]; then
    local REF_LINKS
    REF_LINKS=$(grep -oE 'references/[a-zA-Z0-9_-]+\.md' "$SKILL_MD" 2>/dev/null | sort -u || true)
    for ref in $REF_LINKS; do
      if [[ -f "$SKILL_PATH/$ref" ]]; then
        check_pass "Referenced file exists: $ref [required]"
      else
        check_fail "Referenced file missing: $ref [required]"
      fi
    done
  fi

  for ref_file in "cli-installation-guide.md" "verification-method.md" "acceptance-criteria.md" "related-commands.md"; do
    if [[ -f "$REF_DIR/$ref_file" ]]; then
      check_pass "references/$ref_file exists [recommended]"
    else
      check_warn "references/$ref_file missing [recommended]"
    fi
  done
}

check_dataflow() {
  echo "=== Data Flow Diagram ==="

  local DATAFLOW_FILE="$SKILL_PATH/references/dataflow-diagram.md"
  if [[ -f "$DATAFLOW_FILE" ]]; then
    check_pass "references/dataflow-diagram.md exists [required]"
    if grep -qE '```mermaid' "$DATAFLOW_FILE"; then
      check_pass "dataflow-diagram.md contains Mermaid code block [required]"
    else
      check_fail "dataflow-diagram.md missing Mermaid code block [required]"
    fi
    if grep -qE 'flowchart' "$DATAFLOW_FILE"; then
      check_pass "dataflow-diagram.md contains flowchart directive [required]"
    else
      check_fail "dataflow-diagram.md missing flowchart directive [required]"
    fi
    if grep -qF -- '-->' "$DATAFLOW_FILE"; then
      check_pass "dataflow-diagram.md contains primary data flow arrows (-->) [required]"
    else
      check_fail "dataflow-diagram.md missing primary data flow arrows [required]"
    fi
    if grep -qiE '(Legend|Data Flow Description)' "$DATAFLOW_FILE"; then
      check_pass "dataflow-diagram.md contains legend or description table [recommended]"
    else
      check_warn "dataflow-diagram.md missing legend or description table [recommended]"
    fi
  else
    check_fail "references/dataflow-diagram.md exists [required]"
  fi
}

check_security() {
  echo "=== Security Scan (sec.secret.leak) ==="

  local total_issues=0

  if [ -d "$SKILL_PATH/scripts" ]; then
    for script_file in "$SKILL_PATH/scripts"/*.sh; do
      [ -f "$script_file" ] || continue
      local script_basename
      script_basename=$(basename "$script_file")

      local echo_pipe_count=0
      echo_pipe_count=$(grep -cE 'echo\s+"?\$\{?[A-Za-z_][A-Za-z0-9_]*\}?' "$script_file" 2>/dev/null || true)
      if [ "$echo_pipe_count" -gt 0 ]; then
        local pipe_to_cmd=0
        pipe_to_cmd=$(grep -cE 'echo\s+"?\$\{?[A-Za-z_][A-Za-z0-9_]*\}?.*\|\s*(grep|sed|awk|cut)' "$script_file" 2>/dev/null || true)
        if [ "$pipe_to_cmd" -gt 0 ]; then
          check_fail "$script_basename: echo \$var | cmd pattern ($pipe_to_cmd occurrences) [required]"
          total_issues=$((total_issues + pipe_to_cmd))
        fi
      fi

      local herestr_count=0
      herestr_count=$(grep -cE '<<<\s*"\$' "$script_file" 2>/dev/null || true)
      if [ "$herestr_count" -gt 0 ]; then
        check_fail "$script_basename: grep <<< \$var pattern ($herestr_count occurrences) [required]"
        total_issues=$((total_issues + herestr_count))
      fi

      local printf_sed_count=0
      printf_sed_count=$(grep -cE '^\s*printf\s+.*\$1.*\|.*sed' "$script_file" 2>/dev/null || true)
      if [ "$printf_sed_count" -gt 0 ]; then
        check_fail "$script_basename: sanitize-like printf \$1 | sed pattern ($printf_sed_count occurrences) [required]"
        total_issues=$((total_issues + printf_sed_count))
      fi

      local hardcoded_secret=0
      hardcoded_secret=$(grep -cE '(AK|SK|access_key|secret_key|api_key|apikey|token|password|passwd|credential)\s*[=:]\s*[^$\s]' "$script_file" 2>/dev/null || true)
      if [ "$hardcoded_secret" -gt 0 ]; then
        check_fail "$script_basename: hardcoded secret pattern ($hardcoded_secret occurrences) [required]"
        total_issues=$((total_issues + hardcoded_secret))
      fi

      local long_literal=0
      long_literal=$(grep -cE '[A-Za-z0-9+/=]{40,}' "$script_file" 2>/dev/null || true)
      if [ "$long_literal" -gt 0 ]; then
        local in_keyword=0
        in_keyword=$(grep -cE '(trigger_keywords|negative_keywords|known_services|section_defs|keywords)=.*\[.*\]' "$script_file" 2>/dev/null || true)
        local suspect_count=$((long_literal - in_keyword))
        if [ "$suspect_count" -gt 0 ]; then
          check_warn "$script_basename: long literal string ($suspect_count suspects) [recommended]"
        fi
      fi
    done
  fi

  local SEC_FAIL=0
  local SKILL_MD="$SKILL_PATH/SKILL.md"
  for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
    [[ -f "$f" ]] || continue
    local FNAME
    FNAME=$(basename "$f")
    local LINE_NUM=0
    while IFS= read -r line; do
      LINE_NUM=$((LINE_NUM+1))
      if [[ "$line" =~ (secret\.key[[:space:]]*=[[:space:]]*[^\$<\{]|SECRET_KEY[[:space:]]*=[[:space:]]*[][A-Za-z0-9]{10,}) ]]; then
        if [[ ! "$line" =~ (\{your_|placeholder|xxx|\$\{|\<AK\>|\<SK\>|AK\>|SK\>|=AK|=SK|--access-key=AK|--secret-key=SK) ]]; then
          check_fail "Hardcoded secret key in $FNAME L$LINE_NUM [required]"
          SEC_FAIL=$((SEC_FAIL+1))
        fi
      fi
    done < "$f"
  done
  if [[ $SEC_FAIL -eq 0 ]]; then
    check_pass "No hardcoded secret keys in docs/templates [required]"
  fi

  if [ "$total_issues" -eq 0 ] && [ "$SEC_FAIL" -eq 0 ]; then
    check_pass "No sec.secret.leak patterns detected [required]"
  fi
}

check_i18n() {
  echo "=== i18n (Internationalization) ==="

  local I18N_DIR="$SKILL_PATH/i18n"
  if [[ -d "$I18N_DIR" ]]; then
    check_pass "i18n/ directory exists [recommended]"
  else
    check_warn "i18n/ directory missing [recommended]"
    return
  fi

  local locale_count=0
  local locale_valid=0

  for locale_dir in "$I18N_DIR"/*/; do
    [ -d "$locale_dir" ] || continue
    locale_count=$((locale_count + 1))
    local locale_name
    locale_name=$(basename "$locale_dir")

    if [[ "$locale_name" =~ ^[a-z]{2,3}-[A-Z]{2}$ ]]; then
      check_pass "Locale $locale_name follows BCP 47 format (xx-XX) [recommended]"
      locale_valid=$((locale_valid + 1))
    else
      check_warn "Locale $locale_name does not follow BCP 47 format [recommended]"
    fi

    local skill_files=()
    for f in "$locale_dir"SKILL*.md; do
      [ -f "$f" ] && skill_files+=("$f")
    done

    if [ ${#skill_files[@]} -gt 0 ]; then
      for skill_file in "${skill_files[@]}"; do
        local skill_basename
        skill_basename=$(basename "$skill_file")

        if head -1 "$skill_file" | grep -q '^---'; then
          check_pass "$skill_basename YAML Frontmatter opening --- [required]"
        else
          check_fail "$skill_basename YAML Frontmatter opening --- [required]"
        fi

        local fm_fields_ok=true
        for field in name description version tags; do
          if grep -q "^${field}:" "$skill_file"; then
            :
          else
            check_warn "$skill_basename frontmatter field '$field' missing [recommended]"
            fm_fields_ok=false
          fi
        done
        if [ "$fm_fields_ok" = true ]; then
          check_pass "$skill_basename frontmatter fields complete [recommended]"
        fi

        if [ -f "$SKILL_PATH/SKILL.md" ]; then
          local orig_name i18n_name
          orig_name=$(grep '^name:' "$SKILL_PATH/SKILL.md" | head -1 | awk '{print $2}')
          i18n_name=$(grep '^name:' "$skill_file" | head -1 | awk '{print $2}')
          if [ -n "$orig_name" ] && [ -n "$i18n_name" ]; then
            if [ "$orig_name" = "$i18n_name" ]; then
              check_pass "$skill_basename name matches original SKILL.md [recommended]"
            else
              check_warn "$skill_basename name differs from original [recommended]"
            fi
          fi
        fi

        if grep -qiE '触发场景包括' "$skill_file"; then
          check_pass "$skill_basename contains Chinese trigger words (触发场景包括) [recommended]"
        else
          check_warn "$skill_basename missing Chinese trigger words [recommended]"
        fi

        if grep -qE 'hcloud [A-Z]+ [A-Za-z]+' "$skill_file"; then
          check_pass "$skill_basename CLI commands remain in English [recommended]"
        else
          check_warn "$skill_basename no CLI commands found (verify not translated) [recommended]"
        fi
      done
    else
      check_warn "Locale $locale_name has no SKILL translation files [recommended]"
    fi
  done

  if [ "$locale_count" -gt 0 ]; then
    check_pass "i18n: $locale_valid/$locale_count locales valid [recommended]"
  fi
}

check_content_quality() {
  echo "=== Content Quality ==="

  local SKILL_MD="$SKILL_PATH/SKILL_MD"
  SKILL_MD="$SKILL_PATH/SKILL.md"

  local BODY_START
  BODY_START=$(grep -n '^---' "$SKILL_MD" | sed -n '2p' | cut -d: -f1)
  if [[ -n "$BODY_START" ]]; then
    local TOTAL_LINES
    TOTAL_LINES=$(wc -l < "$SKILL_MD")
    local BODY_LINES=$((TOTAL_LINES - BODY_START))
    if [[ $BODY_LINES -le 500 ]]; then
      check_pass "Body lines: $BODY_LINES (<= 500) [recommended]"
    else
      check_warn "Body lines: $BODY_LINES (> 500, recommended <= 500) [recommended]"
    fi
  else
    check_warn "Cannot determine body line count [recommended]"
  fi

  local CODE_BLOCKS ALL_FENCES
  CODE_BLOCKS=$(grep -cE '^\s*```[a-zA-Z]' "$SKILL_MD" 2>/dev/null || echo 0)
  ALL_FENCES=$(grep -cE '^\s*```' "$SKILL_MD" 2>/dev/null || echo 0)
  local OPENING_TOTAL=$((ALL_FENCES / 2))
  if [[ $OPENING_TOTAL -gt 0 ]] && [[ $CODE_BLOCKS -eq $OPENING_TOTAL ]]; then
    check_pass "All code blocks have language annotation [recommended]"
  elif [[ $OPENING_TOTAL -gt 0 ]] && [[ $CODE_BLOCKS -lt $OPENING_TOTAL ]]; then
    local UNANNOTATED=$((OPENING_TOTAL - CODE_BLOCKS))
    check_warn "$UNANNOTATED code block(s) missing language annotation [recommended]"
  fi
}

check_scripts() {
  echo "=== Scripts Check ==="

  if [[ -d "$SKILL_PATH/scripts" ]]; then
    for script in "$SKILL_PATH/scripts"/*; do
      if [[ -f "$script" ]]; then
        local SNAME
        SNAME=$(basename "$script")
        if grep -qiE '(AK[A-Z0-9]{16,}|SK[A-Z0-9]{16,})' "$script" 2>/dev/null; then
          check_fail "Possible hardcoded AK/SK in $SNAME [required]"
        else
          check_pass "No hardcoded AK/SK in $SNAME [required]"
        fi
        if head -1 "$script" | grep -qE '^#!/'; then
          check_pass "Shebang in $SNAME [recommended]"
        else
          check_warn "Missing shebang in $SNAME [recommended]"
        fi
        if [[ "$SNAME" == *.py ]]; then
          if [[ -f "$(dirname "$script")/__init__.py" ]]; then
            check_pass "__init__.py exists for Python script [recommended]"
          else
            check_warn "Missing __init__.py for Python script $SNAME [recommended]"
          fi
        fi
        if [[ "$SNAME" =~ \.m?js$ ]] && [[ "$SNAME" != *.mjs ]]; then
          check_warn "Node.js script $SNAME should use .mjs extension [recommended]"
        fi
      fi
    done
  else
    check_warn "No scripts/ directory [recommended]"
  fi
}

check_uninstall() {
  echo "=== Uninstall Check ==="

  if ! command -v npx &>/dev/null; then
    check_warn "npx not available, skipping uninstall test [recommended]"
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

  if npx skills remove "$skill_name_field" &>/dev/null 2>&1; then
    check_pass "npx skills remove executed successfully [recommended]"
  else
    check_warn "npx skills remove failed [recommended]"
    return
  fi

  if [ ! -d "$SKILL_PATH" ]; then
    check_pass "Skill directory removed after uninstall [recommended]"
  else
    check_warn "Skill directory still exists after uninstall (may be source path) [recommended]"
  fi
}

check_functional_test() {
  echo "=== Functional CLI Test ==="

  local TEST_SCRIPT="$SKILL_PATH/../scripts/test-cli-commands.sh"
  if [ ! -f "$TEST_SCRIPT" ]; then
    # Fallback: check in skill-creator's own scripts
    TEST_SCRIPT="$(dirname "$0")/test-cli-commands.sh"
  fi

  if [ ! -f "$TEST_SCRIPT" ]; then
    check_warn "test-cli-commands.sh not found — cannot run CLI functional tests [recommended]"
    return
  fi

  if [ ! -x "$TEST_SCRIPT" ]; then
    check_warn "test-cli-commands.sh is not executable [recommended]"
    return
  fi

  local TEST_REPORT="$SKILL_PATH/references/test-report.md"

  # Run the test script
  if bash "$TEST_SCRIPT" "$SKILL_PATH" --output "$TEST_REPORT"; then
    check_pass "CLI functional tests passed — report at references/test-report.md [required]"
  else
    check_fail "CLI functional tests reported failures — check references/test-report.md [required]"
  fi

  if [ -f "$TEST_REPORT" ]; then
    check_pass "references/test-report.md generated [required]"
  else
    check_fail "references/test-report.md was not generated [required]"
  fi
}

case "$PHASE" in
  install)          check_install ;;
  frontmatter)      check_frontmatter ;;
  dependency)       check_dependency ;;
  language)         check_language ;;
  sections)         check_sections ;;
  cli-spec)         check_cli_spec ;;
  references)       check_references ;;
  dataflow)         check_dataflow ;;
  security)         check_security ;;
  i18n)             check_i18n ;;
  content-quality)  check_content_quality ;;
  scripts)          check_scripts ;;
  uninstall)        check_uninstall ;;
  functional-test)  check_functional_test ;;
  all)
    check_install
    check_frontmatter
    check_dependency
    check_language
    check_sections
    check_cli_spec
    check_references
    check_dataflow
    check_security
    check_i18n
    check_content_quality
    check_scripts
    check_uninstall
    check_functional_test
    ;;
  *) echo "Unknown phase: $PHASE"; echo "Phases: install, frontmatter, dependency, language, sections, cli-spec, references, dataflow, security, i18n, content-quality, scripts, uninstall, functional-test, all"; exit 1 ;;
esac

echo ""
echo "=========================================="
echo " Results"
echo "=========================================="
echo "  PASS: $PASS"
echo "  WARN: $WARN"
echo "  FAIL: $FAIL"
echo ""

TOTAL=$((PASS + WARN + FAIL))
if [[ $TOTAL -gt 0 ]]; then
  RECOMMENDED_TOTAL=$((PASS + WARN))
  if [[ $RECOMMENDED_TOTAL -gt 0 ]]; then
    RECOMMENDED_PCT=$((PASS * 100 / RECOMMENDED_TOTAL))
  else
    RECOMMENDED_PCT=0
  fi
  echo "  Recommended pass rate: ${RECOMMENDED_PCT}%"
fi
echo ""

if [[ $FAIL -eq 0 ]]; then
  if [[ $WARN -le 3 ]]; then
    echo "  Grade: A (All required passed, warnings <= 3)"
  elif [[ $WARN -le 6 ]]; then
    echo "  Grade: B (All required passed, warnings <= 6)"
  else
    echo "  Grade: C (All required passed, many warnings)"
  fi
  echo "  Status: PASS"
  exit 0
else
  echo "  Grade: D (Required checks failed)"
  echo "  Status: FAIL"
  exit 1
fi
