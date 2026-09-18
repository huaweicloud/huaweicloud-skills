# Verification Methods

## Manual Testing Steps

### Step 1: Verify Prerequisites
```bash
# Check hcloud CLI installation and configuration
hcloud version
hcloud configure list

# Verify IAM permissions (should return policy list)
hcloud WAF ListPolicy --page=1 --pagesize=1
```

### Step 2: Test Read-Only Commands (Safe)
```bash
# List policies
hcloud WAF ListPolicy --page=1 --pagesize=10

# Show policy details (replace <policy_id> with actual ID)
hcloud WAF ShowPolicy --policy_id=<policy_id>

# List rules by type
hcloud WAF ListCustomRules --policy_id=<policy_id>
hcloud WAF ListCcRules --policy_id=<policy_id>
hcloud WAF ListWhiteblackipRule --policy_id=<policy_id>
hcloud WAF ListGeoipRule --policy_id=<policy_id>
hcloud WAF ListIgnoreRule --policy_id=<policy_id>
hcloud WAF ListAnticrawlerRules  --policy_id=<policy_id>
hcloud WAF ListPrivacyRule --policy_id=<policy_id>
hcloud WAF ListAntitamperRule --policy_id=<policy_id>
hcloud WAF ListAntileakageRules --policy_id=<policy_id>
hcloud WAF ListIpReputationRules --policy_id=<policy_id>
```

### Step 3: Test Write Commands (Require User Confirmation)
```bash
# Create test policy
hcloud WAF CreatePolicy --name=test_verification_policy

# Update policy settings
hcloud WAF UpdatePolicy --policy_id=<policy_id> --level=2 --action.category=log

# Delete test policy (CAUTION: destructive operation)
hcloud WAF DeletePolicy  --policy_id=<policy_id>
```

### Step 4: Test Rule Creation (One Example per Type)
```bash
# Create custom rule
hcloud WAF CreateCustomRule \
  --policy_id=<policy_id> \
  --name=test_custom_rule \
  --priority=1 \
  --action.category=log \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=/test \
  --time=false

# Create CC rule (requires --cli-jsonInput due to --mode conflict)
# See SKILL.md section 3.2 for JSON template

# Create whitelist/blacklist rule
hcloud WAF CreateWhiteblackipRule \
  --policy_id=<policy_id> \
  --name=test_ip_rule \
  --white=0 \
  --addr=192.168.1.0/24

# Create geo-access control rule
hcloud WAF CreateGeoipRule \
  --policy_id=<policy_id> \
  --name=test_geo_rule \
  --geoip="CN|US" \
  --white=0

# Create global whitelist (ignore) rule (requires --cli-jsonInput due to --mode conflict)
# See SKILL.md section 3.5 for JSON template

# Create anti-crawler rule
hcloud WAF CreateAnticrawlerRule \
  --policy_id=<policy_id> \
  --name=test_anticrawler \
  --type=javascript \
  --priority=1 \
  --conditions.1.category=url \
  --conditions.1.logic_operation=contain \
  --conditions.1.contents.1=/admin

# Create privacy masking rule
hcloud WAF CreatePrivacyRule \
  --policy_id=<policy_id> \
  --url=/api/* \
  --category=password \
  --index=0

# Create anti-tamper rule
hcloud WAF CreateAntiTamperRule \
  --policy_id=<policy_id> \
  --hostname=example.com \
  --url=/critical/*

# Create anti-leakage rule
hcloud WAF CreateAntileakageRule \
  --policy_id=<policy_id> \
  --url=/api/sensitive/* \
  --category=phone \
  --contents.1=\\d{11}

# Create IP reputation rule
hcloud WAF CreateIpReputationRule \
  --policy_id=<policy_id> \
  --name=test_ip_reputation \
  --action.category=block \
  --type=idc \
  --tags.1=IDC_Malicious
```

### Step 5: Clean Up Test Resources
```bash
# Delete all test rules created in Step 4
# Use BatchDeleteRules or individual delete commands
# See SKILL.md "Delete Old Rules" section for details

# Delete test policy
hcloud WAF DeletePolicy --policy_id=<policy_id>
```

## JSON Import Verification

### Pre-Import Checklist
- [ ] JSON file exported by `huawei-cloud-waf-policy-query` skill
- [ ] JSON contains required fields: `metadata`, `basic_info`, `module_status`, `rule_details`
- [ ] Target region specified in `metadata.region` is accessible
- [ ] User has appropriate IAM permissions for WAF operations

### Import Validation Steps
1. **Dry Run Analysis**: Review JSON structure and field mappings before import
2. **Small-Scale Test**: Import a simple policy first (fewer rules) to validate workflow
3. **Verify After Import**: Use read-only commands to confirm all rules were created correctly
4. **Check Policy Status**: Ensure policy is enabled and bound to correct domains

### Common Issues to Check
- Missing `project_id` in JSON path parameters
- Invalid `policy_id` references
- Unsupported regions or permission errors
- Parameter conflicts requiring `--cli-jsonInput` (CC rules, global whitelist)

## Command Syntax Verification

### Verify All Commands Have Required Parameters
```bash
# Test each command with --help to confirm parameter names
hcloud WAF CreatePolicy --help | Select-String "name|region"
hcloud WAF CreateCustomRule --help | Select-String "policy_id|name|priority|action|conditions"
hcloud WAF CreateCcRule --help | Select-String "policy_id|mode|conditions"
# ... repeat for other commands
```

### Verify Nested Parameter Format
All nested parameters must use dot notation:
- ✅ Correct: `--action.category=block`
- ❌ Incorrect: `--action=block`

Array parameters must use indexed notation:
- ✅ Correct: `--conditions.1.category=url --conditions.1.contents.1=/test`
- ❌ Incorrect: `--conditions[0].category=url`
