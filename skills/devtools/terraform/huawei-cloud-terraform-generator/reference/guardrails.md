# Guardrails

This document describes the guardrails and safety rules for Terraform generation.

## Do not fabricate specifications, prices, or resource facts

Recommended specifications, models, prices, and existing resource facts must not be fabricated.

They must come from one of the following:

1. explicit user input
2. a reliable resource information lookup channel
3. Terraform data sources resolved during Terraform execution

This applies to values such as:

- region
- availability zone
- flavor / instance type
- image name / image ID
- disk type
- cluster version
- database flavor
- existing resource IDs or names
- pricing

If a value has not been confirmed, present it as pending or unresolved. Do not present it as validated.

This also applies to execution narratives. When reporting what happened during
validation, only describe steps that actually occurred with actual command
outputs. Do not fabricate or infer execution sequences, errors, or recovery
actions that did not actually happen. If a step succeeded on the first attempt
without issues, report it as such — do not invent a prior failure and recovery
story around it.

## Query specifications before using (CRITICAL)

**CRITICAL: Always query available specifications from the target region before proposing to user or using in Terraform.**

### Availability zone validation

**Problem:** Using `data.huaweicloud_availability_zones.test.names[0]` always picks the first zone, which may not be what the user wants or confirmed.

**Required workflow:**
1. Determine target region
2. Query available availability zones
3. Present zones to user or recommend one
4. User confirms specific zone
5. Use confirmed zone as a variable (NOT as data source index)

**Forbidden:**
- ❌ Using `data.huaweicloud_availability_zones.test.names[0]` to always pick first zone
- ❌ Hardcoding availability zone names
- ❌ Assuming zone names based on other regions

### Flavor validation

**Problem:** Flavor availability varies by region and availability zone. A flavor that exists in one region may not exist in another.

**Required workflow:**
1. Determine target region and availability zone
2. Query available flavors using `huawei-cloud-computing-query` skill
3. Select flavor from query results (NOT from hardcoded defaults)
4. Verify the selected flavor exists in the returned list
5. Use the exact flavor name from query result

**Forbidden:**
- ❌ Using hardcoded flavor names without querying
- ❌ Assuming a flavor exists because it exists in another region
- ❌ Using user-provided flavor name without validation

### Image validation

**Problem 1:** Image names must match EXACTLY for Terraform data sources. User may provide abbreviated names that don't match.

**Problem 2:** Image version mismatch. User may confirm "Ubuntu 22.04" but template uses `os = "Ubuntu"` without version, causing any Ubuntu version to be returned.

**Required workflow:**
1. Determine target region
2. Query available images using `huawei-cloud-computing-query` skill
3. Match user's intent to exact image name with version from query results
4. Use the EXACT image name (including version) in Terraform

**Example of name mismatch:**
| User says | Actual name in Huawei Cloud |
|-----------|----------------------------|
| EulerOS 2.0 | Huawei Cloud EulerOS 2.0 Standard 64 bit |
| Ubuntu 22.04 | Ubuntu 22.04 server 64bit |
| CentOS 7 | CentOS 7.9 64bit |

**Example of version mismatch:**
| User confirms | Template uses | Result returned | Actual installed |
|--------------|---------------|-----------------|------------------|
| Ubuntu 22.04 | `os = "Ubuntu"` | Ubuntu 24.04 | Ubuntu 24.04 ❌ |
| Ubuntu 22.04 | `os_version = "Ubuntu 22.04 server 64bit"` | Ubuntu 22.04 | Ubuntu 22.04 ✅ |

**Forbidden:**
- ❌ Using image names like "EulerOS 2.0" without exact match
- ❌ Using `os = "Ubuntu"` without version (may return wrong version)
- ❌ Using hardcoded image names without querying
- ❌ Guessing image names based on common patterns
- ❌ Proceeding if query returns empty results

### Security group rules validation

**Required workflow:**
1. Infer likely ports from user's goal (web → 80, 443; SSH → 22; database → 3306, 5432)
2. Ask user to confirm which ports to open
3. Generate rules based on user-confirmed ports
4. Always include egress rule

**Forbidden:**
- ❌ Using only egress rule without ingress rules
- ❌ Using hardcoded default ports without asking user
- ❌ Generating rules that don't match user confirmation

### Empty query results handling

**Required workflow:**
1. Query specifications using API before generating Terraform
2. If empty: Stop immediately, report error, suggest alternatives, ask user to change conditions
3. If not empty: Proceed with recommendation and user confirmation

**Use exact names instead of data source queries, after validating via API.**

**Forbidden:**
- ❌ Proceeding when query returns empty results
- ❌ Relying on `try()` to silently handle empty results

