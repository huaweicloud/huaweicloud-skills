---
name: huawei-cloud-architecture-resource-archive
description: |
  Huawei Cloud full-resource query and resource marker table generation toolchain. Driven by KooCLI (hcloud), covering 40+ cloud services and 80+ resource types (compute/storage/network/database/security/CDN etc.), with full-region auto-discovery concurrent query, format conversion, and one-click marker table generation.
  Scenarios: cloud resource inventory, resource architecture topology data collection, resource marker table generation, cross-account resource reconciliation.
  Trigger words: 资源查询, 全量查询, 资源盘点, resource query, resource archive, 资源标记表, marker table, KooCLI, hcloud, 资源归档
tags: [huawei-cloud, koocli, resource-query, cre, finops]
metadata: {"resource-archive": {"version": "1.0.0", "requires": {"bins": ["hcloud>=7.2.2", "python3>=3.8"], "python_deps": [{"name": "openpyxl", "pip": "openpyxl", "blocking": true}, {"name": "kubernetes", "pip": "kubernetes", "blocking": false}, {"name": "huaweicloudsdkcore", "pip": "huaweicloudsdkcore", "blocking": false}, {"name": "requests", "pip": "requests", "blocking": false}, {"name": "urllib3", "pip": "urllib3", "blocking": false}, {"name": "yaml", "pip": "pyyaml", "blocking": false}]}, "install": [{"kind": "pip", "command": "pip install openpyxl kubernetes huaweicloudsdkcore requests urllib3 pyyaml"}, {"kind": "koocli", "command": "scripts/check_koocli.py"}]}}
---

# Huawei Cloud Full Resource Query & Marker Table Generation

## 1. Overview

This skill is a Huawei Cloud full-resource query toolchain. Driven by KooCLI (`hcloud`), it automatically queries resources across all regions and all key services of a Huawei Cloud account, then generates the marker table required for resource architecture topology.

### Architecture

```
run_pipeline.py (one-click entry)
    ├── Step 1: check_koocli.py        → Environment check / install KooCLI + dependencies
    ├── Step 2: query_resources.py     → Full-region × 40+ services concurrent query
    ├── Step 3: convert_to_tsc_json.py → Convert to marker-table compatible JSON
    └── Step 4: generate_marker_table.py → Generate marker table Excel + store JSON
```

Involved cloud services: ECS, VPC, EIP, ELB, NAT, DNS, OBS, RDS, DCS, DDS, CCE, WAF, CDN, BMS, CCI, SFS, CSS, MRS, DLI, CloudTable, BGP and 40+ service modules in total. The full registered module list is in `references/service-coverage.md`.

### Use Cases

- Full cloud resource inventory and archival
- Resource architecture topology data collection
- Automatic resource marker table generation
- Cross-account resource reconciliation and gap analysis
- Pre-migration resource inventory

### Typical User Requests

- "Query all resources under my Huawei Cloud account"
- "Generate the resource marker table"
- "Inventory ECS, VPC, RDS resources across all regions"
- "Export the resource list to Excel"

## 2. Prerequisites

### KooCLI Version

```bash
# Verify KooCLI installation
hcloud version
# Requires version >= 7.2.2
```

If not installed, see [CLI Installation Guide](references/cli-installation-guide.md).

### Python Version

```bash
python3 --version
# Requires Python >= 3.8
```

### Python Dependencies

All third-party Python dependencies are checked and auto-installed in Step 1 (`check_koocli.py`):

| Package | pip name | Used by | Blocking? |
|---------|----------|---------|:---------:|
| `kubernetes` | `kubernetes` | CCE K8s sub-resource direct connection (`query_cce_k8s.py`) | No |
| `huaweicloudsdkcore` | `huaweicloudsdkcore` | CCE proxy fallback for K8s sub-resources (`query_cce_k8s.py`) | No |
| `openpyxl` | `openpyxl` | Marker table Excel generation (`generate_marker_table.py`, Step 4) | Yes |
| `requests` | `requests` | CCE proxy HTTP calls (`query_cce_k8s.py`) | No |
| `urllib3` | `urllib3` | SSL warning suppression in K8s query (`query_cce_k8s.py`) | No |
| `yaml` | `pyyaml` | Kubeconfig YAML parsing (`query_cce_k8s.py`) | No |

