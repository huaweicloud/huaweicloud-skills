---
name: huawei-cloud-network-topology-audit
description: |
  Orchestrator skill that audits Huawei Cloud network topology for security and configuration risks.
  Given a user-described access path (e.g., "ELB web-elb → CCE prod-cce → RDS prod-db"), it resolves
  the real topology, expands to the full VPC network surface, evaluates risks against an extensible
  rule directory, and produces a Markdown audit report with a Mermaid topology diagram.
  Triggers include: "组网审计", "网络拓扑审计", "安全组审计", "网络合理性检查", "网络风险审计",
  "network audit", "topology audit", "security group audit", "network risk check", "组网评估".
tags: [huawei-cloud, network, audit, topology, security]
---
# Huawei Cloud Network Topology Audit

> **Read-only orchestrator skill.** This skill audits existing cloud resources — it never creates,
> modifies, or deletes any resource. All data collection is delegated to existing query skills
> (path A) or self-written scripts based on official documentation (path B).

## Overview

This skill audits Huawei Cloud network topology for security and configuration risks. Given a
user-described access path (e.g., "ELB web-elb → CCE prod-cce → RDS prod-db"), it:

1. Resolves the real topology from actual cloud resources
2. Expands to the full VPC network surface (VPCs, subnets, route tables, security groups, EIPs,
   ELBs, NAT gateways, ECS, RDS, CCE, DCS)
3. Evaluates risks against an extensible rule directory (`rules/network-audit-rules.yaml`)
4. Produces a Markdown audit report with a Mermaid topology diagram

### Architecture

```
User describes access path (natural language)
         │
         ▼
 [Step 1]  Connectivity precheck  ── fail ──→  Prompt user to configure credentials
         │ pass
         ▼
 [Step 2]  Path parsing + find-skills lookup
         │
         ▼
 [Step 3]  Real topology discovery (Path A: query skills, Path B: self-written scripts)
         │
         ▼
 [Step 4]  Diff: described path vs real topology (real = source of truth)
         │
         ▼
 [Step 5]  User confirmation of the real topology
         │
         ▼
 [Step 6]  Risk audit against network-audit-rules.yaml
         │
         ▼
 [Step 7]  Markdown report generation (Mermaid diagram, ASCII fallback)
```

### Applicable Scenarios

- User describes an access path with approximate resource names
- Current environment has configured Huawei Cloud credentials (CLI/SDK)
- Need structured audit of network topology risks

### Not Applicable

- User cannot describe any resource names
- No Huawei Cloud credentials configured
- Need to modify resources (this skill is read-only)
- Cross-account audit (v1 limited to single account)

## Prerequisites

1. **Huawei Cloud credentials** — one complete AK/SK pair in the environment, or an hcloud CLI
   profile (hcloud configure set --cli-region=<region>). Supported pairs, checked in this order
   (identical in `scripts/precheck.sh` and `scripts/query-dcs-instances.py`):
   - `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK`
   - `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`
   - `HW_ACCESS_KEY` / `HW_SECRET_KEY`
   - `HWC_AK` / `HWC_SK`
   - `HWC_ACCESS_KEY` / `HWC_SECRET_KEY`

   Never commit real keys to the repository or paste them into examples.
2. **Python 3.8+** — Required for scripts in `scripts/`
3. **PyYAML** — Required by `scripts/validate-rules.py`: `pip install pyyaml`
4. **huaweicloudsdk packages** — For path B resources (DCS): `pip install huaweicloudsdkdcs`
   (also `pip install huaweicloudsdkvpc` if you use the SDK fallback in `scripts/precheck.sh`)
