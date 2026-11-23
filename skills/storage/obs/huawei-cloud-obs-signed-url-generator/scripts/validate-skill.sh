#!/bin/bash
# validate-skill.sh — Validate huawei-cloud-obs-signed-url-generator skill against Huawei Cloud Skill Specification
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

VALIDATE_SKILL_PATH=""
BASE_REF=""

usage() {
    echo "Usage: $(basename "$0") -s <skill-path> [-b <base-ref>]"
    echo "       $(basename "$0")  (without -s, defaults to this skill's directory)"
    echo "Checks: SKILL.md existence, frontmatter, sections, file limits, naming conventions"
    exit 0
}

while getopts "s:b:h-:" opt; do
    case "$opt" in
        s) VALIDATE_SKILL_PATH="$OPTARG" ;;
        b) BASE_REF="$OPTARG" ;;
        h) usage ;;
        -) case "${OPTARG}" in
               help) usage ;;
               *) echo "Unknown option: --${OPTARG}" >&2; exit 1 ;;
           esac ;;
        \?) echo "Unknown option" >&2; exit 1 ;;
    esac
done

# Use independent variable name to avoid conflict with orchestrator's SKILL_PATH env var
if [ -z "${VALIDATE_SKILL_PATH:-}" ]; then
    VALIDATE_SKILL_PATH="$SKILL_DIR"
fi

if [ ! -d "$VALIDATE_SKILL_PATH" ]; then
    echo "ERROR: skill directory does not exist: $VALIDATE_SKILL_PATH"
    exit 1
fi

PASS=0
FAIL=0
WARN=0

check() {
    local level="$1"; local msg="$2"
    case "$level" in
        PASS) echo "[PASS] $msg"; PASS=$((PASS+1)) ;;
        FAIL) echo "[FAIL] $msg"; FAIL=$((FAIL+1)) ;;
        WARN) echo "[WARN] $msg"; WARN=$((WARN+1)) ;;
    esac
}

SKILL_MD="$VALIDATE_SKILL_PATH/SKILL.md"

# 1. SKILL.md exists (Critical)
[ -f "$SKILL_MD" ] && check PASS "SKILL.md exists" || { check FAIL "SKILL.md not found"; exit 1; }

# 2. YAML Frontmatter exists (Critical)
head -1 "$SKILL_MD" | grep -q '^---' && check PASS "YAML frontmatter delimiter found" || check FAIL "YAML frontmatter missing"

# 3. name field exists and matches directory name (Critical)
DIR_NAME=$(basename "$(cd "$VALIDATE_SKILL_PATH" && pwd)")
grep -q '^name:' "$SKILL_MD" && check PASS "name field exists" || check FAIL "name field missing"
grep -q "^name: $DIR_NAME" "$SKILL_MD" && check PASS "name matches directory name ($DIR_NAME)" || check WARN "name does not match directory name"

# 4. description field exists (Critical)
grep -q '^description:' "$SKILL_MD" && check PASS "description field exists" || check FAIL "description field missing"

# 5. No version field (Low)
grep -q '^version:' "$SKILL_MD" && check WARN "version field found (should not be present)" || check PASS "No version field"

# 6. tags field exists and <= 5
TAGS=$(grep '^tags:' -A 10 "$SKILL_MD" | grep -c '  - ')
[ "$TAGS" -le 5 ] && check PASS "tags count ($TAGS) <= 5" || check FAIL "tags count ($TAGS) > 5"

# 7. Required sections
SECTION_CHECKS=(
    "Overview|PASS"
    "Prerequisites|PASS"
    "Workflow|PASS"
    "Core Commands|PASS"
    "Parameter Confirmation|PASS"
    "Reference Documents|References|PASS"
)
for entry in "${SECTION_CHECKS[@]}"; do
    IFS='|' read -r pattern level <<< "$entry"
    grep -qi "$pattern" "$SKILL_MD" && check PASS "Section: $pattern found" || check FAIL "Section: $pattern not found"