The dependency list is declared in `PYTHON_DEPS` inside `check_koocli.py`; the checker also
scans all scripts via AST to detect any undeclared third-party imports.

### Authentication

Recommended: configure AK/SK via environment variables.

```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
```

Or via KooCLI config file:

```bash
hcloud configure set --cli-access-key=<AK> --cli-secret-key=<SK>
hcloud configure set --cli-region=cn-north-4
```

> ⚠️ Never hardcode AK/SK values in conversations or scripts.

### IAM Permissions

This skill only requires **read-only** permissions. See [IAM Policies](references/iam-policies.md) for the full list.

**Permission failure handling flow:**

1. When a command fails due to permission errors, read `references/iam-policies.md`
2. Show the user the required permission list and policy JSON
3. Guide the user to create a custom policy and grant it in the IAM console
4. Pause execution and wait for the user to confirm the permission has been granted

## 3. KooCLI Command Format Standard

```bash
# Standard format
hcloud <SERVICE> <Operation> --param1=value1 --cli-region=<region>

# Example: list ECS instances
hcloud ECS ListServersDetails --cli-region=cn-north-4

# Example: list VPC security groups (v3 operation)
hcloud VPC ListSecurityGroups/v3 --cli-region=cn-north-4

# Example: list IAM users (Keystone prefix)
hcloud IAM KeystoneListUsers --cli-region=cn-north-4
```

Special rules: some VPC/ELB operations require a `/v3` suffix; IAM operations require the Keystone prefix; EIP is an independent service. See [KooCLI Command Reference](references/related-commands.md).

## 4. Workflow

`run_pipeline.py` automatically executes the following 4 steps in order, aborting on any failure:

| Step | Script | Description |
|:----:|--------|-------------|
| 1 | `check_koocli.py` | Check/install KooCLI + AK/SK config + kubernetes client |
| 2 | `query_resources.py` | Full-region (auto discovery) × 40+ services concurrent query, outputs raw JSON |
| 3 | `convert_to_tsc_json.py` | Convert to marker-table compatible JSON |
| 4 | `generate_marker_table.py` | Generate `关键资源标记表.xlsx` + `_resource_store.json` |

```bash
# One-click full pipeline (recommended)
python scripts/run_pipeline.py --account <account-name>

# Specify regions
python scripts/run_pipeline.py --account <account-name> --regions cn-north-4,cn-east-3

# Query only some services
python scripts/run_pipeline.py --account <account-name> --services cce,vpc,ecs

# Reuse existing conversion results, re-run marker table only
python scripts/run_pipeline.py --account <account-name> --skip-check --skip-query
```

## 5. Core Commands

Each command supports two modes: **Interactive** (prompts for required params step by step) and **Non-Interactive** (all params passed via CLI flags, suitable for automation).

### Environment Check

```bash
# Interactive (recommended for first use)
python scripts/check_koocli.py

# Non-interactive (skip if KooCLI already installed)
python scripts/check_koocli.py --install-dir ./koocli
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--install-dir` | No | `./koocli` | Directory to install/locate hcloud binary |

**Status codes**: exit 0 = all checks passed; exit 1 = blocking dependency missing (openpyxl or hcloud not found).

### Full Query

```bash
# Interactive mode (auto-discovers all regions, queries all 43 services)
python scripts/query_resources.py --account <account-name>

# Non-interactive mode with explicit scope
python scripts/query_resources.py --account <account-name> --regions cn-north-4,cn-east-3 --services ecs,vpc,rds

# Reuse only (skip environment check)
python scripts/run_pipeline.py --account <account-name> --skip-check --skip-query
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--account` | Yes | — | Account name, used for output directory naming |
| `--regions` | No | auto discovery | Comma-separated region list; `auto` = IAM KeystoneListProjects + RMS probe |
| `--services` | No | all 43 services | Comma-separated service names (e.g. `ecs,vpc,cce`) |
| `--workers` | No | 8 | Service-level concurrency (region-level defaults to 5) |

**KooCLI return codes & meanings**:

