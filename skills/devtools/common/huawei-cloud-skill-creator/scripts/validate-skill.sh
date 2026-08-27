#!/usr/bin/env bash
# validate-skill.sh — Validate Huawei Cloud Skill structure against 华为云Skill检查规范
# Usage: bash validate-skill.sh [-s <skill-dir>] [-b <base-ref>]
#   -s  Skill directory to validate (default: . ; may also be passed positionally)
#   -b  Base git ref for PR diff scope check (equivalent to legacy BASE_REF env var)
set -euo pipefail

SKILL_DIR="."

while getopts ":s:b:" opt; do
  case "$opt" in
    s) SKILL_DIR="$OPTARG" ;;
    b) BASE_REF="$OPTARG" ;;
    \?) echo "Unknown option: -$OPTARG" >&2; exit 1 ;;
    :) echo "Option -$OPTARG requires an argument" >&2; exit 1 ;;
  esac
done
shift $((OPTIND - 1))
# Backward-compat: accept skill dir as a trailing positional argument
if [ $# -gt 0 ]; then
  SKILL_DIR="$1"
fi

PASS=0
FAIL=0
WARN=0

pass() { echo "  ✅ PASS: $1"; PASS=$((PASS + 1)); return 0; }
fail() { echo "  ❌ FAIL: $1"; FAIL=$((FAIL + 1)); return 1; }
warn() { echo "  ⚠️  WARN: $1"; WARN=$((WARN + 1)); return 0; }

echo "============================================"
echo "  Validate Skill: $(basename "$SKILL_DIR")"
echo "  Against: 华为云Skill检查规范"
echo "============================================"

# === CRITICAL Checks ===
echo ""
echo "--- Critical Checks ---"

[ ! -d "$SKILL_DIR" ] && { echo "[FATAL] Skill directory not found: $SKILL_DIR"; exit 1; }
[ -f "$SKILL_DIR/SKILL.md" ] && pass "SKILL.md exists" || fail "SKILL.md missing"

if [ -f "$SKILL_DIR/SKILL.md" ]; then
    # YAML Frontmatter
    grep -q '^---$' "$SKILL_DIR/SKILL.md" && pass "YAML Frontmatter present" || fail "Frontmatter missing"
    grep -q '^name:' "$SKILL_DIR/SKILL.md" && pass "name field present" || fail "name field missing"
    grep -q '^description:' "$SKILL_DIR/SKILL.md" && pass "description field present" || fail "description field missing"

    FRONTMATTER_NAME=$(sed -n '2,/^---$/s/^name:[[:space:]]*//p' "$SKILL_DIR/SKILL.md" | head -n 1 | tr -d '"' | tr -d "'")
    if [ "$FRONTMATTER_NAME" = "$(basename "$SKILL_DIR")" ]; then
        pass "name field matches directory name"
    else
        fail "name field '$FRONTMATTER_NAME' does not match directory '$(basename "$SKILL_DIR")'" || true
    fi

    if grep -q '^version:' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
        warn "version field must be removed under Huawei Cloud Skill Specification v1.0"
    else
        pass "version field absent"
    fi

    grep -qiE '(Triggers include:|触发词|触发条件|Use when|Use ONLY when)' "$SKILL_DIR/SKILL.md" && pass "description includes trigger words or conditions" || warn "description trigger words or conditions missing"
    
    grep -qiE '^##[[:space:]].*(参考文档|Reference Documents|References)' "$SKILL_DIR/SKILL.md" && pass "Reference Documents section present" || fail "Reference Documents section missing"

    # === SEC-001 — Hardcoded AK/SK literal values ===
    # Pattern: any of access_key / secret_key / ak / sk paired with a literal
    # value (>=8 chars, alphanumeric/base64-ish). Matches e.g.
    #     HUAWEI_ACCESS_KEY="abcd1234..."
    #     secret_key: 'abcd1234...'
    #     "ak": "abcd1234..."
    # Whitelist: NEVER / FORBIDDEN / 禁止 contexts (skill prose explaining
    # what NOT to do) and placeholder templates (your-*, example,
    # placeholder, replace-me, <YOUR_*).
    _ak="access[_-]?key"
    _sk="secret[_-]?key"
    _pair="(^|[^[:alnum:]_])(ak|sk)"
    _value="[[:space:]]*[:=][[:space:]]*['\"]?[[:alnum:]_+/=-]{8,}"
    _sec001_pattern="(${_ak}|${_sk}|${_pair})${_value}"
    _sec001_whitelist='\b(forbidden|never|prohibit|禁止|不得|不应|检测|detection|scan|pattern|your[-_]|example|placeholder|replace-me)\b|<YOUR|<your'
    if grep -RniE "${_sec001_pattern}" "$SKILL_DIR" 2>/dev/null | grep -viE "${_sec001_whitelist}" > /dev/null; then
        fail "[SEC-001] Possible hardcoded AK/SK literal values found" || true
    else
        pass "[SEC-001] No hardcoded AK/SK literal values"
    fi

    # === SEC-002 — In-session AK/SK entry forms ===
    # Pattern: 'hcloud configure set ... --cli-(access|secret)-key=...'
    # AND 'BasicCredentials(..., access_key=..., secret_key=..., ak=..., sk=...)'
    # Both are in-band secret-entry forms that put AK/SK on a command
    # line / SDK kwarg, contradicting the Pre-check contract:
    #   'NEVER ask the user to type or paste AK/SK in chat; user must
    #    set env vars in shell profile out-of-band and re-run.'
    # Whitelist: lines that contain the patterns inside NEVER / Do NOT
    # / 禁止 / forbidden contexts (prose warnings about the anti-pattern
    # are allowed). Strict-mode design: one process-level pass with
    # the whitelist applied; false-positive tolerance is intentional.
    _hcloud_cfg_set='hcloud[[:space:]]+configure[[:space:]]+set[[:space:]]+.*--cli-(access|secret)-key[[:space:]]*='
    _basic_creds_literal='BasicCredentials[[:space:]]*\([^)]*(access_key|secret_key|ak[[:space:]]*=|sk[[:space:]]*=)'
    _sec002_pattern="${_hcloud_cfg_set}|${_basic_creds_literal}"
    _sec002_whitelist="${_sec001_whitelist}|literal"
    if grep -RniE "${_sec002_pattern}" "$SKILL_DIR" 2>/dev/null | grep -viE "${_sec002_whitelist}" > /dev/null; then
        fail "[SEC-002] In-session AK/SK entry form detected outside NEVER context (hcloud configure set --cli-*-key= or BasicCredentials literal kwargs)" || true
    else
        pass "[SEC-002] No in-session AK/SK entry forms outside NEVER context"
    fi

    CROSS_SKILL_REFS=""
    if command -v git >/dev/null 2>&1 && CHECK_ROOT=$(git -C "$SKILL_DIR" rev-parse --show-toplevel 2>/dev/null); then
        while IFS= read -r other_skill_md; do
            other_skill_name=$(basename "$(dirname "$other_skill_md")")
            [ "$other_skill_name" = "$(basename "$SKILL_DIR")" ] && continue
            if grep -Fqi "$other_skill_name" "$SKILL_DIR/SKILL.md"; then
                CROSS_SKILL_REFS=$(printf '%s\n%s' "$CROSS_SKILL_REFS" "$other_skill_name")
            fi
        done < <(find "$CHECK_ROOT" -name SKILL.md -type f 2>/dev/null)
    fi
    if grep -qiE '(\.\./[^[:space:]`]+/(SKILL\.md|scripts/)|\.agents/skills/[^[:space:]`]+)' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
        CROSS_SKILL_REFS=$(printf '%s\n%s' "$CROSS_SKILL_REFS" "cross-directory Skill path")
    fi
    CROSS_SKILL_REFS=$(printf '%s\n' "$CROSS_SKILL_REFS" | sed '/^$/d' | sort -u)
    if [ -n "$CROSS_SKILL_REFS" ]; then
        fail "Named cross-Skill references found; use Agent orchestration instead: $(printf '%s' "$CROSS_SKILL_REFS" | tr '\n' ' ')" || true
    else
        pass "No named cross-Skill references"
    fi
fi

# references/iam-policies.md
[ -f "$SKILL_DIR/references/iam-policies.md" ] && pass "references/iam-policies.md exists" || fail "references/iam-policies.md missing"

if command -v git >/dev/null 2>&1 && REPO_ROOT=$(git -C "$SKILL_DIR" rev-parse --show-toplevel 2>/dev/null); then
    if [ -n "${BASE_REF:-}" ]; then
        CHANGED_PATHS=$(git -C "$REPO_ROOT" diff --name-only "${BASE_REF}...HEAD" 2>/dev/null || true)
    else
        if git -C "$REPO_ROOT" rev-parse --quiet --verify HEAD >/dev/null 2>&1; then
            CHANGED_PATHS=$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | awk '{print $2}' | grep -E "^${SKILL_DIR#"$REPO_ROOT"/}/" || true)
        else
            CHANGED_PATHS=""
        fi
    fi
    CHANGED_SKILL_DIRS=""
    while IFS= read -r changed_path; do
        [ -n "$changed_path" ] || continue
        candidate="$REPO_ROOT/$(dirname "$changed_path")"
        while [ "$candidate" != "$REPO_ROOT" ] && [ "$candidate" != "$(dirname "$candidate")" ]; do
            if [ -f "$candidate/SKILL.md" ]; then
                CHANGED_SKILL_DIRS=$(printf '%s\n%s' "$CHANGED_SKILL_DIRS" "${candidate#"$REPO_ROOT"/}")
                break
            fi
            candidate=$(dirname "$candidate")
        done
    done <<< "$CHANGED_PATHS"
    CHANGED_SKILL_DIRS=$(printf '%s\n' "$CHANGED_SKILL_DIRS" | sed '/^$/d' | sort -u)
    CHANGED_SKILL_COUNT=$(printf '%s\n' "$CHANGED_SKILL_DIRS" | sed '/^$/d' | wc -l | tr -d ' ')
    if [ "$CHANGED_SKILL_COUNT" -le 1 ]; then
        pass "PR changes at most one Skill directory"
    else
        fail "PR changes $CHANGED_SKILL_COUNT Skill directories: $(printf '%s' "$CHANGED_SKILL_DIRS" | tr '\n' ' ')" || true
    fi
