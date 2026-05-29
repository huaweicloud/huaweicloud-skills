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
2. **Do NOT mention or reference AK/SK when showing the plan output**
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

- Must be configured via environment variables (HW_ACCESS_KEY, HW_SECRET_KEY)
- Never guide or prompt user to configure them
- Assume user has already configured them appropriately

**Other sensitive information (passwords, tokens, database credentials, etc.):**

- Recommend user to configure in `terraform.tfvars` file
- Provide placeholder values in generated terraform.tfvars (e.g., "CHANGE_ME", "YOUR_PASSWORD_HERE")
- Remind user to edit terraform.tfvars with their actual values before running terraform apply
- Never ask for actual values in conversation

**Allowed approach:**

- Guide users to configure non-AK/SK sensitive information in terraform.tfvars
- Instruct users to edit configuration files manually
- Never read, inspect, or log sensitive values from files or environment

**If sensitive information is accidentally exposed:**

- Do not store or repeat it
- Advise user to rotate/change the credentials immediately
- Continue with secure approach (e.g., guide to terraform.tfvars)

## Do not guide AK/SK environment variable configuration

**CRITICAL:** Never ask, prompt, or guide the user to configure AK/SK in environment variables.

**Rules:**

- Never ask "Have you configured HW_ACCESS_KEY and HW_SECRET_KEY?"
- Never instruct "Please set HW_ACCESS_KEY and HW_SECRET_KEY environment variables"
- Never show examples of how to export/set AK/SK environment variables
- Never wait for user confirmation about credential configuration
- Assume credentials are already configured by the user
- Proceed directly to validation without any credential-related prompts

**Rationale:**

- The user is responsible for their own credential management
- Guiding credential setup may expose sensitive information in conversation history
- Different users have different secure credential management practices
- The agent should not interfere with the user's security practices
