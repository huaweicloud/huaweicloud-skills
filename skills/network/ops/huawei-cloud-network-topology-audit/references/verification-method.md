# Verification Method

## Prerequisites

- Huawei Cloud credentials configured (AK/SK environment variables)
- Python 3.8+ with huaweicloudsdkdcs installed (for DCS path B script)
- hcloud CLI installed and configured

## Verification Steps

### 1. Validate Rule Directory

```bash
python3 scripts/validate-rules.py rules/network-audit-rules.yaml
```

Expected: All 42 rules pass validation with no errors.

### 2. Precheck Script

```bash
bash scripts/precheck.sh
```

Expected: Exit 0 if credentials are valid. Exit non-zero if not configured.

### 3. DCS Query Script Test

```bash
python3 scripts/query-dcs-instances.py --region=cn-north-4
```

Expected: Returns list of DCS instances (or empty list if none exist).

### 4. Structural Integrity

Verify the directory structure:

```
huawei-cloud-network-topology-audit/
├── SKILL.md
├── rules/
│   └── network-audit-rules.yaml
├── references/
│   ├── resource-skill-mapping.md
│   ├── official-doc-index.md
│   ├── severity-definitions.md
│   ├── rule-authoring-guide.md
│   ├── iam-policies.md
│   ├── cli-installation-guide.md
│   ├── dataflow-diagram.md
│   └── verification-method.md
└── scripts/
    ├── precheck.sh
    ├── validate-rules.py
    ├── mermaid-to-ascii.sh
    ├── query-dcs-instances.py
    └── skill_quality_sdk.py
```

### 5. Validation Script Test

```bash
python3 -c "
import yaml
with open('rules/network-audit-rules.yaml') as f:
    rules = yaml.safe_load(f)
print(f'{len(rules)} rules loaded')
severities = set(r['severity'] for r in rules)
print(f'Severities used: {severities}')
print('All rules valid' if all('id' in r and 'resource_type' in r for r in rules) else 'ERROR: missing fields')
"
```