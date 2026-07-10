---
name: huawei-cloud-skill-creator
version: 1.0.0
description: |
  Invoke this skill to create, build, scaffold and package Huawei Cloud (华为云) agent skills.Triggers include: "创建华为云Skill","新建华为云Skill","华为云skill创建器","创建 Skill","新建 Skill","skill 创建器","create skill","build skill","new skill","skill creator","scaffold a Huawei Cloud skill","wrap CLI or OpenAPI into a skill","package cloud operations into a skill","帮我创建华为云Skill","帮我新建一个Skill","封装华为云CLI为Skill","华为云Skill脚手架".
trigger: create-skill, build-skill, new-skill, skill-creator, 创建-Skill, 新建-Skill, skill-创建器, scaffold-skill, huawei-cloud-skill
tags: [huawei-cloud, skill-creator, skill-development, cli, devops]
---

# Huawei Cloud Skill Creator

Create AI Agent Skills that comply with the Huawei Cloud specification, based on `skill-spec-generic.md`.

> **Specification:** [`references/skill-spec-generic.md`](references/skill-spec-generic.md) — The complete specification that all Skills must follow.

## Prerequisites

> First-time users should read [`references/cli-installation-guide.md`](references/cli-installation-guide.md).

- CLI installed with authentication configured
- AK/SK obtained via environment variables `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`
- IAM user has required permissions (see [`references/iam-policies.md`](references/iam-policies.md))
- Default region configured (e.g., `cn-north-4`)

## Core Commands

| Command | Description |
|---------|-------------|
| `hcloud ECS ListServers --cli-region=cn-north-4` | List ECS instances |
| `hcloud VPC ListVpcs --cli-region=cn-north-4` | List VPCs |
| `hcloud OBS ListBuckets --cli-region=cn-north-4` | List OBS buckets |
| `hcloud IAM ListUsers --cli-region=cn-north-4` | List IAM users |

## Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--cli-region` | Yes | Region ID | `cn-north-4` |
| `--project_id` | No | Project ID | `0a2663967980d2962f94c0120b96c98b` |
| `--limit` | No | Max items to return | `10` |
| `--offset` | No | Page offset | `0` |

## Overview

A Skill is an AI Agent's "domain expertise package" — a structured instruction folder that gives the Agent specialized knowledge and workflows for specific tasks. This Skill creates other Skills that comply with Huawei Cloud standards, ensuring each generated Skill has a complete directory structure, a well-formed SKILL.md, thorough reference docs, and reusable scripts.

## Design Principles

**Principle 1**: Each Skill should address a specific Agent use case. Aim for "usable when the Agent needs it", not for comprehensiveness.

**Principle 2**: A Skill should provide domain completeness. When a user needs capabilities in that domain, the Agent can complete the full workflow within the Skill without frequent context switching.

**Principle 3**: Skill content and Agent capabilities are collaborative. The Skill provides domain knowledge and workflows; the Agent handles reasoning and execution.

## Workflow

When a user requests a new Skill, follow these steps:

### Step 1: Requirements Analysis

1. Confirm the **Huawei Cloud service/product** to wrap (e.g., ECS, VPC, OBS, RDS)
2. Confirm the **functional scope** (management, diagnosis, deployment, monitoring, etc.)
3. Confirm the **CLI commands or API operations** involved
4. Confirm the **trigger scenarios** (when would an Agent use this Skill)

### Step 2: Naming & Directory

1. Generate the Skill name using the `{platform}-{product}-{function}` formula
   - platform is always `huawei-cloud`
   - product is the service abbreviation (ecs, vpc, obs, rds, iam, cce, etc.)
   - function is the capability description (manage, diagnosis-workflow, deploy, etc.)
   - Example: `huawei-cloud-ecs-diagnosis-workflow`

2. Determine the domain directory (compute / network / storage / database / security / monitoring / middleware / devtools / solution), see [`references/naming-conventions.md`](references/naming-conventions.md)

3. Create the directory structure:

```text
{domain}/{skill-name}/
├── SKILL.md                   # Required: YAML Frontmatter + Markdown instructions
├── references/                # Recommended: reference docs (loaded on demand)
│   ├── dataflow-diagram.md    # Required: Mermaid data flow diagram
│   ├── cli-installation-guide.md
│   ├── iam-policies.md
│   ├── verification-method.md
│   ├── acceptance-criteria.md
│   └── related-commands.md
├── scripts/                   # Recommended: executable scripts
│   └── {script-name}
├── templates/                 # Optional: config/template files
│   └── {template-name}
└── demo/                      # Optional: example data
    └── example.json
```

### Step 3: API Research

Use CLI help flags to discover available operations and parameter definitions (e.g., `ECS --help`, `ECS ListServers --help`).

