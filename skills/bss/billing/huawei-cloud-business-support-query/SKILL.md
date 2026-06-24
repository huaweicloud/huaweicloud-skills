---
name: huawei-cloud-business-support-query
description: "Queries Huawei Cloud billing and pricing. Covers balances, bills, coupons, cash coupons, stored-value cards, orders, refunds, costs, free resources, resource usage, enterprise accounts, and on-demand/period/ELB/NAT/DCS pricing. No write operations. Use this skill when the user needs to check fees, view bills, estimate prices, review coupon balances, query orders, or get consumption stats. Triggers: 华为云计费, 账单, 余额, 优惠券, 代金券, 储值卡, 订单, 退款, 成本, 资源用量, 询价, 定价, 费用查看, 账单明细, 价格估算, 消费统计, billing, pricing, cost."
---
# Huawei Cloud Resource Query

> **⚠️ Execution Method (Must Read): This skill executes queries via local Python scripts. Do NOT use hcloud, openstack or other CLI tools, or call APIs directly.**
>
> - Query scripts are located under the skill directory `scripts/<service_category>/` (e.g., `scripts/as/list_scaling_groups.py`)
> - All scripts and environment check scripts are inside the skill package, **must be executed using `skill action=exec`, do not run directly in shell**
> - For specific script paths and parameters, see `references/<service>/guide.md`
> - **Do NOT attempt hcloud, openstack, curl IAM or other CLI/API methods; this skill does not depend on those tools**
> - **All paths are relative to the skill directory, which is the directory where this SKILL.md is located**

## Overview

This skill is a standalone read-only query skill that uses local Python scripts to call the
Huawei Cloud Python SDK for querying Huawei Cloud resources, available specifications,
and existing resource information.

This skill is applicable to the following scenarios:

1. Query available cloud resource specifications in a given region
2. Query available images for a certain OS type
3. Query disk types and existing disk information
4. Query existing resources and their key attributes
5. Query resources that were not created via Terraform or other IaC tools
6. Prepare real parameters for automation configuration, resource verification, or environment inventory
7. Obtain reusable information such as resource ID, name, specification, image, network, disk, etc.

This skill does NOT handle the following:

1. Creating resources
2. Modifying resources
3. Deleting resources
4. Guessing or fabricating information that was not queried

---

## Capability Scope

This skill provides query capabilities through categorized scripts in the scripts directory, and usage instructions through categorized guides in the references directory.
Capabilities provided by this skill include:

1. Query resource lists
2. Query individual resource details
3. Query available specifications, images, disk types, and other selection information
4. Query key identifiers and dependency relationships of existing resources

---

## Usage Principles

Important: Script paths executed within this skill are all relative to the skill directory, which is the directory where this SKILL.md is located

1. This skill only performs queries, no write operations
2. Prefer using explicitly specified region, project, AZ, resource name, resource ID, etc. from the user
3. Query results must be based on actual API responses; do not guess based on experience
4. Returned results should prioritize key fields for subsequent reuse
5. When result sets are large, narrow the scope by region, name, id, status, tag, etc.
6. If there is no corresponding script or guide for the current resource type, clearly state it is unsupported; do not return unreliable results
7. If the user does not provide necessary scope information and there are no default values in the environment, confirm before executing the query
8. Execute directly according to guide.md; do not read script contents in the scripts directory
9. Cache output when it is large
10. Must execute -h to view usage before each script execution
11. Do not invent script names; execute according to script names in guide.md. If a script name is not in guide.md, it means it is not supported
12. **For time-sensitive queries (bills, costs), use script defaults or verify current date first; do not hardcode time parameters based on assumption**

---

## Prerequisites

**Before use, you must run the environment check script to complete environment validation and dependency installation in one step:**

- Linux / macOS: `skill action=exec: bash skill://scripts/check_env.sh`
- Windows: `skill action=exec: powershell -ExecutionPolicy Bypass -File skill://scripts/check_env.ps1`

> Windows note: Do not use `&&` to chain commands (PowerShell 5.x does not support it); use semicolons if you need to change directory first

The script will check in order: Python >= 3.6 → install dependencies → validate SDK →
validate credentials → validate service availability. If the environment check fails,
fix the issue before continuing with other scripts.

**Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| HW_ACCESS_KEY | Yes | Huawei Cloud AK |
| HW_SECRET_KEY | Yes | Huawei Cloud SK |
| HW_REGION_NAME | No | Default cn-north-4 |
| HW_PROJECT_ID | No | Project ID (auto-fetched via IAM API if not set) |
| HW_SECURITY_TOKEN | No | Required for temporary AK/SK |

**Do NOT output the values of the above environment variables.** For additional parameters (availability zone, enterprise project, etc.) needed by other resource scripts, see the corresponding guide.md.

---

## Execution Flow

**When this skill is invoked, the following steps must be executed without waiting for user prompts:**

### Step 1: Environment Preparation

Run the environment check script to ensure dependencies are installed and credentials are configured:

- Linux / macOS: `skill action=exec: bash skill://scripts/check_env.sh`
- Windows: `skill action=exec: powershell -ExecutionPolicy Bypass -File skill://scripts/check_env.ps1`

If the environment check fails, fix according to the prompt and re-execute until it passes.

### Step 2: Identify and Execute Query Script

1. Based on the user's query intent, read `references/<service>/guide.md` to determine the script path and parameters to execute
2. First execute `-h` to view script usage:
   - Linux / macOS: `skill action=exec: skill://.venv/bin/python3 skill://scripts/<service>/<script>.py -h`
   - Windows: `skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/<service>/<script>.py -h`
3. Assemble parameters based on user requirements and execute the script:
   - Linux / macOS: `skill action=exec: skill://.venv/bin/python3 skill://scripts/<service>/<script>.py <parameters>`
   - Windows: `skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/<service>/<script>.py <parameters>`
4. Format the results and return to the user

**Important:**

- All scripts and environment check scripts are inside the skill package, **must be executed using `skill action=exec`, do not run directly in shell**
- venv is auto-created by the check_env script; Python is located at `.venv/bin/python3` on Linux/macOS and `.venv/Scripts/python3.exe` on Windows
- Do not execute scripts directly with `python3`
- Do not read script source code in the scripts directory; just follow the instructions in guide.md
- Cache results when output is large
- `--project_id` parameter is optional; if not provided, it is auto-fetched based on region via IAM API

---

## Directory Structure

Directory conventions are as follows (all paths are relative to the skill directory):

1. scripts/<resource_category>/ contains the Python query scripts for the corresponding resources. No need to read script contents; just execute scripts according to the usage instructions in guide.md
2. references/<resource_category>/guide.md contains the usage guide for the corresponding resources
3. Each script is responsible for a single, clear query action
4. Each resource category must have at least one guide.md explaining script capabilities, parameters, and usage

---

## Parameter Confirmation

Before executing query scripts, confirm the following parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| region | Yes | Huawei Cloud region, e.g., cn-north-4 |
| --project_id | No | Project ID, auto-fetched if not provided |
| --availability_zone | No | Availability zone, required for some resource queries |

For script-specific parameters, see `references/<service>/guide.md`.

---

## Output Format

Query results are output in JSON format with the following common fields:

- `total`: Total number of matched resources
- `items`: Resource list, each resource contains key fields such as id, name, status, etc.
- Specific fields vary by resource type; see individual guide.md for details

---

## Verification Method

1. Run the environment check script to confirm dependencies and credentials are available
2. Use the `-h` parameter to view script usage and confirm parameters are correct
3. Execute queries on known resources and compare with console data to verify result accuracy
4. Check if the returned `total` count is reasonable

---

## Best Practices

1. Narrow the query scope first (specify region, availability zone, etc.) to avoid returning too much data
2. Use `--help` to view the full list of parameters supported by the script
3. Cache large query results locally to avoid repeated requests
4. When querying multiple resources, follow dependency order (e.g., query VPC first, then subnets)
5. When script execution fails, check environment variables and network connectivity first

---

## Reference Documentation

- Usage guides for each service query script: `references/<service>/guide.md`

---

## Notes

1. This skill only provides read-only query capabilities; no write operations are performed
2. Do NOT output values of HW_ACCESS_KEY, HW_SECRET_KEY, and other environment variables
3. All scripts must be executed via `skill action=exec`; do not run directly in shell
4. Do not guess script names; strictly execute according to names in guide.md
5. Must run the environment check script before querying
6. When using temporary AK/SK, set HW_SECURITY_TOKEN