5. **Network access** — To GitCode for find-skills index queries
6. **hcloud CLI** (optional) — For CCE cluster queries via CCE management skill

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SKILL_QUALITY_ENABLE` | No | Set `1` to opt in to quality reporting; **disabled by default** |
| `SKILL_QUALITY_ENDPOINT` | No | Report endpoint (https only), default https://skillsapi.developer.myhuaweicloud.com/api/quality/report |
| `SKILL_QUALITY_NAME` | No | Skill name (auto-detected) |
| `SKILL_QUALITY_DISABLE` | No | Set `1` to force-disable reporting (overrides `SKILL_QUALITY_ENABLE`) |
| `SKILL_QUALITY_TIMEOUT` | No | Report timeout in seconds (default 3) |

## Workflow

### Step 1: Connectivity Precheck

Run the precheck script to verify credentials are available and the API is reachable:

```bash
bash scripts/precheck.sh
```

- **Exit 0**: Credentials OK, VPC API reachable → proceed to Step 2
- **Exit non-zero**: Print error, tell user to configure credentials, **stop**

### Step 2: Path Parsing & Find-Skills Lookup

Parse the user's natural-language access path:

1. Extract resource types and approximate names (e.g., "ELB web-elb" → type=elb_listener,
   name="web-elb")
2. For each resource type, look up the appropriate query skill in
   `references/resource-skill-mapping.md`
3. Use the skill discovery index (search script) to confirm the query skill exists in the
   current index
4. Build a structured collection plan:
   - Path A resources → dispatch to query skill
   - Path B resources → use self-written script

**Output**: Structured path draft + collection path mapping

### Step 3: Real Topology Discovery

Execute the collection plan:

#### Path A (existing query skills)

| Resource | Query Skill Category | Key Queries |
|----------|----------------------|-------------|
| VPC | network inventory query skill | ListVpcs, ShowVpc |
| Subnet | network inventory query skill | ListSubnets |
| Security Group | network inventory query skill | ListSecurityGroups, ShowSecurityGroup |
| Route Table | network inventory query skill | ListRouteTables |
| EIP | network inventory query skill | ListPublicips |
| ELB | network inventory query skill | ListLoadBalancers, ListListeners, ListPools |
| NAT | network inventory query skill | ListNatGateways, ListSnatRules, ListDnatRules |
| ECS | compute inventory query skill | ListServersDetails |
| RDS | database inventory query skill | ListInstances |
| CCE | CCE cluster query skill | ListClusters, ListNodes |

#### Path B (self-written scripts)

| Resource | Script | SDK Used |
|----------|--------|----------|
| DCS | `scripts/query-dcs-instances.py` | `huaweicloudsdkdcs.v2` |

1. For each path A resource, invoke the query skill and collect structured data
2. For path B, run the self-written script
3. After collecting the described resources, **expand to the full VPC network surface**:
   - Find the VPC that contains the described resources
   - Query ALL resources in that VPC (all subnets, all security groups, all route tables,
     all EIPs, all ELBs, all NAT gateways, all ECS instances, all RDS instances, all CCE
     clusters, all DCS instances)
4. Merge all data into a unified topology dataset

**Output**: Real topology dataset (all resources in the VPC network surface)

### Step 4: Diff Analysis

Compare the user-described path against the real topology:

1. For each resource in the user's description:
   - Match by approximate name (case-insensitive, substring match)
   - Confirm resource type
   - Record any differences (wrong name, wrong type, resource not found)
2. Build a diff list where the real topology is the **source of truth**
3. Flag resources the user mentioned that do not exist
4. Flag real resources that deviate from the described path

**Output**: Diff list — "described vs real" with real topology as authoritative

### Step 5: User Confirmation

Present the user with:

1. **Real access path** (as resolved from cloud resources)
2. **Diff list** (where the description differed from reality)
3. Ask: "Is this the correct topology to audit? Reply 'yes' to proceed or describe corrections."

**Wait for user confirmation.** Do not proceed to Step 6 without it.

### Step 6: Risk Audit

Load `rules/network-audit-rules.yaml` and evaluate each rule against the topology dataset:

1. For each rule, filter the topology for matching resource types
2. Apply the rule's condition to each matching resource
3. Rules with a trigger condition (e.g., "public port 22 open") flag matching resources
4. Collect all findings with: rule_id, resource_id, resource_name, severity, description,
   remediation
5. Sort findings by severity (critical → high → medium → low → info)
6. Deduplicate overlapping findings

Validate the rule directory before use:

```bash
python3 scripts/validate-rules.py rules/network-audit-rules.yaml
```

**Output**: Risk list (sorted by severity, each item traceable to a rule ID)

### Step 7: Report Rendering

Generate a Markdown audit report containing:

1. **Topology Summary** — The real access path, VPC, and subnets
2. **Security Group Inventory** — Per-resource security group rules
3. **Risk List** — Sorted by severity, each with rule_id/resource/severity/description/remediation
4. **Mermaid Topology Diagram** — Visual representation of the network topology
5. **Metadata** — Audit timestamp, rule directory version, data sources used

Render the Mermaid diagram. If rendering fails, fall back to ASCII art:

```bash
bash scripts/mermaid-to-ascii.sh
```

**Output**: Final Markdown report (saved to a file and presented to the user)

## KooCLI Command Format (Standard)

All KooCLI (`hcloud`) commands in this skill and its references follow one standard form. Every
invocation carries an explicit region with `--cli-region=<region>`; the service name is in
PascalCase and the operation is in PascalCase as well.

```
hcloud <Service> <Operation> --cli-region=<region> [--key=value ...]
```

| Part | Rule | Example |
|------|------|---------|
| `<Service>` | KooCLI service name, PascalCase | `VPC`, `ELB`, `NAT`, `ECS`, `RDS`, `CCE` |
| `<Operation>` | KooCLI operation, PascalCase | `ListVpcs`, `ListLoadBalancers`, `ListClusters` |
| `--cli-region` | **Required**; `--cli-region=<region>`, never omit or leave as an empty value | `--cli-region=cn-north-4` |
| `--key=value` | Optional request parameters, `=` form | `--limit=1` |

- `--region` and `--cli-region` are different flags: `--region` is this skill's Python script
  parameter, while `--cli-region` is the KooCLI parameter.
- Examples in this document use `<region>` or a concrete region such as `cn-north-4`.
- When this skill runs inside the skill pipeline, wrap KooCLI calls as
  `skill-quality-cli run --skill-name huawei-cloud-network-topology-audit -- hcloud ...`.

## Examples

Run every command from the skill root directory. The commands below are exactly the ones used by
the evaluation and are safe to copy.

### Example 1: Validate the rule directory

```bash
python3 scripts/validate-rules.py rules/network-audit-rules.yaml
```

Expected: `PASSED: All rules valid` and exit code `0`. If PyYAML is missing the script prints an
install hint and exits `2`; a missing rule file also exits `2`; invalid YAML or rule errors exit `1`.
No Python traceback is printed.

### Example 2: Connectivity precheck

```bash
bash scripts/precheck.sh
```

Expected: `[precheck] PASS` and exit code `0`. Missing credentials exit `1` with the full list of
supported AK/SK pairs; an unreachable VPC API after credentials were found exits `2`.

### Example 3: Query DCS instances

```bash
python3 scripts/query-dcs-instances.py --region=cn-north-4
```

Expected with credentials: a DCS instance list (or `(none found)`) and exit code `0`.
Without credentials: a readable error listing all supported AK/SK pairs and exit code `2`.
If `huaweicloudsdkdcs` is not installed: a readable install hint and exit code `3`.

### Example 4: KooCLI CCE query

```bash
hcloud CCE ListClusters --cli-region=cn-north-4
```

Expected: cluster list for the region. `--cli-region` is mandatory.

### Example 5: Mermaid ASCII fallback

```bash
echo 'graph TD; A-->B' | bash scripts/mermaid-to-ascii.sh
```

Expected: an ASCII topology fallback (no network access, no rendering service).

## Core Commands

| Command | Purpose | Exit codes |
|---------|---------|-----------|
| `bash scripts/precheck.sh` | Step 1: Connectivity precheck | `0` pass, `1` missing credentials/dependency, `2` API unreachable |
| `python3 scripts/validate-rules.py rules/network-audit-rules.yaml` | Step 6: Validate rule directory | `0` valid, `1` rule/YAML error, `2` missing PyYAML or unreadable file |
| `bash scripts/mermaid-to-ascii.sh` | Step 7: Mermaid ASCII fallback | `0` |
| `python3 scripts/query-dcs-instances.py --region {region}` | Path B: Query DCS instances (SDK) | `0` success, `2` missing credentials, `3` missing SDK, `1` API error |

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| Access path | Yes | Natural language path with resource names | "ELB web-elb → CCE prod-cce → RDS prod-db" |
| `--region` | Yes | Huawei Cloud region | `cn-north-4` |
| `--output` | No | Report output path | `./audit-report.md` |

## Quality Reporting

This Skill bundles [skill_quality_sdk.py](scripts/skill_quality_sdk.py) for optional execution
quality reporting. Reporting is **disabled by default**: nothing is sent anywhere unless the operator
explicitly opts in with `SKILL_QUALITY_ENABLE=1`. When enabled, each run reports trace_id, status
(success/biz_fail/sys_fail/cancel), error code, cost, and masked input/output to the operations
console.

### Security Defaults

- Reporting is opt-in; the default is no network egress and no data collection.
- The report endpoint must be an `https://` URL; calls always verify TLS certificates, and there is
  no switch to skip certificate or hostname validation.