## Prefer recommended defaults, but do not fabricate validated facts

When the user does not provide every input explicitly, prefer to propose a reasonable default plan rather than asking the user to choose everything from scratch.

For example, the skill may recommend:

- a default region
- a default deployment pattern
- a default operating system choice
- a default resource combination for common scenarios

However:

- recommended defaults must be clearly presented as recommendations
- validated resource facts must come from explicit user input, a reliable lookup channel, or Terraform data sources
- do not present unverified specifications, prices, or existing resources as confirmed facts

## Execute terraform apply with explicit user confirmation

After `terraform plan` succeeds, the agent must popup a confirmation dialog for user confirmation before executing apply.

**Workflow:**

1. Show the terraform plan output to the user
2. **Do NOT mention or reference HW_ACCESS_KEY/HW_SECRET_KEY when showing the plan output**
3. Popup a confirmation dialog asking: "Do you want to execute terraform apply to create these resources?"
4. Based on user selection:
   - If user confirms: execute `terraform apply`
   - If user declines: stop and inform user they can apply manually later
5. Report the apply execution result to the user

**Rules:**

- Never execute `terraform apply` without user confirmation via confirmation dialog
- Always show the plan output before requesting confirmation
- Never execute `terraform destroy` without user confirmation via confirmation dialog

**After apply execution:**

- If apply succeeds: inform the user and show created resources
- If apply fails: explain the error and offer to help fix the issue

## Do not generate outputs

Do not generate:

- `outputs.tf`
- any `output` blocks

The generated Terraform should focus only on the resources and required input variables.

## Security group port validation

When configuring security group rules, never set port number to 0.

**Rules:**

- Port numbers must be valid positive integers (1-65535)
- Port 0 is invalid and must never be used in security group rules
- `port_range_min` and `port_range_max` must be >= 1
- `ports` configuration must not contain 0
- If a specific port is needed, both `port_range_min` and `port_range_max` should be set to the same valid port number

## Do not request sensitive information

Never ask the user to provide sensitive information directly in the conversation.

**Sensitive information includes:**

- Access keys (AK)
- Secret keys (SK)
- Passwords
- API tokens
- Private keys
- Database credentials
- SSH keys
- Any authentication credentials

**Handling different types of sensitive information:**

**AK/SK (Access Keys):**

- Can only be configured via environment variables (HW_ACCESS_KEY, HW_SECRET_KEY)
- For temporary/STS credentials, the agent **must** read `HW_SECURITY_TOKEN` (or `HUAWEICLOUD_SECURITY_TOKEN`) from environment variables and write it to `terraform.tfvars` as `security_token`. The provider does not reliably resolve `security_token` from env vars. If the env var is not set, omit it (permanent AK/SK scenario).
- Never guide or prompt user to configure them
- Assume user has already configured them appropriately

**Other sensitive information (passwords, tokens, database credentials, etc.):**

- Generate random strong passwords for all sensitive information based on **Strong password characteristics** in `terraform.tfvars` file
- Inform the user of all generated passwords and credentials
- Remind user they can edit terraform.tfvars with their own values if needed before running terraform apply
- Never ask for actual values in conversation

**Strong password characteristics:**

- 16 characters minimum length
- Contains uppercase letters (A-Z)
- Contains lowercase letters (a-z)
- Contains digits (0-9)
- Contains special characters (!@#$%^&*)
- Randomly generated, no predictable patterns

**Allowed approach:**

- Guide users to configure non-AK/SK sensitive information in terraform.tfvars
- Instruct users to edit configuration files manually
- Never read, inspect, or log sensitive values from files or environment

**If sensitive information is accidentally exposed:**

- Do not store or repeat it
- Advise user to rotate/change the credentials immediately
- Continue with secure approach (e.g., guide to terraform.tfvars)

## Do not guide AK/SK environment variable configuration

**CRITICAL:** Never ask, prompt, or guide the user to configure or ensure AK/SK in environment variables.

**Rules:**

- Never ask "Have you configured HW_ACCESS_KEY and HW_SECRET_KEY?"
- Never instruct "Please set HW_ACCESS_KEY and HW_SECRET_KEY environment variables"
- Never show examples of how to export/set HW_ACCESS_KEY/HW_SECRET_KEY environment variables
- Never wait for user confirmation about credential configuration
- Assume credentials are already configured by the user
- Proceed directly to validation without any credential-related prompts

**Rationale:**

- The user is responsible for their own credential management
- Guiding credential setup may expose sensitive information in conversation history
- Different users have different secure credential management practices
- The agent should not interfere with the user's security practices
