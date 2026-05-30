---
name: huawei-cloud-computing-query
description: "Queries Huawei Cloud computing resources (ECS/BMS/IMS/AS), Covers ECS instances, flavors, keypairs, quotas, server groups, block devices, NICs, VNC console, BMS bare metal servers/flavors/quotas, IMS images/OS versions/members/quotas, and AS scaling groups/configs/policies/activity logs/lifecycle hooks/warm pools/quotas. No write operations. Use this skill when the user needs to query ECS instance details, list flavors, check BMS availability, browse images, or view auto-scaling group/policy status. Triggers: 弹性云服务器, ECS, 裸金属, BMS, 镜像, IMS, 弹性伸缩, AS, 伸缩组, 伸缩策略, 规格查询, flavor, instance, image, scaling."
---
# Huawei Cloud Resource Query

> **⚠️ Execution Method (Must Read): This skill executes queries via local Python scripts. Using hcloud, openstack, or other CLI tools or direct API calls is prohibited.**
>
> - Query scripts are located under the skill directory `scripts/<service_category>/` (e.g., `scripts/as/list_scaling_groups.py`)
> - All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them; do not run them directly in the shell**
> - For specific script paths and parameters, see `references/<service>/guide.md`
> - **Do not attempt hcloud, openstack, curl IAM, or other CLI/API methods; this skill does not depend on those tools**
> - **All paths are relative to the skill directory, which is the directory containing this SKILL.md**

## Overview

This skill is a standalone read-only query skill that queries Huawei Cloud resources, available specifications, and existing resource information by calling the Huawei Cloud Python SDK via local Python scripts.

This skill is applicable to the following scenarios:

1. Query available cloud resource specifications in a given region
2. Query available images for a specific operating system
3. Query cloud disk types and existing cloud disk information
4. Query existing resources and their key attributes
5. Query resources not created through Terraform or other IaC tools
6. Prepare real parameters for automation configuration, resource verification, or environment inventory
7. Obtain reusable information such as resource IDs, names, specifications, images, networks, and disks

This skill does NOT handle the following:

1. Creating resources
2. Modifying resources
3. Deleting resources
4. Guessing or fabricating information that was not queried

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

Important: Script paths executed within this skill are all relative to the skill directory, which is the directory containing this SKILL.md

1. This skill only performs queries; it does not perform any write operations
2. Prioritize using information explicitly specified by the user, such as region, project, AZ, resource name, and resource ID
3. Query results must be based on actual API responses; do not speculate based on experience
4. Returned results should preserve key fields for subsequent reuse
5. When the result set is large, prioritize narrowing the scope by conditions such as region, name, id, status, and tag
6. If the current resource type does not have a corresponding script or guide, clearly state that it is not supported; do not return unreliable results
7. If the user does not provide necessary scope information and there are no default values in the environment, confirm the information before executing the query
8. Execute directly according to guide.md; do not read the script contents in the scripts directory
9. Cache output when it is large
10. You must execute `-h` to view usage before executing each script
11. Do not fabricate script names; execute according to the script names in guide.md. If a script name is not in guide.md, it means it is not supported

---

## Prerequisites

**Before use, you must run the environment check script to complete environment verification and dependency installation in one step:**

- Linux / macOS: `skill action=exec: bash skill://scripts/check_env.sh`
- Windows: `skill action=exec: powershell -ExecutionPolicy Bypass -File skill://scripts/check_env.ps1`

> Windows Note: Do not use `&&` to concatenate commands (PowerShell 5.x does not support this); use semicolons if you need to change directories first

The script will check in order: Python >= 3.6 → install dependencies → verify SDK → verify credentials → verify service availability. If the environment check fails, fix the issue before continuing with other scripts.

**Environment Variables:**

| Variable | Required | Description |
|----------|----------|-------------|
| HW_ACCESS_KEY | Yes | Huawei Cloud AK |
| HW_SECRET_KEY | Yes | Huawei Cloud SK |
| HW_REGION_NAME | No | Default cn-north-4 |
| HW_PROJECT_ID | No | Project ID (automatically obtained via IAM API if not set) |
| HW_SECURITY_TOKEN | No | Required for temporary AK/SK |