| Return | Meaning | Handling |
|--------|---------|----------|
| HTTP 200 + valid JSON | Success, resources saved to `temp/` | Proceed to conversion |
| `USE_ERROR` | Wrong service/operation name or param | Verify name via `hcloud <SERVICE> --help`; check `references/related-commands.md` |
| `OPENAPI_ERROR` 403 | IAM permission denied | Read `references/iam-policies.md`, show required policy, pause execution |
| `OPENAPI_ERROR` 404 | Service not available in this region | Log and continue (region skipped, other regions unaffected) |
| Empty list (`[]` or `{"items":[]}`) | No resources of this type in this region | Normal, count = 0, no error |
| Timeout (>180s) | Network/proxy issue | Check `HTTPS_PROXY` env var; reduce `--workers` |

### Format Conversion

```bash
# Non-interactive (typical use after query)
python scripts/convert_to_tsc_json.py \
  --query-dir resource-output/<account-name>-<timestamp>/raw \
  --customer <account-name> \
  --output resource-output/<account-name>-<timestamp>/converted
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--query-dir` | Yes | — | Raw query JSON directory (from Step 2) |
| `--customer` | Yes | — | Customer/account name (written to `customer_name` column) |
| `--output` | Yes | — | Output directory for converted JSON |

**Status codes**: exit 0 = conversion done, logs show per-service row count; exit 1 = `no KooCLI query results found` (raw dir missing or empty).

### Marker Table Generation

```bash
# Non-interactive
python scripts/generate_marker_table.py \
  --tsc-dir resource-output/<account-name>-<timestamp>/converted \
  --out resource-output/<account-name>-<timestamp>/marker \
  --customer <account-name>
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--tsc-dir` | Yes | — | Converted TSC JSON directory (from Step 3) |
| `--out` | Yes | — | Marker table output directory |
| `--customer` | Yes | — | Customer/account name |

**Status codes**: exit 0 = `关键资源标记表.xlsx` + `_resource_store.json` generated; exit 1 = `no resource rows found` (conversion output empty, backtrack to Step 3).

### Common Issues Quick Solutions

| Issue | Solution |
|-------|----------|
| 0 rows for smoke services (VPC/ECS/Subnet) | Query link failure — verify service/operation name, credentials, proxy |
| Service JSON contains `USE_ERROR` text | Wrong service/operation name — check `references/related-commands.md` |
| `OPENAPI_ERROR` 403 | IAM permission denied — read `references/iam-policies.md`, grant read-only policy |
| Query hangs >30s on first service | Network/proxy issue — set `HTTPS_PROXY` env var (see experience: corporate-intranet-proxy-adaptation) |
| Conversion rows = 0 but query has data | Converter field mapping error (e.g. id/name key mismatch) — check `convert_to_tsc_json.py` CONVERTERS for that service |
| Marker table missing a service type | Service queried but no converter registered — check `CONVERTERS` dict in `convert_to_tsc_json.py` |
| CCE K8s sub-resources missing | Cluster has no public K8s API endpoint — fallback to CCE proxy mode (needs `huaweicloudsdkcore`) |
| Duplicate `resource_id` in marker table | Converter dedup logic issue — check `_find_list` / `seen` set in converter |
| Dormant CCE cluster | Wake cluster in CCE console first, then re-run query |

## 6. Parameter Reference

| Parameter | Script | Default | Description |
|-----------|--------|---------|-------------|
| `--account` | run_pipeline, query_resources | (required) | Account name, used for output directory naming |
| `--regions` | run_pipeline, query_resources | auto discovery | Comma-separated region list; if omitted, auto-discover all regions |
| `--services` | run_pipeline, query_resources | all registered services | Comma-separated service name list |
| `--skip-check` | run_pipeline | false | Skip Step 1 environment check |
| `--skip-query` | run_pipeline | false | Skip Step 2 query (reuse existing results) |
| `--query-dir` | convert_to_tsc_json | (required) | Raw query JSON directory |
| `--tsc-dir` | generate_marker_table | (required) | Converted TSC JSON directory |
| `--out` | generate_marker_table | (required) | Marker table output directory |
| `--customer` | convert, generate | (required) | Customer/account name |

