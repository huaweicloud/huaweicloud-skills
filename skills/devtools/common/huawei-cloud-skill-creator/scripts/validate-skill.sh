#!/bin/bash
# validate-skill.sh — Validate Huawei Cloud Skill compliance
# Usage: bash validate-skill.sh <skill-path>

set -euo pipefail

SKILL_PATH="${1:?Usage: bash validate-skill.sh <skill-path>}"
PASS=0
FAIL=0
WARN=0

check_pass() { PASS=$((PASS+1)); echo "  [PASS] $1"; }
check_fail() { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }
check_warn() { WARN=$((WARN+1)); echo "  [WARN] $1"; }

echo "=========================================="
echo " Skill Quality Validation"
echo " Target: $SKILL_PATH"
echo "=========================================="
echo ""

# --- Required Items ---
echo "=== Required Items ==="

# 1. SKILL.md exists
SKILL_MD="$SKILL_PATH/SKILL.md"
if [[ -f "$SKILL_MD" ]]; then
  check_pass "SKILL.md exists"
else
  check_fail "SKILL.md exists"
  echo "  >> Cannot continue without SKILL.md"
  exit 1
fi

# 2. YAML Frontmatter
if head -1 "$SKILL_MD" | grep -q '^---'; then
  check_pass "YAML Frontmatter opening ---"
else
  check_fail "YAML Frontmatter opening ---"
fi

# 3. name field
if grep -q '^name:' "$SKILL_MD"; then
  NAME_VAL=$(grep '^name:' "$SKILL_MD" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '"' | tr -d "'")
  if [[ -n "$NAME_VAL" ]]; then
    check_pass "name field: $NAME_VAL"
    if echo "$NAME_VAL" | grep -qE '^huawei-cloud-[a-z0-9]+-[a-z0-9-]+$'; then
      check_pass "name follows naming convention"
    else
      check_warn "name does not follow huawei-cloud-{product}-{function} convention"
    fi
  else
    check_fail "name field is empty"
  fi
else
  check_fail "name field exists"
fi

# 4. description field
if grep -q '^description:' "$SKILL_MD"; then
  check_pass "description field exists"
else
  check_fail "description field exists"
fi

# 5. description contains trigger words (Triggers include)
if grep -qiE 'Triggers include' "$SKILL_MD"; then
  check_pass "description contains trigger words (Triggers include)"
else
  check_fail "description missing trigger words — must include 'Triggers include:'"
fi

# 6. tags field
if grep -q '^tags:' "$SKILL_MD"; then
  check_pass "tags field exists"
else
  check_warn "tags field missing (recommended)"
fi

# 7. version field must exist and follow SemVer
if grep -q '^version:' "$SKILL_MD"; then
  VER=$(grep '^version:' "$SKILL_MD" | head -1 | sed 's/^version:[[:space:]]*//')
  if echo "$VER" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    check_pass "version follows SemVer: $VER"
  else
    check_fail "version does not follow SemVer: $VER"
  fi
else
  check_fail "version field missing (required)"
fi

# 8. AK/SK security check
if grep -qiE '(AK[A-Z0-9]{16,}|SK[A-Z0-9]{16,}|access.key[[:space:]]*=[[:space:]]*[A-Z0-9]{20,}|secret.key[[:space:]]*=[[:space:]]*[A-Z0-9]{20,})' "$SKILL_MD" 2>/dev/null; then
  check_fail "Possible hardcoded AK/SK in SKILL.md"
else
  check_pass "No hardcoded AK/SK in SKILL.md"
fi

# --- Body Structure Check ---
echo ""
echo "=== Body Structure ==="

# 9. Prerequisites chapter
if grep -qE '^## .*Prerequisites' "$SKILL_MD"; then
  check_pass "Prerequisites chapter exists"
else
  check_fail "Prerequisites chapter missing (required)"
fi

# 10. Core Commands chapter
if grep -qE '^## .*Core Commands' "$SKILL_MD"; then
  check_pass "Core Commands chapter exists"