```bash
# Test read-only operations (idempotent, safe to repeat)
hcloud ECS ListServers --cli-region={region}
```

If the CLI does not register the corresponding API, consult Huawei Cloud OpenAPI documentation for methods, paths, parameters, and permissions.

### Step 4: Generate Data Flow Diagram

Each Skill **must** include a Mermaid `flowchart` diagram in `references/dataflow-diagram.md` showing the complete workflow.

```bash
bash scripts/generate-dataflow-diagram.sh {skill-path} --output={skill-path}/references/dataflow-diagram.md
```

Or use [`templates/dataflow-diagram.md.template`](templates/dataflow-diagram.md.template) manually. Requirements: Mermaid flowchart syntax, input-to-output workflow, CLI operations subgraph, data sources subgraph, primary (`-->`) vs secondary (`-.->`) flow, legend + data flow description table (Step | Input | Process | Output).

### Step 5: Generate SKILL.md

Use [`templates/SKILL.md.template`](templates/SKILL.md.template). Must include:

**YAML Frontmatter:** `name` (required, follows naming formula), `description` (required, must include **"Triggers include:"** clause with all trigger scenarios for Agent routing), `tags` (3-8 items), `version` (SemVer).

**Body sections:**

| Section | Required | Content |
|---------|----------|---------|
| Overview | Yes | Background, Skill positioning |
| Prerequisites | Recommended | CLI install, AK/SK config, IAM permissions |
| Main Steps | Yes | Core workflow + code examples |
| Edge Cases | Recommended | Common errors, exception handling |
| Verification | Recommended | Success criteria for operations |
| References | Recommended | Links to references/ |

**Writing requirements:** Each step has clear CLI commands; key parameters have config notes; each operation notes required permissions; provide 3-5 typical usage examples; link to detailed docs in references/. CLI/scripts must **never embed AK/SK**; use env vars or placeholders like `{placeholder}`. Body should stay within 500 lines.

### Step 6: Generate references/

| File | Required | Content |
|------|----------|---------|
| `dataflow-diagram.md` | Yes | Mermaid data flow diagram |
| `cli-installation-guide.md` | Recommended | CLI installation and initialization |
| `iam-policies.md` | Yes | Required API Actions + minimum privilege policy JSON |
| `verification-method.md` | Recommended | Operation verification methods |
| `acceptance-criteria.md` | Recommended | Acceptance criteria |
| `related-commands.md` | As needed | Command quick reference |

Use [`templates/iam-policies.md.template`](templates/iam-policies.md.template) and [`templates/cli-installation-guide.md.template`](templates/cli-installation-guide.md.template) to generate. Each ref file focuses on one topic; add a brief header; large files (>300 lines) add a TOC; use `{placeholder}` for variables; code blocks must specify language type.

### Step 7: Generate scripts/ (As Needed)

**Script types:**

| Type | Purpose | Example |
|------|---------|---------|
| Analysis | Parse CLI output for automated analysis | `analyze-ingress-offline.sh` |
| Deployment | Orchestrate multi-step CLI operations | `deploy-folder.mjs` |
| Data processing | Process CLI JSON output | `get_logs.py` |
| Utility | Shared function reuse | `credentials.py`, `validation.py` |

**Script writing requirements:**
1. Use meaningful names, named by function
2. Shell scripts start with `#!/bin/bash`, Python with `#!/usr/bin/env python3`
3. Never hardcode AK/SK or secrets; use environment variables
4. Scripts should be compatible with multiple CLI versions
5. Provide parameter validation and error handling
6. Python script directories need `__init__.py`
7. Node.js scripts use `.mjs` extension with ES Modules

### Step 8: Generate templates/ and demo/ (As Needed)

- `templates/`: Config templates (IaC templates like Terraform/CloudFormation, API request JSON/YAML templates, report/notification Markdown templates)
- `demo/`: Example data (sample requests/responses, sample config files, test data)

### Step 9: Quality Validation

Use [`scripts/validate-skill.sh`](scripts/validate-skill.sh) to validate:

```bash
bash scripts/validate-skill.sh {skill-path}
```

Validation items are detailed in [`references/quality-checklist.md`](references/quality-checklist.md) and [`references/acceptance-criteria.md`](references/acceptance-criteria.md).

## Huawei Cloud CLI Command Format

