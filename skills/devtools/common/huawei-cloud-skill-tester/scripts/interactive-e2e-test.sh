#!/bin/bash
#===============================================================================
# interactive-e2e-test.sh — Generic End-to-End Interactive Skill Creation Test
#
# Reads any skill-creator's templates, dynamically parses {{VAR}} placeholders,
# generates smart default values from the skill's own metadata, scaffolds a
# complete skill, validates it, and tests CLI commands.
#
# Usage:
#   bash scripts/interactive-e2e-test.sh <skill-creator-path> [options]
#===============================================================================

set -euo pipefail

CREATOR_PATH=""
TEST_VARS_FILE=""
OUTPUT="./interactive-e2e-report.yaml"
DRY_RUN=false
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0
RESULTS=()

usage() {
  cat <<'USAGE_EOF'
Usage: bash scripts/interactive-e2e-test.sh <skill-creator-path> [options]
  --test-vars <file>    JSON with preset answers (overrides auto-generate)
  --output <path>       Report output path
  --dry-run             Parse only, no scaffold
USAGE_EOF
  exit 1
}

[ $# -ge 1 ] || usage
CREATOR_PATH="$1"; shift

while [ $# -gt 0 ]; do
  case "$1" in
    --test-vars) TEST_VARS_FILE="$2"; shift 2 ;;
    --output)    OUTPUT="$2"; shift 2 ;;
    --dry-run)   DRY_RUN=true; shift ;;
    *) usage ;;
  esac
done

log_pass() { echo "[PASS] [e2e] $1"; PASS_COUNT=$((PASS_COUNT + 1)); RESULTS+=("PASS|$1"); }
log_fail() { echo "[FAIL] [e2e] $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); RESULTS+=("FAIL|$1"); }
log_warn() { echo "[WARN] [e2e] $1"; WARN_COUNT=$((WARN_COUNT + 1)); RESULTS+=("WARN|$1"); }
log_info() { echo "[INFO] [e2e] $1"; }

echo "============================================"
echo "  Interactive E2E Test — Skill Creation"
echo "============================================"
echo ""

#--- Step 0: Read skill metadata ---
log_info "=== Step 0: Reading skill metadata ==="
SKILL_MD="$CREATOR_PATH/SKILL.md"
CREATOR_NAME=""; CREATOR_SERVICE=""; CREATOR_TAGS=""

if [ -f "$SKILL_MD" ]; then
  CREATOR_NAME=$(grep '^name:' "$SKILL_MD" | head -1 | awk '{print $2}' | tr -d '"' || echo "unknown")
  CREATOR_TAGS=$(grep '^tags:' "$SKILL_MD" | head -1 | sed 's/tags: *\[//;s/\].*//' | xargs || echo "")
  log_pass "Read creator metadata: $CREATOR_NAME"
  for tag in $(echo "$CREATOR_TAGS" | tr ',' ' '); do
    tag=$(echo "$tag" | tr -d '"' | xargs)
    svc=$(echo "$tag" | tr '[:lower:]' '[:upper:]')
    case "$svc" in
      ECS|VPC|OBS|RDS|IAM|CCE|ELB|DNS|SMN|LTS|CES|BSS|DCS|NAT|VPN|AS|IMS|EVS|SFS|DDS|WAF|CBR|AOM)
        [ -z "$CREATOR_SERVICE" ] && CREATOR_SERVICE="$svc" ;;
    esac
  done
fi
[ -z "$CREATOR_SERVICE" ] && CREATOR_SERVICE="ECS"
log_info "  Detected service: $CREATOR_SERVICE"

#--- Step 1: Template analysis ---
echo ""
log_info "=== Step 1: Template Analysis ==="
TEMPLATES_DIR="$CREATOR_PATH/templates"
if [ ! -d "$TEMPLATES_DIR" ]; then
  log_fail "Templates directory not found at $TEMPLATES_DIR"; exit 1
fi
log_pass "Templates directory found"

declare -a TEMPLATE_FILES=()
TEMPLATE_COUNT=0
while IFS= read -r -d '' tmpl; do
  TEMPLATE_FILES+=("$tmpl"); TEMPLATE_COUNT=$((TEMPLATE_COUNT + 1))
  log_pass "Template: $(basename "$tmpl")"
done < <(find "$TEMPLATES_DIR" -type f -print0 2>/dev/null)

