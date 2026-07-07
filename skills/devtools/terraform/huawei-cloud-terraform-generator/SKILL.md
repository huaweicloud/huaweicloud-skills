---
name: huawei-cloud-terraform-generator
description: Generate Huawei Cloud Terraform configurations and execute deployment with user-guided approval. Use this skill when users want to create Huawei Cloud infrastructure as Terraform, whether they ask explicitly for Terraform or describe goals such as deploying a website, launching an application, or creating network, compute, database, load balancing, or storage resources. Trigger when users mention 创建/create、生成/generate、部署/deploy、配置/configure、使用/use、管理/manage、华为云/Huawei Cloud、Terraform、ECS、VPC、资源/resource、云服务器/ECS、虚拟机/VM、实例/instance、网络/network、负载均衡/ELB、数据库/database、RDS、存储/storage、OBS、桶/bucket、域名/domain、DNS、证书/certificate、SSL、监控/monitoring、日志/log、备份/backup、容器/container、CCE、函数工作流/FunctionGraph
---

# Huawei Cloud Terraform Generator

## 1. Overview

This skill turns user infrastructure goals into Terraform configurations for Huawei Cloud. The primary workflow is to:

1. understand the user's actual deployment intent
2. determine which resources should be created
3. determine whether existing resources should be reused
4. confirm key specifications and dependencies
5. **verify every resource specification against the target region's available resources — query first, write later**
6. ensure Terraform is installed
7. generate Terraform configuration files
8. run validation steps and fix generation issues until `terraform plan` succeeds
9. ask user for confirmation and execute `terraform apply` if approved

This skill provides an interactive workflow where the agent guides the user through credential configuration, validates the plan, and executes apply upon explicit user confirmation.

## 2. Prerequisites

Before using this skill, ensure the following are available:

1. **Terraform** — installed in PATH or auto-installable (see validation-workflow.md)
2. **Provider download source** — the Huawei Cloud mirror should be reachable (see validation-workflow.md)
3. **Target region** — the deployment region (e.g. cn-north-4, cn-south-1) must be identified

## 3. Parameter Confirmation

Before generating Terraform, propose a concrete resource plan for the user to confirm. The plan should include:

- recommended resource specifications
- available candidate options when applicable
- whether to create new resources or reuse existing ones
- pricing information only when obtained from a reliable source

See `reference/guardrails.md` for rules about not fabricating specifications and prices.

Do not ask the user to provide every parameter manually. Instead:

1. infer the likely architecture from the user's goal
2. propose a concrete plan with recommended defaults
3. confirm only the small number of decisions that materially affect correctness, cost, or architecture

Users should mainly confirm a proposed solution, not build the full parameter set themselves.

## 4. Workflow

This skill works in nine phases:

### 4.0 Credential handling (MUST READ)                                                                                                                                                                                                                                           

AK/SK credentials are read from environment variables `HW_ACCESS_KEY` and `HW_SECRET_KEY`. For temporary/STS credentials, the agent **must** read `HW_SECURITY_TOKEN` (or `HUAWEICLOUD_SECURITY_TOKEN`) from environment variables and write it to `terraform.tfvars` as `security_token`. The provider does not reliably resolve `security_token` from env vars. If the env var is not set, omit it (permanent AK/SK scenario).
Before any step that depends on credentials (resource queries, `terraform plan`, etc.), read the complete rules in `reference/guardrails.md`.
If an API or Terraform call fails with an authentication error: tell the user the specific error, ask them to confirm when the issue is resolved, then retry. Do not guide the user on how to configure credentials.

### 4.1 Understand the user's real goal

The user may describe a resource directly, such as creating an ECS instance, or describe a business goal, such as deploying a website or launching an application.  
You must first infer the intended Huawei Cloud architecture from the user's objective, not just from explicit resource names.

### 4.2 Determine the resource set

Based on the user's goal, identify:

- which resources need to be created
- which existing resources may be reused
- what dependencies exist between the resources

For example:

- a simple public website may require VPC, subnet, security group, ECS, and EIP
- a managed database deployment may require VPC, subnet, security group, and RDS
- a scalable public service may require VPC, subnet, security group, ECS or AS, ELB, and public access

### 4.3 Propose a resource plan for confirmation

Before generating Terraform, propose a concrete resource plan for the user to confirm following the rules in the Parameter Confirmation section.

See `reference/guardrails.md` for rules about handling sensitive information.

### 4.3.1 Confirm security group rules with user (CRITICAL)

**Required workflow:**

1. Infer likely ports from user's goal (Web server → 80, 443; SSH → 22; Database → 3306, 5432)
2. Ask user to confirm ports: "需要开放哪些端口？推荐：80、443、22"
3. Generate rules based on confirmed ports, NOT default rules