```bash
# General format
hcloud ECS ListServers --cli-region=cn-north-4 --param1=value1 --param2=value2

# Concrete example
hcloud ECS ListServers --cli-region=cn-north-4

# Idempotent operations (safe to repeat)
hcloud ECS ShowServer --cli-region=cn-north-4 --server_id={instance_id}

# Nested parameters
hcloud ECS CreateServers --cli-region=cn-north-4 --os-start.servers.1.id={id1}
```

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Uppercase PascalCase | `ECS`, `VPC`, `IAM` |
| Operation name | PascalCase | `ListServers`, `ShowServer` |
| Region param | `--cli-region=<value>` | `--cli-region=cn-north-4` |
| Simple param | `--key=value` | `--server_id=xxx` |
| Index param | `--key.1=value1` | `--servers.1.id=xxx` |
| Nested param | `--key.sub_key=value` | `--config.protocol=vnc` |

## Security Operations

**Must follow:**
- Secrets (AK/SK) obtained via environment variables, never as plaintext parameters
- Confirm user intent before create/update/delete operations
- Prefer read-only queries (List/Describe/Get) to verify environment state
- Use dry-run mode (`--dry-run`) before high-risk operations

**Must avoid:**
- Exposing sensitive credentials in plaintext commands
- Executing destructive operations without confirmation
- Using deprecated API versions
- Ignoring error codes and return status

## User-Agent Identification

Add User-Agent identification in CLI calls within generated Skills for platform usage tracking:

```bash
# If CLI supports --user-agent parameter
hcloud ECS ListServers --cli-region=cn-north-4 --user-agent HuaweiCloud-Agent-Skills

# If CLI supports environment variable
export HCLOUD_USER_AGENT=HuaweiCloud-Agent-Skills
```

## Authentication & Security

### Authentication Methods

| Method | Use case | Recommended approach |
|--------|----------|---------------------|
| AK/SK env vars | Development | Set `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY` env vars |
| Temporary token | Production | Use STS temporary AK/SK + SecurityToken |
| IAM role | Cloud runtime | Bind IAM role for automatic permission acquisition |

### CLI Configuration

```bash
# Set default region via environment variable
export HUAWEI_REGION=cn-north-4
```

> **Security reminder:** Never hardcode AK/SK in scripts. Use environment variables or IAM roles. Do not pass plaintext credentials via CLI configuration commands.

### Permission Policy Requirements

Each generated Skill's `references/iam-policies.md` must:
1. Define required permissions (list query and mutation operations separately)
2. Provide minimum privilege policy JSON
3. Mark operations requiring MFA or elevated security

## Version Management

Follow SemVer (`MAJOR.MINOR.PATCH`) in Frontmatter `version` field. Branch strategy: `main` (stable), `preview` (beta), `{skill-name}-{version}` (release snapshot).

### Installation

```bash
npx skills add https://gitcode.com/developer-skill/developer-skill.git --skill {skill-name}
```

## Development Workflow

**Process:** Requirements → Draft → Test cases → Run with/without-skill in parallel → Assertions → Score → User review → Improve → Repeat.

**Iteration:** Re-run all tests after each improvement; track version with iteration markers; stop when feedback is satisfied; extract repetitive work into scripts/.

**Release:** Merge to `main` → Update version → Run `validate-skill.sh` → Tag and publish.

**Deprecation:** Mark deprecated APIs in SKILL.md; declare `deprecated` in description; provide migration guidance.

## Testing & Evaluation

| Type | Method | Goal |
|------|--------|------|
| Structural | Directory inspection | Frontmatter and directory structure |
| Functional | Run test cases | Verify functional correctness |
| Comparison | with/without-skill | Quantify Skill value-add |
| Regression | Cross-iteration comparison | Ensure no regressions |
| Trigger | trigger eval set | Optimize description accuracy |

Metrics: pass_rate, time_seconds, tokens, delta (with/without difference).

## Contributing Guide

Each PR addresses one issue; title format: `[type] description`; run `validate-skill.sh` before submitting; update version number. Labels: `bug`, `feature`, `documentation`, `security`, `question`.

## Data Flow Diagram

This Skill's own data flow diagram, showing how a Skill creation request flows through the workflow:

