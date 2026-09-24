---
name: huawei-cloud-iac-reverse
description: |
  Reverse-engineer existing Huawei Cloud resources into deployable Terraform IaC code.
  Queries all resources via RMS (Config/配置审计) API, analyzes specs and topology
  service-by-service, then synthesizes Terraform HCL configurations with provider
  validation. Use when the user wants to generate IaC from existing cloud resources,
  migrate infrastructure to code, or reverse-engineer cloud topology.
  Triggers include: "逆向生成IaC", "反向生成Terraform", "从现有资源生成代码", "reverse engineer IaC", "generate Terraform from existing resources", "infrastructure to code", "cloud to IaC".
triggers:
  - "逆向生成IaC"
  - "反向生成Terraform"
  - "从现有资源生成代码"
  - "reverse engineer IaC"
  - "generate Terraform from existing resources"
  - "infrastructure to code"
  - "cloud to IaC"
tags: [huawei-cloud terraform iac reverse-engineering rms config]
---

# Huawei Cloud IaC Reverse Engineering Skill

## Overview

Given a Huawei Cloud account with existing resources, this skill:
1. **Discovers** all resources via RMS (Resource Management Service / 配置审计) API
2. **Analyzes** resources in batches by service layer (network → storage → compute → database → auxiliary)
3. **Synthesizes** Terraform HCL configurations from the analyzed topology
4. **Validates** with `terraform fmt` → `validate` → `plan`
5. **Compares** the generated code against the original inventory to identify gaps

## Prerequisites

- `hcloud` CLI (KooCLI) installed and configured with AK/SK
- Terraform >= 1.90.0 installed (see `references/cli-installation-guide.md`)
- Huawei Cloud provider for Terraform (auto-downloaded via Huawei Cloud mirror)
- Environment variables: `HUAWEI_ACCESS_KEY`, `HUAWEI_SECRET_KEY` (unset `HUAWEI_SECURITY_TOKEN` if switching accounts)

## Workflow

### Phase 0: Credential Setup

```bash
# Set credentials (never write AK/SK into .tf files)
export HUAWEI_ACCESS_KEY="your-ak"
export HUAWEI_SECRET_KEY="your-sk"
# CRITICAL: unset stale security token when switching accounts
unset HUAWEI_SECURITY_TOKEN
```

### Phase 1: Resource Discovery (RMS)

Use RMS `ListAllResources` to get ALL resources across ALL services in one call:

```bash
# List all resources in a region
hcloud Config ListAllResources --cli-region={region} --limit=200
```

**Known limitations:**
- Subnets are NOT returned by RMS — query VPC API separately
- CCE Turbo cluster nodes may not be returned by CCE API — extract from RMS data
- Some resource properties (e.g., EVS volume_type) may be missing — supplement with service-specific APIs

### Phase 2: Batch Analysis (9 phases by dependency layer)

Analyze resources in dependency order:

| Phase | Layer | Resources | Key Data to Extract |
|-------|-------|-----------|-------------------|
| 1 | Network | VPC, subnets, SGs, EIPs | CIDR, AZ, rules, bandwidth |
| 2 | Storage | OBS, EVS, SFS Turbo | bucket names, share_type, size |
| 3 | Compute | ECS instances | flavor, image_id, AZ, disk, EIP, SG |
| 4 | CCE | Clusters, nodes | cluster version, network type, node flavor |
| 5 | Database | GaussDB | engine, version, flavor, HA mode, volume |
| 6-7 | Cache/MQ | DCS, DMS | spec_code, broker_num, storage |
| 8 | Auxiliary | KMS, keypairs, HSS, LTS | key alias, topic names |
| 9 | Topology | Cross-references | VPC→subnet→ECS, SG→rules, CCE→nodes |

### Phase 3: Terraform Code Generation

Generate `.tf` files in dependency order:

```
project/
├── providers.tf      # provider config (version, region, no AK/SK)
├── variables.tf      # variables (image IDs, keypair name, passwords)
├── terraform.tfvars  # region assignment
├── .tfrc             # Huawei Cloud provider mirror
├── main.tf           # Layer 0-1: VPC, subnets, SG, EIP
├── storage.tf        # Layer 2: OBS, SFS Turbo
├── compute.tf        # Layer 3a: ECS
├── cce.tf            # Layer 3b-4: CCE cluster + node pool
├── database.tf       # Layer 3c: GaussDB, DCS, DMS
├── security.tf       # Layer 0 aux: KMS
├── lts.tf            # LTS log groups
└── README.md         # documentation
```

**Key rules:**
- Never write AK/SK into `.tf` files — use env vars or provider profile
- Reference existing resources (keypairs, KMS keys) via variables, don't recreate
- Resources auto-created by parent services (CCE nodes, GaussDB nodes, DCS nodes) are NOT in Terraform
- Use `charging_mode = "prePaid"` / `"postPaid"` (string, not numeric)
- CCE node pool volumes use `volumetype` (not `volume_type`)
- GaussDB `datastore.version` uses MySQL-compatible version (e.g., "8.0"), not internal version

### Phase 4: Validation

```bash
terraform fmt -recursive
terraform validate
terraform plan
```

Fix provider schema mismatches iteratively. Common issues:
- `billing_mode` (deprecated) → `charging_mode`
- `volume_type` → `volumetype` (CCE node pool)
- `spec_code` → `flavor` (DCS)
- `subnet_id` → `network_id` (DMS)
- `available_zones` (deprecated) → `availability_zones`
- `scale_enable` → `scall_enable` (CCE node pool, provider typo)
- `eni_subnet_ids` → `eni_subnet_id` (CCE cluster)