else
  check_fail "Core Commands chapter missing (required)"
fi

# 11. Parameters chapter
if grep -qE '^## .*Parameters' "$SKILL_MD"; then
  check_pass "Parameters chapter exists"
else
  check_fail "Parameters chapter missing (required)"
fi

# 12. Overview chapter
if grep -qE '^## .*Overview' "$SKILL_MD"; then
  check_pass "Overview chapter exists"
else
  check_fail "Overview chapter exists (required)"
fi

# 13. Security Operations chapter
if grep -qE '^## .*Security Operations' "$SKILL_MD"; then
  check_pass "Security Operations chapter exists"
  if grep -qE 'Must avoid' "$SKILL_MD"; then
    check_pass "Security spec includes Must avoid section"
  else
    check_warn "Security spec missing Must avoid section"
  fi
else
  check_warn "Security Operations chapter missing (recommended)"
fi

# 14. User-Agent identification
if grep -qiE 'user.agent|User-Agent' "$SKILL_MD"; then
  check_pass "User-Agent identification mentioned"
else
  check_warn "User-Agent identification not mentioned"
fi

# 15. Authentication method
if grep -qE '^## .*Authentication' "$SKILL_MD"; then
  check_pass "Authentication chapter exists"
else
  check_warn "Authentication chapter missing (recommended)"
fi

# --- CLI Command Spec Check ---
echo ""
echo "=== CLI Command Spec ==="

# Helper: extract lines inside ```bash code blocks from a file
extract_bash_blocks() {
  awk '/^```bash/{p=1;next} /^```/{p=0;next} p{print}' "$1" 2>/dev/null
}

# 16. No CLI config with plaintext credentials
HCS_FAIL=0
for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
  [[ -f "$f" ]] || continue
  if grep -qE 'hcloud[[:space:]]+configure[[:space:]]+set.*--access-key' "$f" 2>/dev/null; then
    check_fail "CLI config with --access-key in $(basename "$f") (use environment variables instead)"
    HCS_FAIL=$((HCS_FAIL+1))
  fi
done
if [[ $HCS_FAIL -eq 0 ]]; then
  check_pass "No CLI config with plaintext credentials"
fi

# 17. Commands must include --cli-region (only check code blocks)
CLI_REGION_FAIL=0
for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
  [[ -f "$f" ]] || continue
  FNAME=$(basename "$f")
  MATCH=$(extract_bash_blocks "$f" | grep -E '^\s*hcloud [A-Z]' | grep -vE '(--help|configure)' | grep -vE '\-\-cli-region' || true)
  if [[ -n "$MATCH" ]]; then
    while IFS= read -r line; do
      check_fail "hcloud command missing --cli-region in $FNAME: $line"
      CLI_REGION_FAIL=$((CLI_REGION_FAIL+1))
    done <<< "$MATCH"
  fi
done
if [[ $CLI_REGION_FAIL -eq 0 ]]; then
  check_pass "All hcloud commands in code blocks include --cli-region"
fi

# 18. Service name must be uppercase (check code blocks only)
SVC_FAIL=0
for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
  [[ -f "$f" ]] || continue
  FNAME=$(basename "$f")
  SVC_LIST=$(extract_bash_blocks "$f" | grep -oE 'hcloud [A-Za-z]+' | awk '{print $2}' | grep -vE '^[A-Z][A-Z0-9]*$' | grep -vE '^configure$' || true)
  if [[ -n "$SVC_LIST" ]]; then
    while IFS= read -r SVC; do
      check_fail "Service name not uppercase in $FNAME: '$SVC'"
      SVC_FAIL=$((SVC_FAIL+1))
    done <<< "$SVC_LIST"
  fi
done
if [[ $SVC_FAIL -eq 0 ]]; then
  check_pass "All service names in code blocks are uppercase"
fi