# Parse all {{VAR}} patterns
VARS_JSON="[]"
if [ $TEMPLATE_COUNT -gt 0 ]; then
  VARS_JSON=$(python3 -c "
import json, os, re
all_vars = set()
for root, dirs, files in os.walk('$TEMPLATES_DIR'):
    for f in files:
        with open(os.path.join(root, f)) as fh:
            for m in re.finditer(r'\{\{([A-Z_][A-Z_0-9]*)\}\}', fh.read()):
                all_vars.add(m.group(1))
print(json.dumps(sorted(list(all_vars))))
" 2>&1)
fi

VARS_LIST=()
if echo "$VARS_JSON" | python3 -c "import sys,json; json.load(sys.stdin)" &>/dev/null 2>&1; then
  VARS_LIST=($(echo "$VARS_JSON" | python3 -c "import sys,json; [print(v) for v in json.load(sys.stdin)]" 2>/dev/null))
fi
log_info "  Found ${#VARS_LIST[@]} unique template variables"

#--- Step 2: Generate test values ---
echo ""
log_info "=== Step 2: Generating Test Values ==="
USER_VARS="{}"
[ -n "$TEST_VARS_FILE" ] && [ -f "$TEST_VARS_FILE" ] && USER_VARS=$(cat "$TEST_VARS_FILE") && log_info "Loaded user vars from: $TEST_VARS_FILE"

SERVICE_LOW=$(echo "$CREATOR_SERVICE" | tr '[:upper:]' '[:lower:]')
RESOURCE="server"
case "$CREATOR_SERVICE" in VPC)RESOURCE="vpc";; OBS)RESOURCE="bucket";; RDS)RESOURCE="instance";; IAM)RESOURCE="user";; CCE)RESOURCE="cluster";; ELB)RESOURCE="loadbalancer";; DNS)RESOURCE="zone";; BSS)RESOURCE="account";; NAT)RESOURCE="gateway";; esac

# Write generator to temp file to avoid heredoc quoting issues
cat > /tmp/hermes-e2e-gen.py << 'GENEOF'
import json, sys, os
all_vars = json.loads(sys.argv[1])
user_vars = json.loads(sys.argv[2])
svc = sys.argv[3]
svc_low = svc.lower()
res = sys.argv[4]
skill_name = 'huawei-cloud-' + svc_low + '-' + res + '-manage'
defaults = {}
for v in all_vars:
    if v == 'SKILL_NAME':   defaults[v] = skill_name
    elif v == 'TITLE':      defaults[v] = svc + ' ' + res.title() + ' Manager'
    elif v == 'SERVICE':    defaults[v] = svc
    elif v == 'SERVICE_LOW': defaults[v] = svc_low
    elif v == 'RESOURCE':   defaults[v] = res
    elif v == 'DOMAIN':
        if svc in ('ECS','AS','IMS'): defaults[v] = 'compute'
        elif svc in ('VPC','ELB','NAT','VPN','EIP'): defaults[v] = 'network'
        elif svc in ('OBS','EVS','SFS'): defaults[v] = 'storage'
        elif svc in ('RDS','DDS','GAUSSDB','DCS'): defaults[v] = 'database'
        elif svc in ('IAM','WAF','CBR'): defaults[v] = 'security'
        elif svc in ('CES','LTS','AOM'): defaults[v] = 'monitoring'
        else: defaults[v] = 'middleware'
    elif v == 'TAGS':       defaults[v] = json.dumps(['huawei-cloud', svc_low, res, 'management'])
    elif v == 'FUNCTIONAL_POSITIONING': defaults[v] = 'Manage and monitor ' + svc + ' ' + res + 's'
    elif v == 'TRIGGER_CONDITIONS': defaults[v] = '管理' + svc_low + ', 查看' + svc_low + ', manage ' + svc_low + ', ' + svc_low + ' management'
    elif v == 'PREREQUISITE': defaults[v] = 'Requires hcloud CLI with ' + svc + ' ReadOnlyAccess'
    elif v == 'OVERVIEW':   defaults[v] = 'A skill that manages Huawei Cloud ' + svc + ' ' + res + 's'
    elif v == 'STEP_1_TITLE': defaults[v] = 'List ' + svc + ' ' + res + 's'
    elif v == 'OPERATION_1': defaults[v] = 'List' + res[0].upper() + res[1:] + 's'
    elif 'PARAMS_1' in v:   defaults[v] = '--limit=10'
    elif v == 'ACTION_1':   defaults[v] = svc_low + ':' + res + 's:list'
    elif v == 'STEP_2_TITLE': defaults[v] = 'Show ' + res + ' Detail'
    elif v == 'OPERATION_2': defaults[v] = 'Show' + res[0].upper() + res[1:]
    elif 'PARAMS_2' in v:   defaults[v] = '--' + res + '_id={instance_id}'
    elif v == 'ACTION_2':   defaults[v] = svc_low + ':' + res + 's:get'
    elif v == 'STEP_3_TITLE': defaults[v] = 'Monitor ' + res + ' Status'
    elif v == 'OPERATION_3': defaults[v] = 'Show' + res[0].upper() + res[1:]
    elif 'PARAMS_3' in v:   defaults[v] = '--' + res + '_id={instance_id}'
    elif v == 'ACTION_3':   defaults[v] = svc_low + ':' + res + 's:get'
    elif v == 'EXAMPLE_1_TITLE': defaults[v] = 'List all ' + res + 's'
    elif v == 'EXAMPLE_1_OPERATION': defaults[v] = 'List' + res[0].upper() + res[1:] + 's'
    elif 'EXAMPLE_1_PARAMS' in v: defaults[v] = '--limit=20'
    elif v == 'EXAMPLE_2_TITLE': defaults[v] = 'Show ' + res + ' details'
    elif v == 'EXAMPLE_2_OPERATION': defaults[v] = 'Show' + res[0].upper() + res[1:]
    elif 'EXAMPLE_2_PARAMS' in v: defaults[v] = '--' + res + '_id=i-12345'
    elif v == 'EXAMPLE_3_TITLE': defaults[v] = 'Verify ' + svc + ' connectivity'
    elif v == 'EXAMPLE_3_OPERATION': defaults[v] = 'Show' + res[0].upper() + res[1:]
    elif 'EXAMPLE_3_PARAMS' in v: defaults[v] = '--' + res + '_id=i-12345'
    elif v == 'EDGE_CASE_1': defaults[v] = res.title() + ' not found'
    elif v == 'EDGE_CASE_1_SOLUTION': defaults[v] = 'Return error: ' + res + ' not found'
    elif v == 'EDGE_CASE_2': defaults[v] = 'Empty ' + res + ' list'
    elif v == 'EDGE_CASE_2_SOLUTION': defaults[v] = 'Return empty result with info'
    elif v == 'EDGE_CASE_3': defaults[v] = 'Insufficient permissions'
    elif v == 'EDGE_CASE_3_SOLUTION': defaults[v] = 'Guide to check IAM policy'
    elif v == 'VERIFY_OPERATION': defaults[v] = 'List' + res[0].upper() + res[1:] + 's'
    elif 'VERIFY_PARAMS' in v: defaults[v] = '--limit=1'
    elif v == 'RESOURCE_TYPE': defaults[v] = svc + ' ' + res
    elif v == 'BILLING_MODEL': defaults[v] = 'pay-per-use'
    elif v == 'ESTIMATED_COST': defaults[v] = 'varies by spec'
    elif v == 'DELETE_REQUIRES_MFA': defaults[v] = 'No'
    elif v == 'MFA_DESCRIPTION': defaults[v] = 'No MFA for read-only ops'
    elif v == 'SCRIPT_USAGE_SECTION': defaults[v] = 'Uses hcloud CLI commands directly'
    elif v == 'VERSION':    defaults[v] = '1.0.0'