### Phase 5: Gap Analysis

Compare generated resources against original inventory:

| Category | Check |
|----------|-------|
| Fully covered | Each original resource has a TF equivalent |
| Correctly excluded | Auto-created sub-resources (CCE nodes, DB nodes) not in TF |
| Gaps | Missing resources, incomplete properties, provider limitations |

Common gaps to check:
- GaussDB: provider may not support `security_group_id`, `port`, `dataVolumeSizeInGBs`
- SFS Turbo: `share_type` mapping (e.g., `HPC_STANDARD_20M` → `HPC` + `hpc_bandwidth`)
- CCE: initial node count vs node pool count
- OBS: custom ACLs / cross-account grants
- LTS: log topics
- KMS: encryption keys

## Core Commands

| Command | Purpose |
|---------|---------|
| `hcloud Config ListAllResources --cli-region={region} --limit=200` | Discover all resources via RMS |
| `hcloud GaussDB ShowGaussMySqlEngineVersion --database_name=gaussdb-mysql --cli-region={region}` | Query GaussDB engine versions |
| `hcloud SFSTurbo ListShares --cli-region={region}` | Query SFS Turbo shares |
| `hcloud CCE ListClusters --cli-region={region}` | Query CCE clusters |
| `bash scripts/query_all_resources.sh {region}` | Query all resources in a region |
| `bash scripts/validate_terraform.sh {project_dir}` | Validate Terraform configuration |
| `bash scripts/compare_resources.sh {plan_file} {rms_json_file}` | Compare plan vs inventory |

## Parameter Confirmation

### hcloud Config ListAllResources

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region, agent fills automatically |
| `--limit` | No | Number of records to return, default 200 |

### hcloud GaussDB ShowGaussMySqlEngineVersion

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--database_name` | Yes | Database name, e.g. `gaussdb-mysql` |
| `--cli-region` | Yes (auto) | Region, agent fills automatically |

### hcloud SFSTurbo ListShares

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region, agent fills automatically |

### hcloud CCE ListClusters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region, agent fills automatically |

### Helper Scripts

| Script | Required Args |
|--------|---------------|
| `scripts/query_all_resources.sh` | `{region}` (positional) |
| `scripts/validate_terraform.sh` | `{project_dir}` (positional, default `.`) |
| `scripts/compare_resources.sh` | `{plan_file}` `{rms_json_file}` (positional) |

## KooCLI Command Format Standard

Format template: `hcloud <service> <Operation> --cli-region={region} [--key={value} ...]` (template only — replace the placeholders with real values; not an executable command)

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | hcloud service as detected in metadata | `Config`, `GaussDB`, `SFSTurbo`, `CCE` |
| Operation name | PascalCase | `ListAllResources`, `ListShares`, `ListClusters` |
| Region parameter | `--cli-region={region}` | `--cli-region=cn-north-4` |
| Simple parameter | `--key={value}` | `--database_name=gaussdb-mysql` |

## Provider Schema Discovery

When unsure about argument names, query the provider schema:

```bash
terraform providers schema -json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for name, schema in data.get('provider_schemas', {}).items():
    resources = schema.get('resource_schemas', {})
    for rname in ['TARGET_RESOURCE']:
        if rname in resources:
            attrs = resources[rname].get('block', {}).get('attributes', {})
            for an, av in attrs.items():
                req = av.get('required', False)
                print(f'  [{"REQ" if req else "opt"}] {an}')
"
```

## Huawei Cloud API Lookup (for supplementing missing data)

When RMS doesn't return enough detail, use `hcloud` CLI:

```bash
# Query GaussDB engine versions
hcloud GaussDB ShowGaussMySqlEngineVersion --database_name=gaussdb-mysql --cli-region={region}

# Query SFS Turbo shares
hcloud SFSTurbo ListShares --cli-region={region}

# Query CCE clusters
hcloud CCE ListClusters --cli-region={region}
```

## Important Notes

1. **Never `terraform apply` without user confirmation** — this skill only generates and validates code.
2. **Sensitive variables** (passwords, tokens) use `sensitive = true` and default values marked as placeholders.
3. **Provider limitations** are documented as comments in the `.tf` files when a property cannot be set via Terraform.
4. **State management**: Local state is fine for this use case. Remote backend is not forced.
5. **Resource count**: The generated code manages "top-level" resources. Sub-resources (CCE nodes, DB nodes, EVS volumes) are auto-created by their parent resources and correctly excluded from Terraform.

## Example Output

For a 144-resource environment, the skill generates ~57 Terraform resources:
- 27 network (VPC, subnets, SG + rules, EIPs)
- 10 storage (OBS buckets, ACLs, SFS Turbo)
- 3 compute (ECS)
- 2 CCE (cluster + node pool)
- 6 database (GaussDB, DCS, DMS)
- 1 KMS key
- 7 LTS log groups
- 1 keypair reference (variable)

## Reference Documents

- `references/iam-policies.md` — Least-privilege IAM policies
- `references/cli-installation-guide.md` — KooCLI installation and credential configuration
- `references/verification-method.md` — Verification method details
- `references/acceptance-criteria.md` — Acceptance criteria
- `references/dataflow-diagram.md` — Data flow diagram