**Terraform generation:**
```hcl
# User confirmed: 80, 443, 22

resource "huaweicloud_networking_secgroup_rule" "http" {
  security_group_id = huaweicloud_networking_secgroup.main.id
  direction         = "ingress"
  ethertype         = "IPv4"
  port_range_min    = 80
  port_range_max    = 80
  protocol          = "tcp"
  remote_ip_prefix  = "0.0.0.0/0"
}

# ... similar for 443, 22 (always include ethertype = "IPv4")

# Always include egress
resource "huaweicloud_networking_secgroup_rule" "egress" {
  security_group_id = huaweicloud_networking_secgroup.main.id
  direction         = "egress"
  ethertype         = "IPv4"
  remote_ip_prefix  = "0.0.0.0/0"
}
```

**Forbidden:**
- ❌ Using only egress rule without ingress rules
- ❌ Using hardcoded default ports without asking user
- ❌ Generating rules that don't match user confirmation

### 4.4 Verify resource availability BEFORE generating any code

**This step is mandatory and must never be skipped. A failed query is not a license to proceed — it is a blocker that must be resolved.**

Before writing a single line of Terraform, you MUST verify every resource specification in the confirmed plan against the target region. The target region is already known from the confirmed plan in step 4.3 — lacking the region means step 4.3 was incomplete and must be revisited. There is no excuse for not knowing which region you are deploying to.

1. **Step 1 — Read the target skill's SKILL.md first (DO NOT skip):** You MUST read the file `../huawei-cloud-computing-query/SKILL.md` before invoking the skill. This tells you the exact invocation format, required parameters, parameter format, and how to pass the target region. You cannot correctly invoke a skill you haven't read.
2. **Step 2 — Invoke the skill with confirmed parameters:** Only after reading the skill definition, invoke the `huawei-cloud-computing-query` skill with the exact parameters it requires, passing the target region from the confirmed plan in step 4.3. Confirm that each resource specification in the confirmed plan actually exists and is available in the target region. Any specification that cannot be confirmed MUST NOT appear in any .tf file.
3. **Cross-region assumptions are forbidden** — a resource available in region A does NOT imply availability in region B. Always re-query for the target region.

**Forbidden:**
- ❌ Invoking the `huawei-cloud-computing-query` skill without first reading its SKILL.md
- ❌ Guessing or fabricating parameters for skill invocation
- ❌ Proceeding to generate Terraform when a resource specification cannot be confirmed available
- ❌ Assuming resource availability carries over across regions

**If the query fails (environment error, network issue, SDK crash):**

- You MUST NOT proceed to generate Terraform. Stop immediately.
- Diagnose and fix the issue: invoke the `huawei-cloud-computing-query` skill's environment check, verify credentials, check network.
- Retry the query. If it fails again, fix and retry again.
- There is no "graceful degradation" — an unverified specification is a broken deployment waiting to happen.
- The only acceptable outcomes from this step are: (a) all specs confirmed available, or (b) a spec is confirmed unavailable and the user is asked to choose a different one.

**Why this matters:** Writing an unavailable flavor into `main.tf` produces a configuration that passes `terraform validate` but fails at `terraform apply` — the worst kind of error because it surfaces only after minutes of waiting.

**When modifying existing Terraform** (user asks to change a flavor, switch regions, use a different instance type, etc.): re-run the availability query for the new specification in the new region BEFORE editing any .tf file. Do not assume the previously-queried results still apply.

### 4.5 Generate Terraform after confirmation

**CRITICAL: Before generating, MUST read relevant reference documents from Section 8.1 mapping table.**

Once the user confirms the resource plan, generate the Terraform files following the required structure and style rules.

See `reference/terraform-generation-guide.md` for detailed file structure and content rules.

**Critical:** Generate all required files (providers.tf, variables.tf, main.tf, terraform.tfvars, README.md) and verify they exist before proceeding.

### 4.6 Verify credentials configuration

Before proceeding to validation, verify that Huawei Cloud credentials are configured via environment variables.

See `reference/guardrails.md` for rules about AK/SK handling.

### 4.6.1 Configure Huawei Cloud mirror for provider download

**Before running terraform init, configure the Huawei Cloud mirror to avoid slow downloads from the official Terraform registry.**
**Do NOT attempt to download from official registry first. Always use Huawei Cloud mirror.**

**Steps:**
1. Check if local provider cache exists (see validation-workflow.md for locations)
2. If cache exists and version >= 1.90.0, skip download
3. If download needed, create `.tfrc` file in the project directory:
   ```hcl
   provider_installation {
     network_mirror {
       url = "https://mirrors.huaweicloud.com/terraform/"
       include = ["registry.terraform.io/huaweicloud/*"]
     }
   }
   ```
4. Set `TF_CLI_CONFIG_FILE` environment variable to the `.tfrc` file path
5. **Every `terraform init` command MUST include `TF_CLI_CONFIG_FILE` in the same command line. Bare `terraform init` without the env var is FORBIDDEN.** Example:
   ```bash
   export TF_CLI_CONFIG_FILE="/path/to/project/.tfrc" && terraform init -upgrade
   ```

### 4.7 Validate and fix the generated configuration

Run validation in order: `terraform fmt -recursive` → `terraform init` → `terraform validate` → `terraform plan`