else
    warn "One-PR-one-Skill check skipped because no Git worktree was found"
fi

# === HIGH Checks ===
echo ""
echo "--- High Priority Checks ---"

# Naming convention
SKILL_NAME=$(basename "$SKILL_DIR")
if echo "$SKILL_NAME" | grep -qE '^huawei-cloud-[a-z0-9]+(-[a-z0-9]+)*$'; then
    pass "Naming convention: $SKILL_NAME"
else
    warn "Naming convention check: $SKILL_NAME (should be huawei-cloud-{product}-{function})"
fi

# Required sections
for section in "Overview|概述" "Prerequisites|前置条件" "Workflow|工作流" "Core Commands|核心命令" "Parameter Confirmation|参数确认"; do
    if grep -qiE "^##[[:space:]].*($section)" "$SKILL_DIR/SKILL.md"; then
        pass "${section%%|*} section present"
    else
        fail "${section%%|*} section missing" || true
    fi
done

CLI_USED=0
if grep -qE 'hcloud[[:space:]]+([^<{[:space:]][^[:space:]]*|[<{](Service|service)[}>])' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
    CLI_USED=1
fi

if [ "$CLI_USED" -eq 1 ]; then
    [ -f "$SKILL_DIR/references/cli-installation-guide.md" ] && pass "references/cli-installation-guide.md exists" || fail "references/cli-installation-guide.md missing for CLI-based Skill" || true