result = {**defaults, **user_vars}
with open('/tmp/hermes-e2e-vars.json', 'w') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
GENEOF

python3 /tmp/hermes-e2e-gen.py "$VARS_JSON" "$USER_VARS" "$CREATOR_SERVICE" "$RESOURCE" "$CREATOR_NAME" 2>&1 || { log_fail "Failed to generate vars"; exit 1; }

VARS_JSON=$(cat /tmp/hermes-e2e-vars.json)
TEST_SKILL_NAME=$(echo "$VARS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('SKILL_NAME','unknown'))" 2>/dev/null || echo "unknown")
log_info "Test skill: $TEST_SKILL_NAME ($CREATOR_SERVICE)"
log_info "Generated ${#VARS_LIST[@]} variable values"

if [ "$DRY_RUN" = true ]; then
  log_info "DRY RUN: Would scaffold $TEST_SKILL_NAME"; log_pass "Dry run completed"; exit 0
fi

#--- Step 3: Scaffold ---
echo ""; log_info "=== Step 3: Scaffolding Skill ==="
TMP_SKILL=$(mktemp -d /tmp/hermes-interactive-e2e-XXXXXX)
SKILL_DIR="$TMP_SKILL/$TEST_SKILL_NAME"
trap "rm -rf $TMP_SKILL" EXIT
mkdir -p "$SKILL_DIR/references" "$SKILL_DIR/scripts" "$SKILL_DIR/templates" "$SKILL_DIR/i18n/zh-CN"

for tmpl in "${TEMPLATE_FILES[@]}"; do
  base_name=$(basename "$tmpl")
  dst=""
  case "$base_name" in
    SKILL.md.template)                  dst="$SKILL_DIR/SKILL.md" ;;
    iam-policies.md.template)           dst="$SKILL_DIR/references/iam-policies.md" ;;
    dataflow-diagram.md.template)       dst="$SKILL_DIR/references/dataflow-diagram.md" ;;
    verification-method.md.template)    dst="$SKILL_DIR/references/verification-method.md" ;;
    cli-installation-guide.md.template) dst="$SKILL_DIR/references/cli-installation-guide.md" ;;
    test-report.md.template)            dst="$SKILL_DIR/references/test-report.md" ;;
    i18n-zh-CN-SKILL_CN.md.template)   dst="$SKILL_DIR/i18n/zh-CN/SKILL_CN.md" ;;
    *)                                  dst="$SKILL_DIR/references/$base_name" ;;
  esac
  python3 -c "
