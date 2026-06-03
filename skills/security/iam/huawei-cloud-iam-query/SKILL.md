---
name: huawei-cloud-iam-query
description: "Queries Huawei Cloud identity and access management resources (IAM) via read-only Python SDK. Covers users, groups, policies, agencies, AK/SK, MFA devices, login/password/ACL policies, security compliance, and account quotas. No write operations. Use this skill when the user needs to query IAM identity info, check policies/permissions, view agency details, or inspect AK/SK/MFA status. Triggers: IAM, 用户, 用户组, 策略, 委托, 权限, AK/SK, MFA, 密码策略, 安全合规, 身份查询, 身份认证, identity, policy, agency."
---
# Huawei Cloud Resource Query

> **⚠️ Execution Method (Must Read): This skill executes queries via local Python scripts. Using hcloud, openstack, or other CLI tools or direct API calls is prohibited.**
>
> - Query scripts are located under the skill directory `scripts/<service_category>/` (e.g., `scripts/as/list_scaling_groups.py`)
> - All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them; do not run them directly in a shell**
> - For specific script paths and parameters, see `references/<service>/guide.md`
> - **Do not attempt hcloud, openstack, curl IAM, or other CLI/API methods. This skill does not depend on these tools**
> - **All paths are relative to the skill directory, which is the directory where this SKILL.md resides**

## Overview

This skill is a standalone read-only query skill that uses local Python scripts to call the Huawei Cloud Python SDK to query Huawei Cloud resources, available specifications, and existing resource information.

This skill is applicable to the following scenarios:

1. Query available cloud resource specifications in a given region
2. Query available images for a certain operating system
3. Query cloud disk types and existing cloud disk information
4. Query existing resources and their key attributes
5. Query resources not created through Terraform or other IaC tools
6. Prepare real parameters for automation configuration, resource verification, or environment inventory
7. Obtain reusable information such as resource IDs, names, specifications, images, networks, and disks

This skill does NOT handle the following:

1. Creating resources
2. Modifying resources
3. Deleting resources
4. Guessing or fabricating information that has not been queried

---

## Capability Scope

This skill provides query capabilities through categorized scripts under the scripts directory, and usage instructions through categorized guides under the references directory.
Capabilities provided by this skill include:

1. Query resource lists
2. Query individual resource details
3. Query available specifications, images, disk types, and other selection information
4. Query key identifiers and dependency relationships of existing resources

---

## Usage Principles

Important: Script paths executed within this skill are all relative to the skill directory, which is the directory where this SKILL.md resides

1. This skill only performs queries; it does not perform any write operations
2. Prioritize using explicitly specified region, project, AZ, resource name, resource ID, etc. provided by the user
3. Query results must be based on actual API responses; do not infer based on experience
4. Returned results should prioritize retaining key fields for subsequent reuse
5. When the result set is large, narrow the scope first using conditions such as region, name, id, status, tag, etc.
6. If there is no corresponding script or guide for the current resource type, clearly state that it is not supported; do not return unreliable results
7. If the user has not provided necessary scope information and there are no default values in the environment, confirm the missing information before executing the query
8. Execute directly according to guide.md; do not view script contents in the scripts directory
9. Cache output when it is large
10. You must execute `-h` before each script execution to view usage
11. Do not guess script names; execute according to the script names in guide.md. If a script name is not in guide.md, it means it is not supported

---

## Prerequisites

**Before using, you must run the environment check script to complete environment validation and dependency installation in one step:**

- Linux / macOS: `skill action=exec: bash skill://scripts/check_env.sh`
- Windows: `skill action=exec: powershell -ExecutionPolicy Bypass -File skill://scripts/check_env.ps1`

> Windows Note: Do not use `&&` to chain commands (PowerShell 5.x does not support it). Use semicolons if you need to change directories first.

The script will check in sequence: Python >= 3.6 → install dependencies → validate SDK → validate credentials → validate service availability.
If the environment check fails, fix the issues before continuing with other scripts.

**Environment Variables:**

| Variable | Required | Description |
|------|------|------|
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
2. First execute `-h` to view script usage:
   - Linux / macOS: `skill action=exec: skill://.venv/bin/python3 skill://scripts/<service>/<script>.py -h`
   - Windows: `skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/<service>/<script>.py -h`
3. Assemble parameters based on user requirements and execute the script:
   - Linux / macOS: `skill action=exec: skill://.venv/bin/python3 skill://scripts/<service>/<script>.py <parameters>`
   - Windows: `skill action=exec: skill://.venv/Scripts/python3.exe skill://scripts/<service>/<script>.py <parameters>`
4. Format the results and return them to the user

**Important**:

- All scripts and environment check scripts are inside the skill package. **You must use `skill action=exec` to execute them; do not run them directly in a shell**
- The venv is automatically created by the check_env script. On Linux/macOS, Python is located at `.venv/bin/python3`; on Windows, at `.venv/Scripts/python3.exe`
- Do not use `python3` directly to execute scripts
- Do not read script source code in the scripts directory; just follow the instructions in guide.md
- Cache results when output is large
- The `--project_id` parameter is optional; when not provided, it is automatically obtained via the IAM API based on region

---

## Directory Structure

Directory conventions are as follows (all paths are relative to the skill directory):

1. scripts/<resource_category>/ contains Python query scripts for the corresponding resources. You do not need to read script contents; just execute scripts according to the usage instructions in guide.md
2. references/<resource_category>/guide.md contains usage guides for the corresponding resources
3. Each script is responsible for only one clear, single query action
4. Each resource category maintains at least one guide.md to describe script capabilities, parameters, and usage

---

## Parameter Confirmation

Before executing a query script, confirm the following parameters:

| Parameter | Required | Description |
|------|------|------|
| region | Yes | Huawei Cloud region, e.g., cn-north-4 |
| --project_id | No | Project ID; automatically obtained when not provided |
| --availability_zone | No | Availability zone; required for some resource queries |

For script-specific parameters, see `references/<service>/guide.md`.

---

## Output Format

Query results are output in JSON format, containing the following common fields:

- `total`: Total number of matched resources
- `items`: Resource list, where each resource contains key fields such as id, name, status, etc.
- Specific fields vary by resource type; see individual guide.md files for details

---

## Verification Method

1. Run the environment check script to confirm dependencies and credentials are available
2. Use the `-h` parameter to view script usage and confirm correct parameters
3. Execute queries on known resources and compare with console data to verify result accuracy
4. Check whether the returned `total` count is reasonable

---

## Best Practices

1. Narrow the query scope first (specify region, availability zone, etc.) to avoid returning too much data
2. Use `--help` to view the complete list of supported parameters for a script
3. Cache large query results locally to avoid repeated requests
4. When querying multiple resources, follow dependency order (e.g., query VPC first, then subnets)
5. When script execution fails, check environment variables and network connectivity first

---

## Reference Documentation

- Query script usage guides for each service: `references/<service>/guide.md`

---

## Notes

1. This skill only provides read-only query capabilities; it does not perform any write operations
2. Do not output the values of environment variables such as HW_ACCESS_KEY, HW_SECRET_KEY, etc.
3. All scripts must be executed via `skill action=exec`; do not run them directly in a shell
4. Do not guess script names; strictly execute according to the names in guide.md
5. You must run the environment check script before querying
6. When using temporary AK/SK, you must set HW_SECURITY_TOKEN