else
    pass "references/cli-installation-guide.md not required because no CLI command is used"
fi

# === MEDIUM Checks ===
echo ""
echo "--- Medium Priority Checks ---"

CLI_COMMAND_LINES=$(grep -E '(^[[:space:]]*hcloud[[:space:]]|`hcloud[[:space:]])' "$SKILL_DIR/SKILL.md" 2>/dev/null || true)
CLI_COMMAND_COUNT=0
SERVICE_ERRORS=0
OPERATION_ERRORS=0
REGION_ERRORS=0
while IFS= read -r cli_line; do
    [ -n "$cli_line" ] || continue
    echo "$cli_line" | grep -qiE '(forbidden|prohibit|禁止|不得|detection|检测)' && continue
    cli_tail=$(printf '%s\n' "$cli_line" | sed -E 's/^.*hcloud[[:space:]]+//')
    service=$(printf '%s\n' "$cli_tail" | awk '{print $1}' | tr -d '`')
    operation=$(printf '%s\n' "$cli_tail" | awk '{print $2}' | tr -d '`')
    printf '%s%s\n' "$service" "$operation" | grep -qE '[<>{}]' && continue
    [ -n "$service" ] && [ -n "$operation" ] || continue
    CLI_COMMAND_COUNT=$((CLI_COMMAND_COUNT + 1))
    echo "$service" | grep -qE '^[A-Z][A-Za-z0-9]*$' || SERVICE_ERRORS=$((SERVICE_ERRORS + 1))
    echo "$operation" | grep -qE '^[A-Z][A-Za-z0-9]*$' || OPERATION_ERRORS=$((OPERATION_ERRORS + 1))
    echo "$cli_line" | grep -q -- '--cli-region' || REGION_ERRORS=$((REGION_ERRORS + 1))