## 7. Output Format

```
resource-output/
└── <account>-<timestamp>/
    ├── converted/              # Step 3 output: converted JSON
    └── marker/                 # Step 4 output: marker table + store
        ├── 关键资源标记表.xlsx
        └── _resource_store.json
```

> Raw query JSON from Step 2 is automatically deleted after Step 3 conversion completes.

The marker table Excel contains 15 columns, one row per resource instance.

## 8. Verification Method

Verification is divided into three levels (installation, configuration, functional) and covers every pipeline step (query → convert → marker table). Each step defines explicit success/failure criteria. See [Verification Method](references/verification-method.md) for the full step-by-step pass/fail criteria.

```bash
# Level 1: installation verification
hcloud version            # should return >= 7.2.2
python3 -c "import openpyxl; print(openpyxl.__version__)"

# Level 2: configuration verification
hcloud configure list     # should show valid AK/SK and region

# Level 3: functional verification (single service)
hcloud ECS ListServersDetails --cli-region=cn-north-4   # should return instance list

# End-to-end: full pipeline (all steps must pass)
python scripts/run_pipeline.py --account <account> --services ecs --regions cn-north-4
# Success: 关键资源标记表.xlsx + _resource_store.json generated, rows match console resources
```

✅ Success: every step's success criteria met (see the reference doc per step).

❌ Failure: a step failed; follow the failure handling for that step (e.g. 0 rows → verify KooCLI service/operation name; permission error → check `references/iam-policies.md`).

## 9. Best Practices

- **Use run_pipeline.py instead of step-by-step execution**: Step 1 automatically installs kubernetes and other dependencies; running steps separately can easily miss prerequisites
- **Validate on a small scope first**: on first use, try `--services ecs,vpc --regions cn-north-4` to verify the flow
- **Reuse query results**: the query takes a long time; conversion and marker table can be tuned repeatedly with `--skip-check --skip-query`
- **CCE K8s sub-resources**: requires a cluster with a public K8s API endpoint; otherwise it falls back to CCE proxy mode (requires huaweicloudsdkcore)

## 10. Reference Documents

- [CLI Installation Guide](references/cli-installation-guide.md)
- [IAM Policies](references/iam-policies.md)
- [Verification Method](references/verification-method.md)
- [Acceptance Criteria](references/acceptance-criteria.md)
- [KooCLI Command Reference](references/related-commands.md)
- [Service Coverage](references/service-coverage.md)
- [Semantic Catalog](references/semantic/catalog.yml) — 薄路由层，account/region_scope/services → resource-ontology 实体
- [Resource Ontology](references/semantic/resource-ontology.yml) — 语义本体，定义资源事实、粒度、KooCLI 只读 source_operations 与 evidence_boundary

## 11. Notes

### Security

- **Read-only only**: this skill only executes List/Show read-only APIs and never modifies any cloud resource
- **Credential safety**: AK/SK are never shown in output reports. `check_koocli.py` first checks whether hcloud can already authenticate; if yes, skips `configure set` entirely (no disk write). If hcloud is not yet configured, `configure set` writes encrypted credentials to `~/.hcloud/config.json` (hcloud CLI requires this; there is no env-var-only path). Subsequent runs skip `configure set` and do not write to disk.
- **Least privilege**: only read-only permissions are required; see [IAM Policies](references/iam-policies.md)

### Compatibility

- **KooCLI version**: requires >= 7.2.2; lower versions have different parameter formats for some operations
- **Python version**: requires >= 3.8 (uses `from __future__ import annotations`)
- **CCE K8s sub-resources**: requires the kubernetes Python client (v37+), auto-installed in Step 1
- **CCE proxy fallback**: without a public K8s API endpoint, falls back to CCE proxy mode, requiring additional huaweicloudsdkcore + huaweicloudsdkcce

### Known Limitations