# 19. Operation name must be PascalCase (check code blocks only)
OP_FAIL=0
for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
  [[ -f "$f" ]] || continue
  FNAME=$(basename "$f")
  OP_LIST=$(extract_bash_blocks "$f" | grep -oE 'hcloud [A-Z]+ [A-Za-z]+' | awk '{print $3}' | grep -vE '^[A-Z][A-Za-z0-9]*$' || true)
  if [[ -n "$OP_LIST" ]]; then
    while IFS= read -r OP; do
      check_fail "Operation name not PascalCase in $FNAME: '$OP'"
      OP_FAIL=$((OP_FAIL+1))
    done <<< "$OP_LIST"
  fi
done
if [[ $OP_FAIL -eq 0 ]]; then
  check_pass "All operation names in code blocks are PascalCase"
fi

# --- Reference Docs Check ---
echo ""
echo "=== Reference Docs ==="
REF_DIR="$SKILL_PATH/references"
if [[ -d "$REF_DIR" ]]; then
  check_pass "references/ directory exists"
else
  check_warn "references/ directory missing"
fi

# 20. iam-policies.md
if [[ -f "$REF_DIR/iam-policies.md" ]]; then
  check_pass "references/iam-policies.md exists"
  if grep -qiE 'MFA' "$REF_DIR/iam-policies.md"; then
    check_pass "iam-policies.md includes MFA requirements"
  else
    check_warn "iam-policies.md missing MFA requirements"
  fi
else
  check_fail "references/iam-policies.md exists (required)"
fi

# 21. SKILL.md referenced references file check
if [[ -d "$REF_DIR" ]]; then
  REF_LINKS=$(grep -oE 'references/[a-zA-Z0-9_-]+\.md' "$SKILL_MD" 2>/dev/null | sort -u || true)
  for ref in $REF_LINKS; do
    if [[ -f "$SKILL_PATH/$ref" ]]; then
      check_pass "Referenced file exists: $ref"
    else
      check_fail "Referenced file missing: $ref"
    fi
  done
fi

# 22. Standard reference files
for ref_file in "cli-installation-guide.md" "verification-method.md" "acceptance-criteria.md" "related-commands.md"; do
  if [[ -f "$REF_DIR/$ref_file" ]]; then
    check_pass "references/$ref_file exists"
  else
    check_warn "references/$ref_file missing (recommended)"
  fi
done

# --- Security Scan ---
echo ""
echo "=== Security Scan ==="

# 23. Scan all files for hardcoded keys
SEC_FAIL=0
for f in "$SKILL_MD" "$SKILL_PATH/references/"*.md "$SKILL_PATH/templates/"*.template; do
  [[ -f "$f" ]] || continue
  FNAME=$(basename "$f")
  LINE_NUM=0
  while IFS= read -r line; do
    LINE_NUM=$((LINE_NUM+1))
    if echo "$line" | grep -qiE '(secret.key[[:space:]]*=[[:space:]]*[^$<{]|SECRET_KEY[[:space:]]*=[[:space:]]*["\x27][A-Za-z0-9]{10,})' 2>/dev/null; then
      if ! echo "$line" | grep -qE '(\{your_|placeholder|xxx|\$\{|<AK>|<SK>|AK>|SK>|=AK|=SK|--access-key=AK|--secret-key=SK)'; then
        check_fail "Hardcoded secret key in $FNAME L$LINE_NUM"
        SEC_FAIL=$((SEC_FAIL+1))
      fi
    fi
  done < "$f"
done
if [[ $SEC_FAIL -eq 0 ]]; then
  check_pass "No hardcoded secret keys detected"
fi

# --- Data Flow Diagram Check ---
echo ""
echo "=== Data Flow Diagram ==="