- Inputs and outputs are masked (phone numbers, secrets, tokens) before transmission.

### Integration

- **Python entry point:** wrap main logic with `quality_context` context manager:
  ```python
  from skill_quality_sdk import quality_context, QualityError
  with quality_context(skill_name="huawei-cloud-network-topology-audit", skill_version="1.0.0") as q:
      q.input = {...}
      result = do_something()
      q.output = result
  ```
- **CLI-only workflows:** the SDK is vendored in `scripts/` for future Python wrapper use

### Error Code Convention

| Prefix | Category | Examples |
|--------|----------|---------|
| U | User input | U01 missing resource name, U03 no data found |
| C | Configuration | C01 missing credentials, C02 missing region |
| N | Network | N01 API timeout, N02 connection refused |
| B | Code bug | B01 null pointer, B04 rule parse error |
| P | Platform | P01 report generation failed |

Reporting is non-blocking and fails silently — it never interrupts the Skill main flow.
Enable explicitly with `SKILL_QUALITY_ENABLE=1`; force-disable with `SKILL_QUALITY_DISABLE=1`.

## Reference Documents

- [Resource-Skill Mapping](references/resource-skill-mapping.md) — Resource type → query skill mapping
- [Official Doc Index](references/official-doc-index.md) — Official API/SDK docs for path B resources
- [Severity Definitions](references/severity-definitions.md) — Five-level severity definitions
- [Rule Authoring Guide](references/rule-authoring-guide.md) — How to write/update audit rules
- [IAM Policies](references/iam-policies.md) — Required IAM permissions
- [CLI Installation Guide](references/cli-installation-guide.md) — hcloud CLI installation
- [Data Flow Diagram](references/dataflow-diagram.md) — Mermaid data flow diagram
- [Verification Method](references/verification-method.md) — How to verify the skill
- [Acceptance Criteria](references/acceptance-criteria.md) — Acceptance criteria