- **Dormant CCE clusters**: K8s sub-resources of dormant CCE clusters cannot be queried; wake the cluster in the CCE console first
- **CCE K8s public endpoint**: when the cluster has no public access, K8s sub-resources (Deployment/Service/ConfigMap and 15 other types) cannot be queried
- **Region auto-discovery**: uses RMS/ListRegionsInDDM to auto-discover all 25 regions; regions without permission may be included (they error out but do not affect other regions)
- **Global service regions**: CDN only supports cn-north-1 / ap-southeast-1; GEIP/CCAAS/EPS/CC2 are global services, queried once per account
- **OBS bucket list**: KooCLI has no `OBS ListBuckets` operation; buckets are queried indirectly via RMS `ListAllResources --type=obs.buckets`
- **Concurrent query**: defaults to 10 workers, adjustable via `MAX_WORKERS` in common.py; region-level concurrency defaults to 5
- **Output directory**: query results default to `resource-output/` under the skill root; customize with `--output-dir`

## 12. Hard Constraints (Non-Negotiable)

The following three are derived from resource inventory principles, non-negotiable.

### Read-Only

No write operations that change resources, identity status, or cluster state; refuse create, delete, update, scale, restart, bind, unbind, wake dormant clusters.
**Why**: 一旦发生写操作，资源盘点快照所依赖的事实状态被自身污染。`List*`/`Show*`/`ListAllResources` 均为只读查询；`CreateKubernetesClusterCert` 虽含 Create，但其返回值仅为 kubeconfig 证书（只读用途），不改变集群状态，归入此类。

### No Leak

No output of credentials, AK/SK, security tokens, long identifiers that can restore identity, complete `project_id`/`cluster_id` with binding context.
**Why**: 身份维度泄露超出 `evidence_boundary` 响应范围；交付价值与泄露程度无关。AK/SK 仅从环境变量读取，不落盘、不出现在输出报告中。

### No Extrapolation

Partial region results, RMS summary rows, sampled service subsets, and zero-count responses cannot be stated as whole-account, all-services, final inventory, or "resource does not exist."
**Why**: 粒度不允许放大。RMS `CollectAllResourcesSummary` 为汇总行（provider×type×count），不可当实例级事实；部分 region 查询结果不可外推为全账号全量；`--services ecs` 子集查询不可声明"全量盘点完成"。

## 13. Boundaries

- **Service Scope** — Only Huawei Cloud read-only resource inventory via KooCLI (ECS/VPC/CCE/OBS/RDS/CDN/DCAAS and 43 service modules / 83 resource types). Non-Huawei Cloud or other cloud vendor resources not in scope. Billing/cost/charge attribution belongs to `huawei-cloud-billing-scout`, not this skill.
- **Refuse Routing** — Resource creation/modification/deletion, cluster wake/scale, IAM policy grant, KooCLI installation execution, price/cost estimation — all not in this skill scope; only one sentence pointing to console or corresponding skill, no evidence gathering, no write API calls.
- **Official Identity** — Does not represent Huawei Cloud; conclusions only based on evidence found at that time (query snapshot point-in-time, not real-time consistency).
- **Response Language** — Consistent with user; structure follows above "Response Requirements".
- **Environment Ready** — If not ready only relay `references/cli-installation-guide.md`; can self-check via `hcloud version` / `hcloud configure list`. `check_koocli.py` may call `hcloud configure set` to configure AK/SK when hcloud is not yet authenticated (writes encrypted credentials to `~/.hcloud/config.json`); if hcloud is already authenticated, it skips `configure set` (no disk write).

## 14. Response Requirements

> Briefing-style delivery: conclusion first, facts later; only write what was found, state grain clearly.

- **Like a Brief** — Summary one to three sentences, state account / region_scope / services coverage, answer resource count, type coverage, what's still missing (e.g. dormant CCE clusters, regions without permission). With evidence then quantitative, without evidence then mark uncertain. **Fact points use `·` list or short paragraphs, no raw JSON dump (IM-friendly)**.
- **Only Trust Evidence** — Points only list content that was found, use resource type names (consistent with KooCLI service names, no API internal names); speculation and pending checks only in summary; no count written for unqueried services. RMS summary count ≠ instance count; always state grain.
- **Delivery Baseline** — No sending: raw API responses, command text, complete `project_id`/`cluster_id` with binding context, AK/SK, `profile` / `region` config. Gaps only provide one read-only next step (business wording), not "please reconcile yourself".