import json
with open('$tmpl') as f: content = f.read()
with open('/tmp/hermes-e2e-vars.json') as f: data = json.load(f)
for k, v in data.items(): content = content.replace('{{' + k + '}}', str(v))
with open('$dst', 'w') as f: f.write(content)
" 2>&1 && log_pass "Rendered: $base_name" || log_fail "Failed: $base_name"
done

for refdir in "references" "scripts"; do
  [ -d "$CREATOR_PATH/$refdir" ] || continue
  for f in "$CREATOR_PATH/$refdir/"*; do
    bname=$(basename "$f"); [ -f "$SKILL_DIR/$refdir/$bname" ] && continue
    cp "$f" "$SKILL_DIR/$refdir/" 2>/dev/null; chmod +x "$SKILL_DIR/$refdir/$bname" 2>/dev/null || true
  done
done

STRUCTURE_OK=true
for dir in references scripts templates i18n; do
  [ -d "$SKILL_DIR/$dir" ] && log_pass "Directory $dir/ created" || { log_fail "Directory $dir/ missing"; STRUCTURE_OK=false; }
done
[ -f "$SKILL_DIR/SKILL.md" ] && log_pass "SKILL.md created" || { log_fail "SKILL.md missing"; STRUCTURE_OK=false; }
$STRUCTURE_OK && log_pass "Skill structure verified [required]" || { log_fail "Skill structure incomplete"; echo "==="; exit 1; }

#--- Step 4: Validate ---
echo ""; log_info "=== Step 4: Validate Created Skill ==="
if [ -f "$SKILL_DIR/scripts/validate-skill.sh" ]; then
  bash "$SKILL_DIR/scripts/validate-skill.sh" "$SKILL_DIR" --phase all 2>&1 &&     log_pass "Validation: all passed [required]" || log_fail "Validation: some failed [required]"
else
  for field in name description version tags; do
    grep -q "^$field:" "$SKILL_DIR/SKILL.md" 2>/dev/null &&       log_pass "Frontmatter $field present" || log_fail "Frontmatter $field missing"
  done
  for s in "$SKILL_DIR/scripts/"*.sh; do
    [ -x "$s" ] && log_pass "$(basename $s) executable" || log_fail "$(basename $s) not executable"
  done
fi

#--- Step 5: CLI test ---
echo ""; log_info "=== Step 5: CLI Commands Test ==="
if [ -f "$SKILL_DIR/scripts/test-cli-commands.sh" ]; then
  bash "$SKILL_DIR/scripts/test-cli-commands.sh" "$SKILL_DIR" --region cn-north-4 2>&1 &&     log_pass "CLI test: passed [required]" || log_fail "CLI test: failed [required]"
fi

#--- Step 6: Verify answers ---
echo ""; log_info "=== Step 6: Verify Skill Content ==="
grep -qi "$CREATOR_SERVICE" "$SKILL_DIR/SKILL.md" 2>/dev/null &&   log_pass "SKILL.md references $CREATOR_SERVICE" || log_warn "Missing service ref"
OP1=$(echo "$VARS_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('OPERATION_1',''))" 2>/dev/null || true)
[ -n "$OP1" ] && grep -qi "$OP1" "$SKILL_DIR/SKILL.md" 2>/dev/null &&   log_pass "SKILL.md includes $OP1" || log_warn "Missing operation $OP1"

#--- Report ---
echo ""; echo "=== E2E Interactive Test Summary ==="
echo "PASS: $PASS_COUNT | FAIL: $FAIL_COUNT | WARN: $WARN_COUNT"
{
  echo "interactive_e2e_test_report:"
  echo "  skill_name: "$TEST_SKILL_NAME""
  echo "  template_source: "$CREATOR_NAME""
  echo "  timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  echo "  pass_count: $PASS_COUNT"
  echo "  fail_count: $FAIL_COUNT"
  echo "  warn_count: $WARN_COUNT"
  echo "  results:"
  for r in "${RESULTS[@]}"; do
    s=$(echo "$r" | cut -d'|' -f1)
    d=$(echo "$r" | cut -d'|' -f2-)
    echo "    - status: $s"
    echo "      description: "$d""
  done
} > "$OUTPUT"

rm -f /tmp/hermes-e2e-vars.json /tmp/hermes-e2e-gen.py
log_pass "Report generated: $OUTPUT"
[ $FAIL_COUNT -gt 0 ] && { echo "Status: FAIL"; exit 1; } || { echo "Status: PASS"; exit 0; }