If any step fails, inspect the error, fix the configuration, and retry until `terraform plan` succeeds.

See `reference/validation-workflow.md` for detailed validation steps.

### 4.8 Display cost estimation (CRITICAL — MUST NOT SKIP)

**This step is MANDATORY and MUST be executed immediately after `terraform plan` succeeds, BEFORE any confirmation dialog or `terraform apply`. Skipping this step is a CRITICAL violation.**

**Cost display format (fill with actual resources from the plan):**
```
💰 费用预估

即将创建的资源：
- [资源类型] ([规格]): [预估费用]
- [资源类型] ([规格]): [预估费用]
- ...

预估合计: [总费用]

📌 华为云价格计算器: https://www.huaweicloud.com/pricing.html#/calculator
```

**Required elements (ALL must be present):**
- Resource list with specifications (from confirmed plan)
- Estimated monthly cost per resource (range is acceptable)
- Total estimated cost
- Link to Huawei Cloud pricing calculator (fixed URL)

**If you cannot estimate a cost:** still list the resource with "费用请参考价格计算器" — do NOT omit the resource from the list.

**Verification:** Before proceeding to step 4.9, confirm that you have output ALL required elements above. If any element is missing, stop and add it.

### 4.9 Execute terraform apply with user confirmation

After cost estimation is displayed, popup a confirmation dialog for user confirmation before executing apply.

See `reference/guardrails.md` for rules about user confirmation workflow.

### 4.10 Apply error repair loop

If `terraform apply` fails, inspect the error, fix the configuration, re-run `terraform plan`, and re-execute `terraform apply`. Repeat until successful.

### 4.11 Post-apply resource verification

After `terraform apply` succeeds, verify that deployed resources match the confirmed plan. If discrepancies found, report and fix them.

## 5. Guardrails

See `reference/guardrails.md` for detailed guardrail rules.

Key principles:
- Do not fabricate specifications, prices, or resource facts
- Execute terraform apply with explicit user confirmation
- Do not request sensitive information
- Do not invoke any referenced skill without first reading that skill's SKILL.md file

## 6. Terraform Generation Rules

After the user confirms the resource plan, generate Terraform that is minimal, valid, and aligned with the confirmed solution.

See `reference/terraform-generation-guide.md` for detailed guidance on file structure, content rules, data source usage, and variable design.

Core principles:
1. Start from the confirmed resource plan
2. Follow the Minimum Viable Configuration principle
3. Prefer Terraform validity over unnecessary flexibility
4. Use existing package references when relevant

## 7. Environment Preparation and Validation

See `reference/validation-workflow.md` for detailed guidance on ensuring Terraform availability, provider download **(from Huawei Cloud mirror)**, validation order, authentication, and repair loop.

## 8. Reference Usage and Template Guidance

Use the reference materials, templates, examples, and helper utilities in the skill package when relevant.

### 8.1 Use existing references when relevant

**MUST consult these references before generating:**

| Resource | Reference Document | Key Pattern |
|----------|-------------------|-------------|
| **通用规则** | `reference/guardrails.md` + `reference/terraform-generation-guide.md` | 密码自动生成、不向用户要敏感信息 |
| Security Group | `reference/VPC-best-practices/VPC-best-practices.md` → "Deploy Security Group" | `ethertype` is required |
| ECS with EIP | `reference/ECS-best-practices/Deploy-Instance-with-EIP-best-practices.md` | Use `huaweicloud_compute_eip_associate`, `public_ip = .address` |
| VPC/Subnet | `reference/VPC-best-practices/VPC-best-practices.md` → "Deploy Basic Network" | VPC/subnet structure |
| RDS | `reference/RDS-best-practices/RDS-best-practices.md` | Database + network config |

### 8.2 Use existing examples and templates as a starting point

If the package contains an example close to the target scenario, use it as a starting point. Preserve useful structure, adapt to the confirmed plan, and remove unneeded resources.

### 8.3 Match user goals to relevant references

Map business goals to service references (e.g., "deploy a website" → VPC + ECS + EIP, "managed database" → RDS + network).

### 8.4 Use references to improve, not to overbuild

Keep the final Terraform aligned with the user-confirmed plan and follow Minimum Viable Configuration principle.

### 8.5 Do not rely on templates blindly

Always verify that the template matches the confirmed plan and validate through the normal validation workflow.

## 9. Quality Checklist

Before finalizing, ensure:

- [ ] The generated Terraform matches the confirmed resource plan
- [ ] All 5 required files were generated and verified (providers.tf, variables.tf, main.tf, terraform.tfvars, README.md)
- [ ] No sensitive information was requested from user
- [ ] Validation reached `terraform plan`, or the blocker was clearly explained
- [ ] Cost estimation was displayed BEFORE user confirmation (step 4.8 — MUST NOT skip)
- [ ] Cost estimation includes ALL required elements: resource list, specifications, estimated cost per resource, total cost, pricing calculator link
- [ ] User was asked for confirmation via confirmation dialog before terraform apply
- [ ] `terraform apply` was executed only after explicit user confirmation (or user declined)