**Do not output the values of the above environment variables.** For other resource scripts that require additional parameters (availability zone, enterprise project, etc.), see the corresponding guide.md.

---

## Execution Flow

**When this skill is invoked, you must follow these steps; do not wait for the user to prompt again:**

### Step 1: Environment Preparation

Execute the environment check script to ensure dependencies are installed and credentials are configured:

- Linux / macOS: `skill action=exec: bash skill://scripts/check_env.sh`
- Windows: `skill action=exec: powershell -ExecutionPolicy Bypass -File skill://scripts/check_env.ps1`

If the environment check fails, fix the issue as prompted and re-execute until it passes.

### Step 2: Identify and Execute Query Scripts

1. Based on the user's query intent, read `references/<service>/guide.md` to determine the script path and parameters to execute
2. First execute `-h` to view script usage:
   - Linux / macOS: `skill action=exec: skill://.venv/bin/python3 skill://scripts/<service>/<script>.py -h`
   - Windows: `skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/<service>/<script>.py -h`
3. Assemble parameters based on user requirements and execute the script:
   - Linux / macOS: `skill action=exec: skill://.venv/bin/python3 skill://scripts/<service>/<script>.py <parameters>`
   - Windows: `skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/<service>/<script>.py <parameters>`
4. Format the results and return them to the user

**Important:**

- All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them; do not run them directly in the shell**
- The venv is automatically created by the check_env script. On Linux/macOS, Python is located at `.venv/bin/python3`; on Windows, at `.venv/Scripts/python3.exe`
- Do not use `python3` directly to execute scripts
- Do not read script source code in the scripts directory; execute according to the instructions in guide.md
- Cache results when the output is large
- The `--project_id` parameter is optional; if not provided, it is automatically obtained via the IAM API based on the region

---

## Directory Structure

The directory conventions are as follows (all paths are relative to the skill directory):

1. scripts/<resource_category>/ contains the Python query scripts for the corresponding resources. You do not need to read the script contents; execute the scripts according to the usage instructions in guide.md
2. references/<resource_category>/guide.md contains the usage guide for the corresponding resources
3. Each script is responsible for a single, clear query action
4. Each resource category maintains at least one guide.md to describe script capabilities, parameters, and usage

---

## Parameter Confirmation

Before executing query scripts, confirm the following parameters:

| Parameter | Required | Description |
|-----------|----------|-------------|
| region | Yes | Huawei Cloud region, e.g., cn-north-4 |
| --project_id | No | Project ID; automatically obtained if not provided |
| --availability_zone | No | Availability zone; required for some resource queries |

For script-specific parameters, see `references/<service>/guide.md`.

---

## Output Format

Query results are output in JSON format, containing the following common fields:

- `total`: Total number of matching resources
- `items`: Resource list, each resource containing key fields such as id, name, and status
- Specific fields vary by resource type; see individual guide.md files for details

---

## Verification Method

1. Execute the environment check script to confirm dependencies and credentials are available
2. Use the `-h` parameter to view script usage and confirm parameters are correct
3. Execute a query on a known resource and compare with console data to verify result accuracy
4. Check whether the returned `total` count is reasonable

---

## Best Practices

1. Narrow the query scope first (specify region, availability zone, etc.) to avoid returning too much data
2. Use `--help` to view the complete list of parameters supported by a script
3. Cache query results locally when they are large to avoid repeated requests
4. When multiple resource information is needed, query in dependency order (e.g., query VPC first, then subnet)
5. When script execution fails, check environment variables and network connectivity first

---

## Reference Documentation

- [Huawei Cloud Python SDK Official Documentation](https://doc.huihua.com/api/sdk/python.html)
- [Huawei Cloud API Explorer](https://support.huaweicloud.com/apiexplorer/index.html)
- Query script usage guides for each service: `references/<service>/guide.md`

---

## Notes

1. This skill only provides read-only query capabilities; it does not perform any write operations
2. Do not output values of environment variables such as HW_ACCESS_KEY and HW_SECRET_KEY
3. All scripts must be executed via `skill action=exec`; do not run them directly in the shell
4. Do not fabricate script names; strictly execute according to the names in guide.md
5. You must run the environment check script before querying
6. When using temporary AK/SK, you need to set HW_SECURITY_TOKEN