# 26. dataflow-diagram.md exists
DATAFLOW_FILE="$REF_DIR/dataflow-diagram.md"
if [[ -f "$DATAFLOW_FILE" ]]; then
  check_pass "references/dataflow-diagram.md exists"
  # 27. Contains Mermaid flowchart
  if grep -qE '```mermaid' "$DATAFLOW_FILE"; then
    check_pass "dataflow-diagram.md contains Mermaid code block"
  else
    check_fail "dataflow-diagram.md missing Mermaid code block"
  fi
  # 28. Contains flowchart keyword
  if grep -qE 'flowchart' "$DATAFLOW_FILE"; then
    check_pass "dataflow-diagram.md contains flowchart directive"
  else
    check_fail "dataflow-diagram.md missing flowchart directive"
  fi
  # 29. Contains primary flow arrows
  if grep -qF -- '-->' "$DATAFLOW_FILE"; then
    check_pass "dataflow-diagram.md contains primary data flow arrows (-->)"
  else
    check_fail "dataflow-diagram.md missing primary data flow arrows (-->)"
  fi
  # 30. Contains legend or description table
  if grep -qiE '(Legend|Data Flow Description)' "$DATAFLOW_FILE"; then
    check_pass "dataflow-diagram.md contains legend or description table"
  else
    check_warn "dataflow-diagram.md missing legend or description table (recommended)"
  fi
else
  check_fail "references/dataflow-diagram.md exists (required)"
fi

# --- Content Quality Checks ---
echo ""
echo "=== Content Quality ==="

# 31. Body line count
BODY_START=$(grep -n '^---' "$SKILL_MD" | sed -n '2p' | cut -d: -f1)
if [[ -n "$BODY_START" ]]; then
  TOTAL_LINES=$(wc -l < "$SKILL_MD")
  BODY_LINES=$((TOTAL_LINES - BODY_START))
  if [[ $BODY_LINES -le 500 ]]; then
    check_pass "Body lines: $BODY_LINES (<= 500)"
  else
    check_warn "Body lines: $BODY_LINES (> 500, recommended <= 500)"
  fi
else
  check_warn "Cannot determine body line count"
fi

# 32. Code block language annotation
CODE_BLOCKS=$(grep -cE '^\s*```[a-zA-Z]' "$SKILL_MD" 2>/dev/null || echo 0)
ALL_FENCES=$(grep -cE '^\s*```' "$SKILL_MD" 2>/dev/null || echo 0)
OPENING_TOTAL=$((ALL_FENCES / 2))
if [[ $OPENING_TOTAL -gt 0 ]] && [[ $CODE_BLOCKS -eq $OPENING_TOTAL ]]; then
  check_pass "All code blocks have language annotation"
elif [[ $OPENING_TOTAL -gt 0 ]] && [[ $CODE_BLOCKS -lt $OPENING_TOTAL ]]; then
  UNANNOTATED=$((OPENING_TOTAL - CODE_BLOCKS))
  check_warn "$UNANNOTATED code block(s) missing language annotation ($CODE_BLOCKS/$OPENING_TOTAL annotated)"
fi

# --- scripts/ Check ---
echo ""
echo "=== Scripts Check ==="
if [[ -d "$SKILL_PATH/scripts" ]]; then
  for script in "$SKILL_PATH/scripts"/*; do
    if [[ -f "$script" ]]; then
      SNAME=$(basename "$script")
      if grep -qiE '(AK[A-Z0-9]{16,}|SK[A-Z0-9]{16,})' "$script" 2>/dev/null; then
        check_fail "Possible hardcoded AK/SK in $SNAME"
      else
        check_pass "No hardcoded AK/SK in $SNAME"
      fi
      if head -1 "$script" | grep -qE '^#!/'; then
        check_pass "Shebang in $SNAME"
      else
        check_warn "Missing shebang in $SNAME"
      fi
      if echo "$SNAME" | grep -qE '\.py$'; then
        if [[ -f "$(dirname "$script")/__init__.py" ]]; then
          check_pass "__init__.py exists for Python script"
        else
          check_warn "Missing __init__.py for Python script $SNAME"
        fi
      fi
      if echo "$SNAME" | grep -qE '\.m?js$' && ! echo "$SNAME" | grep -qE '\.mjs$'; then
        check_warn "Node.js script $SNAME should use .mjs extension (ES Module)"
      fi
    fi
  done
else
  check_warn "No scripts/ directory"
fi

# --- Results ---
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
