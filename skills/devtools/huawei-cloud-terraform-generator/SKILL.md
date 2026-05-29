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
5. ensure Terraform is installed
6. generate Terraform configuration files
7. run validation steps and fix generation issues until `terraform plan` succeeds
8. ask user for confirmation and execute `terraform apply` if approved

This skill provides an interactive workflow where the agent guides the user through credential configuration, validates the plan, and executes apply upon explicit user confirmation.

## 2. Prerequisites

Before using this skill, ensure the following are available:

1. **Terraform** — installed in PATH or auto-installable (see validation-workflow.md)
2. **Provider download source** — the Huawei Cloud mirror must be reachable (see validation-workflow.md)
3. **Target region** — the deployment region (e.g. cn-north-4, cn-south-1) must be identified

## 3. Parameter Confirmation

Before generating Terraform, propose a concrete resource plan for the user to confirm. The plan should include:

- recommended resource specifications
- available candidate options when applicable
- whether to create new resources or reuse existing ones
- pricing information only when obtained from a reliable source

Important rules:

- recommended specifications, models, and prices must not be fabricated
- they must come from a reliable source, such as a trusted resource lookup channel or explicit user input
- users should not be expected to know exact product models or specification names in advance
- when exact values are not yet confirmed, present them as pending choices rather than pretending they are validated
- do not ask user anything about AK/SK configuration

Do not ask the user to provide every parameter manually. Instead:

1. infer the likely architecture from the user's goal
2. propose a concrete plan with recommended defaults
3. confirm only the small number of decisions that materially affect correctness, cost, or architecture

Users should mainly confirm a proposed solution, not build the full parameter set themselves.

## 4. Workflow

This skill works in nine phases:

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

### 4.4 Generate Terraform after confirmation

Once the user confirms the resource plan, generate the Terraform files following the required structure and style rules.

**Required files (all must be generated):**
- `providers.tf`
- `variables.tf`
- `main.tf`
- `terraform.tfvars`
- `README.md`

**Critical:**
- Generate all 5 required files before reporting completion
- Verify each file exists on disk after writing
- Only report "Terraform files generated successfully" after all files are confirmed to exist
- If any file fails to generate, report the specific file that failed and do not proceed to step 5

See `reference/terraform-generation-guide.md` for detailed file structure and content rules.

### 4.5 Verify credentials configuration

Before proceeding to validation, verify that Huawei Cloud credentials are configured via environment variables:
- **Do NOT ask or guide the user to configure AK/SK in environment variables**
- Assume the user has already configured credentials appropriately
- Proceed directly to validation without prompting about credential setup

### 4.6 Validate and fix the generated configuration

Run validation directly:
- `terraform fmt -recursive`
- `terraform init`
- `terraform validate`
- `terraform plan`

If any step fails:
- inspect the exact error
- identify the real cause
- fix the generated configuration or required inputs
- retry until `terraform plan` succeeds

See `reference/validation-workflow.md` for detailed validation steps.

### 4.7 Execute terraform apply with user confirmation

After `terraform plan` succeeds:
- Show the plan output to the user
- **Do NOT mention or reference AK/SK in the plan output summary**
- Popup a confirmation dialog for user to confirm execution
- If user confirms: execute `terraform apply`
- If user declines: stop and inform the user they can manually run apply later
- Report the apply result to the user

### 4.8 Apply error repair loop

If `terraform apply` fails:
- Inspect the exact error output
- Identify the root cause
- Fix the Terraform configuration or inputs accordingly
- Re-run `terraform plan` to validate the fix
- Re-execute `terraform apply` after plan succeeds
- Repeat until `terraform apply` completes successfully
- Do not stop at the first apply failure; continue fixing and retrying

### 4.9 Post-apply resource verification

After `terraform apply` succeeds:
- Verify that the deployed cloud resources match the resource plan confirmed by the user
- Check key resource attributes (types, specifications, names, counts, dependencies) against the confirmed plan
- If discrepancies are found between deployed resources and the confirmed plan:
  - Report the discrepancies to the user
  - Propose and apply fixes to align the deployment with the confirmed plan
  - Re-run apply if needed and re-verify
- Confirm to the user that the deployed resources are consistent with the confirmed plan

## 5. Guardrails

