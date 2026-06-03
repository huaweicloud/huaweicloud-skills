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

### 4.4 Generate Terraform after confirmation

Once the user confirms the resource plan, generate the Terraform files following the required structure and style rules.

See `reference/terraform-generation-guide.md` for detailed file structure and content rules.

**Critical:** Generate all required files (providers.tf, variables.tf, main.tf, terraform.tfvars, README.md) and verify they exist before proceeding.

### 4.5 Verify credentials configuration

Before proceeding to validation, verify that Huawei Cloud credentials are configured via environment variables.

See `reference/guardrails.md` for rules about AK/SK handling.

### 4.6 Validate and fix the generated configuration

Run validation in order: `terraform fmt -recursive` → `terraform init` → `terraform validate` → `terraform plan`

If any step fails, inspect the error, fix the configuration, and retry until `terraform plan` succeeds.

See `reference/validation-workflow.md` for detailed validation steps.

### 4.7 Execute terraform apply with user confirmation

After `terraform plan` succeeds, show the plan output to user and popup a confirmation dialog before executing `terraform apply`.

See `reference/guardrails.md` for rules about user confirmation workflow.

### 4.8 Apply error repair loop

If `terraform apply` fails, inspect the error, fix the configuration, re-run `terraform plan`, and re-execute `terraform apply`. Repeat until successful.

### 4.9 Post-apply resource verification

After `terraform apply` succeeds, verify that deployed resources match the confirmed plan. If discrepancies found, report and fix them.

## 5. Guardrails

See `reference/guardrails.md` for detailed guardrail rules.

Key principles:
- Do not fabricate specifications, prices, or resource facts
- Execute terraform apply with explicit user confirmation
- Do not request sensitive information

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

Consult service-specific reference documents (VPC, ECS, RDS, CCE, ELB, OBS, etc.) when the user's request involves that service.

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
- [ ] User was asked for confirmation via confirmation dialog before terraform apply
- [ ] `terraform apply` was executed only after explicit user confirmation (or user declined)