```mermaid
flowchart TD
  INPUT([/"User: Create a Huawei Cloud Skill"/])
  STEP1["Step 1: Requirements Analysis"]
  STEP2["Step 2: Naming & Directory"]
  STEP3["Step 3: API Research"]
  STEP4["Step 4: Data Flow Diagram"]
  STEP5["Step 5: Generate SKILL.md"]
  STEP6["Step 6: Generate references/"]
  STEP7["Step 7: Generate scripts/"]
  STEP8["Step 8: Generate templates/ & demo/"]
  STEP9["Step 9: Quality Validation"]
  OUTPUT([/"Complete Skill Package"/])

  subgraph CLI_OPS["CLI Operations"]
    CLI_OP1["hcloud ECS ListServers --cli-region={region}"]
    CLI_OP2["hcloud ECS ShowServer --cli-region={region}"]
    CLI_OP3["hcloud VPC ListVpcs --cli-region={region}"]
  end

  subgraph DATA["Data Sources"]
    ENV[/"Environment Variables\nHUAWEI_ACCESS_KEY, HUAWEI_SECRET_KEY, HUAWEI_REGION"/]
    REFS["references/\nskill-spec-generic.md, naming-conventions.md"]
    TEMPLATES["templates/\nSKILL.md.template, iam-policies.md.template"]
    SCRIPTS["scripts/\ngenerate-dataflow-diagram.sh, validate-skill.sh"]
  end

  INPUT --> STEP1
  STEP1 --> STEP2
  STEP2 --> STEP3
  STEP3 --> STEP4
  STEP4 --> STEP5
  STEP5 --> STEP6
  STEP6 --> STEP7
  STEP7 --> STEP8
  STEP8 --> STEP9
  STEP9 --> OUTPUT

  ENV -.-> STEP1
  REFS -.-> STEP2
  TEMPLATES -.-> STEP5
  SCRIPTS -.-> STEP4
  SCRIPTS -.-> STEP9

  STEP3 --> CLI_OPS
  CLI_OP1 -.-> STEP3
  CLI_OP2 -.-> STEP3
  CLI_OP3 -.-> STEP5
```

### Data Flow Description

| Step | Input | Process | Output |
|------|-------|---------|--------|
| 1. Requirements Analysis | User request + env config | Confirm service, scope, triggers | Structured requirements |
| 2. Naming & Directory | Requirements + naming conventions | Generate name, create directory structure | Skill directory path |
| 3. API Research | Directory + CLI access | Discover operations, test read-only commands | API operation list |
| 4. Data Flow Diagram | Workflow steps + CLI operations | Generate Mermaid diagram from template | `references/dataflow-diagram.md` |
| 5. Generate SKILL.md | API list + templates | Fill SKILL.md.template with service data | `SKILL.md` |
| 6. Generate references/ | SKILL.md + API data | Create iam-policies, cli-guide, etc. | `references/` directory |
| 7. Generate scripts/ | Workflow requirements | Create analysis/deployment scripts | `scripts/` directory |
| 8. Generate templates/ & demo/ | Config patterns | Create IaC/API templates + examples | `templates/` + `demo/` |
| 9. Quality Validation | Complete skill directory | Run validate-skill.sh | Validation report |

## Typical Use Cases

**ECS Management Skill:** User requests ECS management → confirm scope (query, create, start/stop, delete) → name: `huawei-cloud-ecs-manage` → domain: `compute` → research CLI operations → generate data flow diagram → generate full directory → validate.

**OBS Diagnosis Skill:** User requests OBS diagnosis → confirm scope (bucket status, access logs, capacity) → name: `huawei-cloud-obs-diagnosis-workflow` → domain: `storage` → research → generate → validate.

**VPC Management Skill:** User requests VPC management → confirm scope (VPC/subnet/security group) → name: `huawei-cloud-vpc-manage` → domain: `network` → research → generate → validate.

## Key Principles

- **Spec-first** — All generated Skills must comply with `references/skill-spec-generic.md`
- **Description drives triggers** — `description` must include a `"Triggers include:"` clause with all trigger phrases for accurate Agent routing
- **Security first** — Never hardcode AK/SK, confirm before write operations, dry-run for high-risk
- **Domain completeness** — Complete full workflow within the Skill, minimal context switching
- **Least privilege** — iam-policies.md provides minimum privilege policy JSON, query/mutation listed separately, MFA noted
- **Idempotent preferred** — Prefer List/Show/Get read-only operations for state verification
- **User-Agent** — Add User-Agent identification in CLI calls for tracking
- **Version management** — Follow SemVer, recorded in Frontmatter version field
- **Data flow diagram** — Every Skill must include a Mermaid data flow diagram in `references/dataflow-diagram.md` showing the complete workflow

## References

- [`references/skill-spec-generic.md`](references/skill-spec-generic.md) — Complete specification
- [`references/naming-conventions.md`](references/naming-conventions.md) — Naming conventions quick reference
- [`references/quality-checklist.md`](references/quality-checklist.md) — Quality checklist
- [`references/acceptance-criteria.md`](references/acceptance-criteria.md) — Acceptance criteria
- [`references/verification-method.md`](references/verification-method.md) — Verification methods
- [`references/related-commands.md`](references/related-commands.md) — Command quick reference
- [`references/dataflow-diagram.md`](references/dataflow-diagram.md) — Data flow diagram (this Skill's own diagram)
- [`templates/dataflow-diagram.md.template`](templates/dataflow-diagram.md.template) — Data flow diagram template
