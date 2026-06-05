---
name: huawei-cloud-network-query
description: "Queries Huawei Cloud network resources (VPC/EIP/ELB/NAT/VPN/DNS). Covers VPCs, subnets, security groups, firewalls, route tables, flow logs, EIPs, bandwidths, load balancers, listeners, pools, health monitors, NAT gateways, SNAT/DNAT rules, VPN gateways, VPN connections, DNS zones, record sets, PTR records, and endpoints. No write operations. Use this skill when the user needs to query network topology, security group rules, load balancer config, NAT rules, VPN status, or DNS resolution info. Triggers: VPC, 子网, 安全组, EIP, 弹性公网IP, ELB, 负载均衡, NAT网关, VPN, DNS, 域名解析, 路由表, 防火墙, 带宽, network, subnet, security group."
---
# Huawei Cloud Resource Query

> **⚠️ Execution Method (Must Read): This skill executes queries via local Python scripts. Using hcloud, openstack or other CLI tools or direct API calls is prohibited.**
>
> - Query scripts are located under the skill directory `scripts/<service_category>/` (e.g., `scripts/as/list_scaling_groups.py`)
> - All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them. Do not run them directly in a shell.**
> - For specific script paths and parameters, refer to `references/<service>/guide.md`
> - **Do not attempt hcloud, openstack, curl IAM or other CLI/API methods. This skill does not depend on those tools.**
> - **All paths are relative to the skill directory, which is the directory where this SKILL.md is located.**

## Overview

This skill is an independent read-only query skill that queries Huawei Cloud resources, available specifications, and existing resource information by calling the Huawei Cloud Python SDK via local Python scripts.

This skill is applicable to the following scenarios:

1. Query available cloud resource specifications in a specific region
2. Query which images are available for a certain operating system
3. Query cloud disk types and existing cloud disk information
4. Query existing resources and their key attributes
5. Query resources that were not created through Terraform or other IaC tools
6. Prepare real parameters for automated configuration, resource verification, or environment inventory
7. Obtain reusable information such as resource IDs, names, specifications, images, networks, and disks

This skill is NOT responsible for:

1. Creating resources
2. Modifying resources
3. Deleting resources
4. Guessing or fabricating information that has not been queried

---

## Capability Scope

This skill provides query capabilities through categorized scripts in the scripts directory, and usage instructions through categorized guides in the references directory.
The capabilities provided by this skill include:

1. Query resource lists
2. Query individual resource details
3. Query selection information such as available specifications, images, and disk types
4. Query key identifiers and dependency relationships of existing resources

---

## Usage Principles

Important: Script paths executed within this skill are all relative paths under the skill directory, which is the directory where this SKILL.md is located.

1. This skill only performs queries; it does not perform any write operations
2. Prioritize information explicitly specified by the user, such as region, project, AZ, resource name, resource ID, etc.
3. Query results must be based on actual API responses; do not infer from experience
4. Returned results should prioritize retaining key fields for subsequent reuse
5. When the result set is large, narrow the scope first by conditions such as region, name, id, status, tag, etc.
6. If there is no corresponding script or guide for the current resource type, clearly state that it is not supported; do not return unreliable results
7. If the user does not provide necessary scope information and there are no default values in the environment, confirm with the user before executing the query
8. Execute directly according to guide.md; do not view the script contents in the scripts directory
9. Cache output when it is large
10. You must run `-h` to view usage before executing each script
11. Do not make up script names. Execute according to the script names in guide.md. If a script name is not in guide.md, it means it is not supported

---

## Prerequisites

**You must run the environment check script first to complete environment validation and dependency installation in one step:**

- Linux / macOS: `skill action=exec: bash skill://scripts/check_env.sh`
- Windows: `skill action=exec: powershell -ExecutionPolicy Bypass -File skill://scripts/check_env.ps1`

> Windows Note: Do not use `&&` to concatenate commands (PowerShell 5.x does not support it). Use semicolons if you need to change directories first.

The script will check in order: Python >= 3.6 → Install dependencies → Validate SDK → Validate credentials → Validate service availability. If the environment check fails, fix the issues before continuing with other scripts.

**Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| HW_ACCESS_KEY | Yes | Huawei Cloud AK |
| HW_SECRET_KEY | Yes | Huawei Cloud SK |
| HW_REGION_NAME | No | Default cn-north-4 |
| HW_PROJECT_ID | No | Project ID (automatically obtained via IAM API when not set) |
| HW_SECURITY_TOKEN | No | Required when using temporary AK/SK |

**Do not output the values of the above environment variables.** For additional parameters required by other resource scripts (availability zone, enterprise project, etc.), see the corresponding guide.md.

---

## Execution Flow

**When this skill is invoked, you must follow these steps. Do not wait for the user to prompt again:**

### Step 1: Environment Preparation

Run the environment check script to ensure dependencies are installed and credentials are configured:

- Linux / macOS: `skill action=exec: bash skill://scripts/check_env.sh`
- Windows: `skill action=exec: powershell -ExecutionPolicy Bypass -File skill://scripts/check_env.ps1`

If the environment check fails, fix the issues as prompted and re-run until it passes.

### Step 2: Identify and Execute Query Scripts

1. Based on the user's query intent, read `references/<service>/guide.md` to determine the script path and parameters to execute
2. First run `-h` to view the script usage:
   - Linux / macOS: `skill action=exec: skill://.venv/bin/python3 skill://scripts/<service>/<script>.py -h`
   - Windows: `skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/<service>/<script>.py -h`
3. Assemble parameters based on user needs and execute the script:
   - Linux / macOS: `skill action=exec: skill://.venv/bin/python3 skill://scripts/<service>/<script>.py <parameters>`
   - Windows: `skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/<service>/<script>.py <parameters>`
4. Format the results and return them to the user

**Important:**

- All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them. Do not run them directly in a shell.**
- The venv is automatically created by the check_env script. On Linux/macOS, Python is located at `.venv/bin/python3`; on Windows, it is at `.venv/Scripts/python3.exe`
- Do not execute scripts directly with `python3`
- Do not read the script source code in the scripts directory; just follow the instructions in guide.md
- Cache results when the output is large
- The `--project_id` parameter is optional; when not provided, it is automatically obtained via IAM API based on the region

---

## Directory Structure

The directory conventions are as follows (all paths are relative to the skill directory):

1. `scripts/<resource_category>/` contains the corresponding Python query scripts. There is no need to read script contents; just execute the scripts according to the instructions in guide.md
2. `references/<resource_category>/guide.md` contains the usage guide for the corresponding resource
3. Each script is responsible for a single, clear query action
4. Each resource category must maintain at least one guide.md to document script capabilities, parameters, and usage

---

## Parameter Confirmation

Before executing a query script, confirm the following parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| region | Yes | Huawei Cloud region, e.g., cn-north-4 |
| --project_id | No | Project ID; automatically obtained when not provided |
| --availability_zone | No | Availability zone; required for some resource queries |

For script-specific parameters, see `references/<service>/guide.md`.

---

## Output Format

Query results are output in JSON format and include the following common fields:

- `total`: Total number of matched resources
- `items`: Resource list, where each resource contains key fields such as id, name, status, etc.
- Specific fields vary by resource type; see each guide.md for details

---

## Verification Method

1. Run the environment check script to confirm dependencies and credentials are available
2. Use the `-h` parameter to view script usage and confirm parameters are correct
3. Execute queries on known resources and compare with console data to verify result accuracy
4. Check whether the returned `total` count is reasonable

---

## Best Practices

1. Narrow the query scope first (specify region, availability zone, etc.) to avoid returning too much data
2. Use `--help` to view the complete list of parameters supported by a script
3. Cache query results locally when they are large to avoid repeated requests
4. When multiple resource information is needed, query in dependency order (e.g., query VPC first, then subnets)
5. When script execution fails, check environment variables and network connectivity first

---

## Reference Documentation

- Usage guides for each service query script: `references/<service>/guide.md`

---

## Notes

1. This skill only provides read-only query capabilities; it does not perform any write operations
2. Do not output the values of environment variables such as HW_ACCESS_KEY and HW_SECRET_KEY
3. All scripts must be executed via `skill action=exec`; do not run them directly in a shell
4. Do not guess script names; execute strictly according to the names in guide.md
5. You must run the environment check script before querying
6. When using temporary AK/SK, you need to set HW_SECURITY_TOKEN
