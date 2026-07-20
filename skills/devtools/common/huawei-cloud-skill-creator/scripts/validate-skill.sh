#!/usr/bin/env bash
# validate-skill.sh — Validate Huawei Cloud Skill structure against 华为云Skill检查规范
set -euo pipefail

SKILL_DIR="${1:-.}"
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

[ -f "$SKILL_DIR/SKILL.md" ] && pass "SKILL.md exists" || fail "SKILL.md missing"

if [ -f "$SKILL_DIR/SKILL.md" ]; then
    # YAML Frontmatter
    grep -q '^---$' "$SKILL_DIR/SKILL.md" && pass "YAML Frontmatter present" || fail "Frontmatter missing"
    grep -q '^name:' "$SKILL_DIR/SKILL.md" && pass "name field present" || fail "name field missing"
    grep -q '^description:' "$SKILL_DIR/SKILL.md" && pass "description field present" || fail "description field missing"
    
    # version field (recommended, semver format)
    if grep -q '^version:' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
        if grep -q '^version:[[:space:]]*[0-9]\+\.[0-9]\+\.[0-9]\+' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
            pass "version field present (semver format)"
        else
            warn "version field present but not semver format (e.g. 2.0.0)"
        fi
    else
        warn "version field missing (recommended: semantic versioning)"
    fi
    
    # Description contains triggers
    grep -q 'Triggers include:' "$SKILL_DIR/SKILL.md" && pass "Triggers include: in description" || warn "Triggers include: missing"
    
    # 参考文档章节
    grep -q '##.*参考文档' "$SKILL_DIR/SKILL.md" && pass "参考文档 section present" || fail "参考文档 section missing"
    
    # No hardcoded credentials
    if grep -qiE '(access_key|secret_key|ak\s*=|sk\s*=|hcloud configure set)' "$SKILL_DIR/SKILL.md" 2>/dev/null | grep -v 'forbidden\|never\|禁止\|禁止硬编码' > /dev/null 2>&1; then
        fail "Possible hardcoded credentials found" || true
    else
        pass "No hardcoded credentials"
    fi
    
    # No cross-skill invocation
    if grep -qiE '(invoke|call).*huawei-cloud-' "$SKILL_DIR/SKILL.md" 2>/dev/null | grep -v '关联技能\|相关技能\|references' > /dev/null 2>&1; then
        fail "Cross-skill invocation detected" || true
    else
        pass "No cross-skill invocation"
    fi
fi

# references/iam-policies.md
[ -f "$SKILL_DIR/references/iam-policies.md" ] && pass "references/iam-policies.md exists" || fail "references/iam-policies.md missing"

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
for section in "概述" "前置条件" "工作流" "核心命令" "参数确认"; do
    if grep -q "##.*$section" "$SKILL_DIR/SKILL.md"; then
        pass "$section section present"
    else
        fail "$section section missing" || true
    fi
done

# CLI installation guide (if CLI is used)
[ -f "$SKILL_DIR/references/cli-installation-guide.md" ] && pass "references/cli-installation-guide.md exists" || warn "references/cli-installation-guide.md missing (recommended for CLI-based skills)"

# KooCLI command format section (mandatory for all skills)
    grep -q 'KooCLI.*命令格式' "$SKILL_DIR/SKILL.md" && pass "KooCLI命令格式标准 section present" || { fail "KooCLI命令格式标准 section missing" || true; }

# === MEDIUM Checks ===
echo ""
echo "--- Medium Priority Checks ---"

# Service name uppercase
if grep -qE '`hcloud [A-Z]' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
    pass "Service names use PascalCase"
else
    warn "No CLI commands found or service names not PascalCase"
fi

# Operation names PascalCase
if grep -qE '`hcloud [A-Z][a-z]+ [A-Z]' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
    pass "Operation names use PascalCase"
fi

# --cli-region in CLI commands
if grep -q 'hcloud' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
    grep -q 'cli-region' "$SKILL_DIR/SKILL.md" && pass "--cli-region present in CLI commands" || warn "--cli-region missing in some CLI commands"
fi

# verification-method.md
[ -f "$SKILL_DIR/references/verification-method.md" ] && pass "references/verification-method.md exists" || warn "references/verification-method.md missing (recommended)"

# === LOW Checks ===
echo ""
echo "--- Low Priority Checks ---"

# acceptance-criteria.md
[ -f "$SKILL_DIR/references/acceptance-criteria.md" ] && pass "references/acceptance-criteria.md exists" || warn "references/acceptance-criteria.md missing (recommended)"

# kebab-case references
kebab_ok=0
kebab_total=0
for ref in "$SKILL_DIR/references/"*.md; do
    [ -f "$ref" ] || continue
    kebab_total=$((kebab_total + 1))
    base=$(basename "$ref")
    if echo "$base" | grep -qE '^[a-z0-9-]+\.md$'; then
        kebab_ok=$((kebab_ok + 1))
    fi
done
[ "$kebab_total" -gt 0 ] && [ "$kebab_ok" -eq "$kebab_total" ] && pass "All reference files use kebab-case" || warn "Some reference files don't use kebab-case"

# CLI write operation confirmation
if grep -qiE '(Create|Delete|Update)' "$SKILL_DIR/SKILL.md" 2>/dev/null; then
    grep -qiE '确认|confirm|用户确认' "$SKILL_DIR/SKILL.md" && pass "Write operation confirmation mentioned" || warn "Write operations may need user confirmation"
fi

# === Security Audit (skill-targeted-audit) ===
echo ""
echo "--- Security Audit (skill-targeted-audit) ---"

AUDIT_SCRIPT=""
for candidate in \
    "$(dirname "$0")/../scripts/skill_audit.py" \
    "$(dirname "$0")/../../skill-targeted-audit/scripts/skill_audit.py" \
    "${HOME}/.agents/skills/skill-targeted-audit/scripts/skill_audit.py"; do
    if [ -f "$candidate" ]; then
        AUDIT_SCRIPT="$candidate"
        break
    fi
done

if [ -n "$AUDIT_SCRIPT" ] && command -v python3 &>/dev/null; then
    echo "  Running skill_audit.py ..."
    AUDIT_OUTPUT=$(python3 "$AUDIT_SCRIPT" --target "$SKILL_DIR" --no-install 2>&1) || true
    REPORT_FILE=$(echo "$AUDIT_OUTPUT" | grep -oP 'Report saved: \K.+')
    if [ -n "$REPORT_FILE" ] && [ -f "$REPORT_FILE" ]; then
        VERDICT=$(grep -oP 'Gate Verdict: \K\w+' "$REPORT_FILE" || echo "UNKNOWN")
        if [ "$VERDICT" = "PASS" ]; then
            pass "Security audit: PASS (see $REPORT_FILE)"
        else
            ISSUE_COUNT=$(grep -cP '^\s+\[(CRITICAL|ERROR|WARNING)\]' "$REPORT_FILE" 2>/dev/null || echo "0")
            fail "Security audit: FAIL ($ISSUE_COUNT issues, see $REPORT_FILE)" || true
        fi
    else
        warn "Security audit: could not parse report (audit may have missing dependencies)"
    fi
else
    warn "Security audit: skipped (skill_audit.py not found or python3 unavailable)"
fi

# === Summary ===
echo ""
echo "============================================"
echo "  Validation Summary"
echo "  PASS: $PASS  FAIL: $FAIL  WARN: $WARN"
echo "============================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