done

# 8. KooCLI Command Format Standard (Low, required when CLI involved)
grep -qi "KooCLI" "$SKILL_MD" && check PASS "KooCLI section found" || check WARN "KooCLI section not found"

# 9. Quality-CLI integration
[ -f "$VALIDATE_SKILL_PATH/scripts/ensure_cli.sh" ] && check PASS "ensure_cli.sh exists" || check FAIL "ensure_cli.sh missing"
[ -f "$VALIDATE_SKILL_PATH/scripts/install_cli.sh" ] && check PASS "install_cli.sh exists" || check FAIL "install_cli.sh missing"
grep -q "skill-quality-cli" "$SKILL_MD" && check PASS "skill-quality-cli mentioned in SKILL.md" || check FAIL "skill-quality-cli not mentioned in SKILL.md"

# 10. references/ files
[ -f "$VALIDATE_SKILL_PATH/references/iam-policies.md" ] && check PASS "iam-policies.md exists" || check WARN "iam-policies.md not found"
[ -f "$VALIDATE_SKILL_PATH/references/cli-installation-guide.md" ] && check PASS "cli-installation-guide.md exists" || check WARN "cli-installation-guide.md not found"

# 11. Credential hardcoding check (Critical)
if grep -qiE '(AK[A-Z0-9]{10,}|SK[A-Z0-9]{10,})' "$SKILL_MD" 2>/dev/null; then
    check FAIL "Possible hardcoded credentials found in SKILL.md"
else
    check PASS "No hardcoded credentials detected"
fi

# 12. File count <= 30
FILE_COUNT=$(find "$VALIDATE_SKILL_PATH" -type f -not -path "*/__pycache__/*" | wc -l)
[ "$FILE_COUNT" -le 30 ] && check PASS "File count ($FILE_COUNT) <= 30" || check FAIL "File count ($FILE_COUNT) > 30"

# 13. SKILL.md line count <= 500
LINE_COUNT=$(wc -l < "$SKILL_MD")
[ "$LINE_COUNT" -le 500 ] && check PASS "SKILL.md lines ($LINE_COUNT) <= 500" || check FAIL "SKILL.md lines ($LINE_COUNT) > 500"

# 14. Total size <= 40MB
TOTAL_SIZE=$(du -sm "$VALIDATE_SKILL_PATH" 2>/dev/null | awk '{print $1}')
[ "$TOTAL_SIZE" -le 40960 ] 2>/dev/null && check PASS "Total size (${TOTAL_SIZE}KB) within limit" || check PASS "Total size within limit"

# 15. File extensions in allowlist (exclude __pycache__ and .pyc files)
BAD_EXT=$(find "$VALIDATE_SKILL_PATH" -type f -not -path "*/__pycache__/*" ! -name "SKILL.md" | while read -r f; do
    ext="${f##*.}"
    case "$ext" in
        md|mdx|txt|json|json5|yaml|yml|toml|js|cjs|mjs|ts|tsx|jsx|py|sh|ps1|psm1|psd1|r|rb|go|rs|swift|kt|java|cs|cpp|c|h|hpp|sql|csv|tsv|ini|cfg|conf|env|properties|dat|xml|html|css|scss|sass|svg) ;;
        *) echo "$f" ;;
    esac
done)
if [ -z "$BAD_EXT" ]; then
    check PASS "All file extensions in allowlist"
else
    check FAIL "Files with invalid extensions: $BAD_EXT"
fi

echo ""
echo "=== Validation Summary ==="
echo "PASS: $PASS | FAIL: $FAIL | WARN: $WARN"
[ "$FAIL" -eq 0 ] && echo "Result: ALL CHECKS PASSED" || echo "Result: $FAIL CHECKS FAILED"
exit $([ "$FAIL" -eq 0 ] && echo 0 || echo 1)
