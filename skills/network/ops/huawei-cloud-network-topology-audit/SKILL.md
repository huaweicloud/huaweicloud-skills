---
name: huawei-cloud-network-topology-audit
description: >-
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

1. **Huawei Cloud credentials** — Environment variables (`HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` or
   `HW_AK` / `HW_SK` / `HWC_ACCESS_KEY` / `HWC_SECRET_KEY`) or hcloud CLI config
2. **Python 3.8+** — Required for scripts in `scripts/`
3. **huaweicloudsdk packages** — For path B resources (DCS): `pip install huaweicloudsdkdcs`
4. **Network access** — To GitCode for find-skills index queries
5. **hcloud CLI** (optional) — For CCE cluster queries via CCE management skill

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SKILL_QUALITY_ENDPOINT` | No | Report endpoint, default https://skillsapi.developer.myhuaweicloud.com/api/quality/report |
| `SKILL_QUALITY_NAME` | No | Skill name (auto-detected) |
| `SKILL_QUALITY_DISABLE` | No | Set `1` to disable reporting (local dev) |
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
3. Call `huawei-cloud-find-skills` (via its search script) to confirm the query skill exists
   in the current index
4. Build a structured collection plan:
   - Path A resources → dispatch to query skill
   - Path B resources → use self-written script

**Output**: Structured path draft + collection path mapping

### Step 3: Real Topology Discovery

Execute the collection plan:

#### Path A (existing query skills)

| Resource | Query Skill | Key Queries |
|----------|-------------|-------------|
| VPC | `huawei-cloud-network-query` | ListVpcs, ShowVpc |
| Subnet | `huawei-cloud-network-query` | ListSubnets |
| Security Group | `huawei-cloud-network-query` | ListSecurityGroups, ShowSecurityGroup |
| Route Table | `huawei-cloud-network-query` | ListRouteTables |
| EIP | `huawei-cloud-network-query` | ListPublicips |
| ELB | `huawei-cloud-network-query` | ListLoadBalancers, ListListeners, ListPools |
| NAT | `huawei-cloud-network-query` | ListNatGateways, ListSnatRules, ListDnatRules |
| ECS | `huawei-cloud-computing-query` | ListServersDetails |
| RDS | `huawei-cloud-rds-smart-service` | ListInstances |
| CCE | `huawei-cloud-cce-cluster-management` | ListClusters, ListNodes |

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

## Core Commands

| Command | Purpose |
|---------|---------|
| `bash scripts/precheck.sh` | Step 1: Connectivity precheck |
| `python3 scripts/validate-rules.py rules/network-audit-rules.yaml` | Step 6: Validate rule directory |
| `bash scripts/mermaid-to-ascii.sh` | Step 7: Mermaid ASCII fallback |
| `python3 scripts/query-dcs-instances.py --region {region}` | Path B: Query DCS instances (SDK) |

## Parameter Confirmation

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| Access path | Yes | Natural language path with resource names | "ELB web-elb → CCE prod-cce → RDS prod-db" |
| `--region` | Yes | Huawei Cloud region | `cn-north-4` |
| `--output` | No | Report output path | `./audit-report.md` |

## Quality Reporting

This Skill integrates [skill_quality_sdk.py](scripts/skill_quality_sdk.py) for execution quality
reporting. Every run automatically reports trace_id, status (success/biz_fail/sys_fail/cancel),
error code, cost, and masked input/output to the operations console.

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
Disable via `SKILL_QUALITY_DISABLE=1` for local testing.

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