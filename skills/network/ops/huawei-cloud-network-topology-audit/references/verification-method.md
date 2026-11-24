# Verification Method

## Prerequisites

- Huawei Cloud credentials configured as one complete AK/SK pair (see `SKILL.md` § Prerequisites for
  the supported variable names) or an hcloud CLI profile
- Python 3.8+ with PyYAML installed (`pip install pyyaml`) — required by `scripts/validate-rules.py`
- `huaweicloudsdkdcs` installed for the DCS path B script (`pip install huaweicloudsdkdcs`)
- hcloud CLI installed and configured (optional; only for CCE queries)

## Verification Steps

### 1. Validate Rule Directory

```bash
python3 scripts/validate-rules.py rules/network-audit-rules.yaml
```

Expected: all 42 rules pass validation, exit code `0`. Missing PyYAML or an unreadable file prints a
readable error and exits `2`; invalid YAML or rule errors exit `1`.

### 2. Precheck Script

```bash
bash scripts/precheck.sh
```

Expected: `[precheck] PASS` and exit code `0` when credentials are valid. Missing credentials exit
`1` with the full list of supported AK/SK pairs; an unreachable VPC API exits `2`.

### 3. DCS Query Script Test

```bash
python3 scripts/query-dcs-instances.py --region=cn-north-4
```

Expected: returns a DCS instance list (or `(none found)`) and exit code `0` when credentials are
available. Without credentials it prints a readable error listing all supported AK/SK pairs and
exits `2`; without `huaweicloudsdkdcs` it exits `3`.

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

### 6. Security Defaults

```bash
# Reporting must stay off unless explicitly enabled (no default data egress).
python3 -c "import os; print('reporting enabled' if os.environ.get('SKILL_QUALITY_ENABLE') == '1' else 'reporting disabled by default')"

# No certificate-validation bypass may remain in the code.
grep -rn "verify_mode\|_create_unverified_context" scripts/ && echo "UNEXPECTED" || echo "no TLS bypass"
```

Expected: reporting is disabled by default and no TLS bypass exists.