done <<< "$CLI_COMMAND_LINES"

if [ "$CLI_COMMAND_COUNT" -eq 0 ]; then
    warn "No concrete CLI commands found"
else
    [ "$SERVICE_ERRORS" -eq 0 ] && pass "All concrete service names begin with uppercase/title case" || warn "$SERVICE_ERRORS CLI command(s) have invalid service names"
    [ "$OPERATION_ERRORS" -eq 0 ] && pass "All concrete operation names use PascalCase" || warn "$OPERATION_ERRORS CLI command(s) have invalid operation names"
    [ "$REGION_ERRORS" -eq 0 ] && pass "Every concrete CLI command includes --cli-region" || warn "$REGION_ERRORS CLI command(s) omit --cli-region"
fi

# verification-method.md
[ -f "$SKILL_DIR/references/verification-method.md" ] && pass "references/verification-method.md exists" || warn "references/verification-method.md missing (recommended)"

# === LOW Checks ===
echo ""
echo "--- Low Priority Checks ---"

if command -v git >/dev/null 2>&1 && git -C "$SKILL_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
    SKILL_PREFIX=$(git -C "$SKILL_DIR" rev-parse --show-prefix 2>/dev/null | sed 's:/*$::')
    if echo "$SKILL_PREFIX" | grep -qE '^skills/[^/]+/[^/]+/[^/]+$'; then
        pass "Skill path matches skills/{category}/{subcategory}/{skill-name}/"
    else
        warn "Skill path '$SKILL_PREFIX' does not match skills/{category}/{subcategory}/{skill-name}/"
    fi
else
    warn "Skill path layout check skipped because no Git worktree was found"
fi

if [ "$CLI_USED" -eq 1 ]; then
    grep -qiE '^##[[:space:]].*(KooCLI.*(Command Format|命令格式)|CLI Command Format|CLI命令格式)' "$SKILL_DIR/SKILL.md" && pass "KooCLI Command Format Standard section present" || warn "KooCLI Command Format Standard section missing for CLI-based Skill"
fi

# --- Size constraints (华为云Skill检查规范 - hwcloud-spec) ---
# 1) Total skill file content size must not exceed 40 MB
TOTAL_BYTES=0
while IFS= read -r -d '' skill_file; do
    FILE_BYTES=$(wc -c < "$skill_file")
    TOTAL_BYTES=$((TOTAL_BYTES + FILE_BYTES))