See `reference/guardrails.md` for detailed guardrail rules.

Key principles:

- Do not fabricate specifications, prices, or resource facts
- Prefer recommended defaults, but do not fabricate validated facts
- Execute terraform apply with explicit user confirmation
- Do not generate outputs
- Validate security group port numbers (no port 0)
- Do not request sensitive information
- Do not guide AK/SK environment variable configuration

## 6. Terraform Generation Rules

After the user confirms the resource plan, generate Terraform that is minimal, valid, and aligned with the confirmed solution.

### 6.1 Core generation principles

Follow these principles when generating Terraform:

1. Start from the confirmed resource plan
2. Follow the Minimum Viable Configuration principle
3. Prefer Terraform validity over unnecessary flexibility
4. Use existing package references when relevant

### 6.2 File structure and content

See `reference/terraform-generation-guide.md` for detailed guidance on:
- Fixed file structure
- providers.tf requirements
- variables.tf requirements
- main.tf structure
- terraform.tfvars content
- README.md content
- Data source usage rules
- Variables vs data sources

## 7. Environment Preparation and Validation

See `reference/validation-workflow.md` for detailed guidance on:
- Ensuring Terraform is available
- Checking local provider cache version
- Downloading provider from Huawei Cloud mirror
- Handling provider download failure
- Validation order
- Authentication handling
- Repair loop
- Cleanup

## 8. Reference Usage and Template Guidance

Use the reference materials, templates, examples, and helper utilities already included in the skill package when they are relevant to the current scenario.

### 8.1 Use existing references when relevant

If the package contains service-specific reference documents, consult them when the user's request involves that service.

These references may provide:
- recommended architecture patterns
- required resources
- dependency design
- common parameter structures
- service-specific best practices

Typical services may include: VPC, ECS, RDS, CCE, ELB, OBS, EVS, NAT, VPN and other Huawei Cloud services covered by the package.

### 8.2 Use existing examples and templates as a starting point

If the package already contains an example or template close to the user's target scenario, use it as a starting point instead of inventing structure.

Example:
- `assets/vpc/basic` may serve as a complete working example for a basic VPC scenario

When using an existing example or template:
- preserve the useful structure
- adapt it to the confirmed plan
- remove resources that are not needed
- avoid copying unrelated complexity

### 8.3 Match user goals to the most relevant references

When the user describes a business goal instead of explicit resource names, map the goal to the most relevant service references.

Examples:
- "deploy a website" may map to VPC + ECS + EIP, and possibly ELB or OBS
- "create a managed database" may map to RDS with related network resources
- "build a Kubernetes environment" may map to CCE with required networking and node configuration

### 8.4 Use references to improve, not to overbuild

References and templates are guides, not mandatory full blueprints.

When using them:
- keep the final Terraform aligned with the user-confirmed plan
- follow the Minimum Viable Configuration principle
- avoid adding optional resources unless the user actually needs them
- prefer simpler configurations when they are sufficient

### 8.5 Do not rely on templates blindly

A matching template or example does not guarantee correctness for the current request.

Always:
- check whether the template matches the confirmed plan
- verify that specifications and dependencies are still appropriate
- adjust variables, data sources, and resource arguments as needed
- validate the final generated Terraform through the normal validation workflow

## 9. Quality Checklist

Before finalizing, ensure:

- [ ] The generated Terraform matches the confirmed resource plan
- [ ] All 5 required files were generated and verified (providers.tf, variables.tf, main.tf, terraform.tfvars, README.md)
- [ ] No sensitive information was requested from user
- [ ] terraform.tfvars does not contain access_key or secret_key
- [ ] Recommended values were not fabricated
- [ ] Queryable cloud facts use Terraform data sources where supported
- [ ] `variables.tf` includes `region`
- [ ] No `outputs.tf` or output blocks were generated
- [ ] Security group rules do not use port 0
- [ ] Validation reached `terraform plan`, or the blocker was clearly explained
- [ ] User was asked for confirmation via confirmation dialog before terraform apply
- [ ] `terraform apply` was executed only after explicit user confirmation (or user declined)
- [ ] Network reachability was checked before provider installation when needed
- [ ] Terraform CLI provider installation behavior was configured appropriately when using a mirror or local provider source