done < <(find "$SKILL_DIR" -type f -print0 2>/dev/null)
TOTAL_MB=$(( (TOTAL_BYTES + 1048575) / 1048576 ))
if [ "$TOTAL_BYTES" -le 41943040 ]; then
    pass "Total file content size ≤ 40 MB (${TOTAL_MB} MB)"
else
    fail "Total file content size exceeds 40 MB (${TOTAL_MB} MB). Split or remove large files." || true
fi

# 2) Total file count must not exceed 30
TOTAL_FILES=$(find "$SKILL_DIR" -type f 2>/dev/null | wc -l)
if [ "$TOTAL_FILES" -le 30 ]; then
    pass "Total file count ≤ 30 ($TOTAL_FILES files)"
else
    fail "Total file count exceeds 30 ($TOTAL_FILES files). Consolidate or remove redundant files." || true
fi

# 3) SKILL.md line count must not exceed 500
if [ -f "$SKILL_DIR/SKILL.md" ]; then
    SKILL_LINES=$(wc -l < "$SKILL_DIR/SKILL.md")
    if [ "$SKILL_LINES" -le 500 ]; then
        pass "SKILL.md lines ≤ 500 ($SKILL_LINES lines)"
    else
        fail "SKILL.md exceeds 500 lines ($SKILL_LINES lines). Split content into references/." || true
    fi
fi

ALLOWED_EXTENSIONS="md mdx txt json json5 yaml yml toml js cjs mjs ts tsx jsx py sh ps1 psm1 psd1 r rb go rs swift kt java cs cpp c h hpp sql csv tsv ini cfg conf env properties dat xml html css scss sass svg"
INVALID_EXTENSION_FILES=""
while IFS= read -r -d '' skill_file; do
    base_name=$(basename "$skill_file")
    if [[ "$base_name" == *.* ]]; then
        extension=${base_name##*.}
        extension=$(printf '%s' "$extension" | tr '[:upper:]' '[:lower:]')
    else
        extension=""
    fi
    case " $ALLOWED_EXTENSIONS " in
        *" $extension "*) ;;
        *) INVALID_EXTENSION_FILES=$(printf '%s\n%s' "$INVALID_EXTENSION_FILES" "${skill_file#"$SKILL_DIR"/}") ;;
    esac
done < <(find "$SKILL_DIR" -type f -print0 2>/dev/null)
INVALID_EXTENSION_FILES=$(printf '%s\n' "$INVALID_EXTENSION_FILES" | sed '/^$/d')
if [ -z "$INVALID_EXTENSION_FILES" ]; then
    pass "All files use one of the 46 allowed extensions"
else
    fail "Files without an allowed extension: $(printf '%s' "$INVALID_EXTENSION_FILES" | tr '\n' ' ')" || true
fi

# acceptance-criteria.md
[ -f "$SKILL_DIR/references/acceptance-criteria.md" ] && pass "references/acceptance-criteria.md exists" || warn "references/acceptance-criteria.md missing (recommended)"

# kebab-case references
kebab_ok=0
kebab_total=0
while IFS= read -r -d '' ref; do
    kebab_total=$((kebab_total + 1))
    base=$(basename "$ref")
    if echo "$base" | grep -qE '^[a-z0-9]+(-[a-z0-9]+)*\.[a-z0-9]+$'; then
        kebab_ok=$((kebab_ok + 1))
    fi
done < <(find "$SKILL_DIR/references" -type f -print0 2>/dev/null)
[ "$kebab_total" -gt 0 ] && [ "$kebab_ok" -eq "$kebab_total" ] && pass "All reference files use kebab-case" || warn "Some reference files don't use kebab-case"

# CLI write operation confirmation
if grep -qiE '(Create|Delete|Update)' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
    grep -qiE '确认|confirm|用户确认' "$SKILL_DIR/SKILL.md" && pass "Write operation confirmation mentioned" || warn "Write operations may need user confirmation"
fi

# === Summary ===
echo ""
echo "============================================"
echo "  Validation Summary"
echo "  PASS: $PASS  FAIL: $FAIL  WARN: $WARN"
echo "============================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
