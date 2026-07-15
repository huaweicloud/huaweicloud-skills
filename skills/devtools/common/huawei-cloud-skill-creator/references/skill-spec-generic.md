# Skill Development Specification & Guide (Generic v1)

> v1.0.0 | Synthesized from Codex Skill Creator, Community Skill Creator, Feishu lark-skill-maker, and Huawei Cloud Skills specifications.

---

## 1. Overview

A Skill is an AI Agent's "domain expertise package" — a structured instruction folder that gives the Agent specialized knowledge and workflows for specific tasks.

This specification defines a universal Skill development standard covering directory structure, naming conventions, SKILL.md authoring, reference doc organization, script development, CLI usage, authentication & security, version management, testing & evaluation, and more.

---

## 2. Directory Structure & Naming

### 2.1 Repository Organization

Skills are organized by domain/service in the repository:

```
skills-repo/
├── README.md
├── skills/
│   ├── compute/          # Compute
│   │   ├── myservice-manage/
│   │   └── myservice-diagnosis/
│   ├── network/          # Network
│   ├── storage/          # Storage
│   ├── database/         # Database
│   ├── security/         # Security
│   ├── monitoring/       # Monitoring
│   ├── middleware/       # Middleware
│   ├── devtools/         # Dev tools
│       ├── cli/
│       └── common/
│   └── solution/         # Solutions
```

### 2.2 Skill Internal Directory Structure

```
skill-name/
├── SKILL.md                   # Required: YAML Frontmatter + Markdown instructions
├── i18n/                      # Recommended: internationalization
│   └── zh-CN/                 # Recommended: Simplified Chinese (default)
│       └── SKILL_CN.md        # Recommended: Chinese version of SKILL.md
├── references/                # Recommended: reference docs (loaded on demand)
│   ├── dataflow-diagram.md    # Required: Mermaid data flow diagram
│   ├── cli-installation-guide.md   # CLI install & config guide
│   ├── iam-policies.md             # Permission policy docs
│   ├── verification-method.md      # Verification methods
│   ├── acceptance-criteria.md      # Acceptance criteria
│   └── related-commands.md         # Command quick reference
├── scripts/                   # Recommended: executable scripts
│   ├── analyze.py
│   └── deploy.sh
├── templates/                 # Optional: config/template files
│   ├── config.yaml
│   └── report.md
└── demo/                      # Optional: example data
    └── example.json
```

### 2.3 Naming Conventions

| Level | Rule | Example | Description |
|-------|------|---------|-------------|
| Domain directory | Singular noun | `compute`, `storage`, `network` | Group by service/product domain |
| Service directory | Service/product abbreviation | `ecs`, `vpc`, `obs` | Sub-service under domain |
| Skill name | `{platform}-{product}-{function}` | `mycloud-ecs-diagnosis-workflow` | Platform + product + function |
| Reference file | kebab-case | `cli-installation-guide.md` | Descriptive naming |
| Script file | kebab-case | `analyze-ingress.sh` | Verb + noun |

**Skill naming formula:**

```
{platform}-{product}-{function}
```

**Examples:**
- `mycloud-ecs-diagnosis-workflow` — ECS diagnosis workflow
- `mycloud-vpc-manage` — VPC management
- `mycloud-obs-manage` — OBS storage management
- `mycloud-cli-guidance` — CLI usage guide
- `mycloud-rds-copilot` — RDS ops copilot

### 2.4 Skill Design Principles

**Principle 1**: Each Skill should address a specific Agent use case. Aim for "usable when the Agent needs it", not for comprehensiveness.

**Principle 2**: A Skill should provide domain completeness. When a user needs capabilities in that domain, the Agent can complete the full workflow within the Skill without frequent context switching.

**Principle 3**: Skill content and Agent capabilities are collaborative. The Skill provides domain knowledge and workflows; the Agent handles reasoning and execution.

---

## 3. SKILL.md Specification

SKILL.md is the Skill's core file, structured as **YAML Frontmatter + Markdown body**. Body should stay within 500 lines.

### 3.1 YAML Frontmatter Specification

SKILL.md begins with `---`-wrapped YAML metadata:

```yaml
---
name: mycloud-ecs-diagnosis-workflow
description: |
  1. What the Skill does (functional scope)
  2. When the Skill is triggered (trigger conditions)
  3. What value the Skill provides (value description)
tags: [cloud, ecs, diagnostics, troubleshooting, devops]
version: 1.0.0
---
```

#### 3.1.1 Frontmatter Field Descriptions

| Field | Required | Type | Description | Example |
|-------|----------|------|-------------|---------|
| `name` | Yes | string | Unique Skill identifier | `mycloud-ecs-diagnosis` |
| `description` | Yes | string | Functional scope + trigger conditions + value description | See below |
| `tags` | Recommended | string[] | Classification tags for search, 3-8 recommended | `[cloud, ecs, diagnostics]` |
| `version` | Recommended | string | SemVer version number | `2.0.0` |

#### 3.1.2 Description Authoring Specification

Use a structured format with numbered points:

1. **Functional scope** — What this Skill is responsible for
2. **Trigger conditions** — When this Skill is triggered
3. **Value description** — What the user gains from using it
4. **Usage pattern** — Which CLI/API operations are involved
5. **Prerequisites** — Conditions that must be met before use

### 3.2 Body Structure

SKILL.md body is organized as follows:

| Section | Content | Required |
|---------|---------|----------|
| Overview | Background, Skill positioning | Yes |
| Prerequisites | CLI install status, IAM permissions, env vars | Recommended |
| Main Steps | Core workflow with code examples | Yes |
| Edge Cases | Common errors, exception handling | Recommended |
| Verification | How to verify operation success | Recommended |
| References | Links to more detailed docs in references/ | Recommended |
| Script Usage | Documentation for scripts/ | As needed |

#### 3.2.1 Body Authoring Requirements

**Content requirements:**
- Each step has clear instructions
- Key parameters have configuration notes
- Each operation notes required permissions
- Provide 3-5 typical usage examples
- Link to detailed docs in references/

**Security requirements:**
- CLI parameters/scripts must **never embed AK/SK or other secrets directly**
- Secrets are obtained via environment variables or secure configuration
- Account info in examples uses placeholders

### 3.3 Quality Gates

| Check | Required | Description |
|-------|----------|-------------|
| SKILL.md format complete | Yes | YAML + Markdown structure correct |
| SKILL.md Frontmatter complete | Yes | name, description required |
| references/ links valid | Yes | Referenced files exist |
| Examples/commands runnable | Recommended | Code example syntax correct |

---

## 4. Reference Document Specification (references/)

### 4.1 Standard Reference Files

| Filename | Purpose | Example Content |
|----------|---------|-----------------|
| `dataflow-diagram.md` | Mermaid data flow diagram | Workflow visualization with Mermaid flowchart |
| `cli-installation-guide.md` | CLI tool install & init | Install steps, config methods |
| `iam-policies.md` | Permission policy docs | Required API Actions, policy JSON |
| `verification-method.md` | Operation verification methods | Success/failure criteria |
| `acceptance-criteria.md` | Acceptance criteria | Task completion conditions |
| `related-commands.md` | Command quick reference | Command cheat sheet |

### 4.2 Extended Reference Files

| Filename | Purpose | Use Case |
|----------|---------|----------|
| `related-commands.md` / `related-apis.md` | Command/API quick reference | Many operations to document |
| `generic-diagnostics-workflow.md` | Generic diagnostics workflow | Multi-step diagnosis scenarios |
| `service-catalog.md` | Service catalog | Multi-service interactions |
| `parameter-format.md` | Parameter format specification | Special parameter format requirements |
| `common-workflows.md` | Common workflows | Different operation modes |
| `cli-troubleshooting.md` | CLI troubleshooting | Known CLI issues |
| `region-and-spec.md` | Region/spec information | Region/spec-dependent behavior |
| `search-commands.md` | Search command guide | Quick command lookup |

### 4.3 Reference File Authoring Requirements

1. Each ref file focuses on one problem, no mixed content
2. Add a brief header explaining when to read the file
3. Large files (>300 lines) add a TOC at the top
4. Keep reference info consistent with platform docs
5. Use curly braces for placeholders (e.g., `{instance_id}`)
6. Code blocks must specify language type

---

## 5. Data Flow Diagram Specification

### 5.1 Overview

Every Skill **must** include a data flow diagram that visualises how data moves through the Skill's workflow. The diagram provides an at-a-glance understanding of the Skill's operation, inputs, outputs, and data dependencies.

### 5.2 Format

- Use **Mermaid** `flowchart` syntax (widely supported in Markdown renderers, GitHub, GitLab, etc.)
- Save as `references/dataflow-diagram.md`

### 5.3 Diagram Structure Requirements

| Element | Required | Description |
|---------|----------|-------------|
| Start/End nodes | Yes | Asymmetric rectangles `([/ /])` showing user input and final output |
| Process steps | Yes | Rectangles `[ ]` for each workflow step |
| CLI Operations subgraph | Yes | Subgraph containing all CLI commands |
| Data Sources subgraph | Yes | Subgraph containing env vars, references, scripts |
| Primary flow arrows | Yes | `-->` for main data flow between steps |
| Secondary flow arrows | Recommended | `-.->` for reference/lookup data flow |
| Legend | Yes | Table explaining Mermaid symbols |
| Data Flow Description table | Yes | Step \| Input \| Process \| Output |

### 5.4 Example Diagram

```mermaid
flowchart TD
  INPUT([/"User Request"/]) --> STEP1["Step 1: Validate"]
  STEP1 --> STEP2["Step 2: Execute"]
  STEP2 --> STEP3["Step 3: Format"]
  STEP3 --> OUTPUT([/"Result"/])

  subgraph CLI["CLI Operations"]
    CLI1["hcloud SERVICE Operation1"]
    CLI2["hcloud SERVICE Operation2"]
  end

  subgraph DATA["Data Sources"]
    ENV[/"Environment Variables"/]
    REFS["references/"]
  end

  ENV -.-> STEP1
  REFS -.-> STEP2
  STEP1 --> CLI
  CLI1 -.-> STEP2
```

### 5.5 Generation

Use `scripts/generate-dataflow-diagram.sh` to auto-generate from SKILL.md:

```bash
bash scripts/generate-dataflow-diagram.sh {skill-path} --output={skill-path}/references/dataflow-diagram.md
```

Or use `templates/dataflow-diagram.md.template` to create manually.

---

## 6. Script Specification (scripts/)

### 5.1 Script Types

| Type | Purpose | Example |
|------|---------|---------|
| Analysis | Parse CLI output for automated analysis | `analyze-ingress-offline.sh` |
| Deployment | Orchestrate multi-step CLI operations | `deploy-folder.mjs` |
| Data processing | Process CLI JSON output | `get_logs.py` |
| Utility | Shared function reuse | `credentials.py`, `validation.py` |

### 5.2 Script Authoring Requirements

1. Use meaningful names, named by function
2. Shell scripts start with `#!/bin/bash`, Python with `#!/usr/bin/env python3`
3. Never hardcode AK/SK or secrets; use environment variables
4. Scripts should be compatible with multiple CLI versions
5. Provide parameter validation and error handling
6. Python script directories need `__init__.py`
7. Node.js scripts use `.mjs` extension with ES Modules

---

## 7. Templates & Examples (templates/ & demo/)

### 6.1 templates/

Stores configuration template files:
- Infrastructure as Code templates (Terraform/CloudFormation)
- API request JSON/YAML templates
- Report/notification Markdown templates

### 6.2 demo/

Stores example data files:
- Sample requests/responses
- Sample configuration files
- Test data

---

## 8. Internationalization Specification (i18n/)

### 8.1 Overview

Every Skill **should** include an `i18n/` directory for internationalization support. The default locale is Simplified Chinese (`zh-CN`).

### 8.2 Directory Structure

```
i18n/
├── zh-CN/                 # Required: Simplified Chinese (default)
│   └── SKILL_CN.md        # Required: Chinese version of SKILL.md
├── en-US/                 # Optional: American English
│   └── SKILL_EN.md
├── ja-JP/                 # Optional: Japanese
│   └── SKILL_JA.md
└── {locale}/              # Optional: Other locales
    └── SKILL_{LANG}.md
```

### 8.3 SKILL_CN.md Requirements

| Requirement | Description |
|-------------|-------------|
| YAML Frontmatter | Same structure as SKILL.md (name, description, tags, version) |
| description field | Must be written in Chinese, include Chinese trigger phrases (e.g., "触发场景包括:") |
| Body content | Translated to Simplified Chinese |
| CLI commands | Remain in English — do not translate commands, parameters, or code blocks |
| Technical terms | May retain English in parentheses (e.g., "弹性云服务器 (ECS)") |
| Line count | Body should stay within 500 lines (same as SKILL.md) |

### 8.4 Locale Naming Convention

| Locale | Directory | Filename | Language |
|--------|-----------|----------|----------|
| zh-CN | `i18n/zh-CN/` | `SKILL_CN.md` | Simplified Chinese |
| en-US | `i18n/en-US/` | `SKILL_EN.md` | American English |
| ja-JP | `i18n/ja-JP/` | `SKILL_JA.md` | Japanese |
| ko-KR | `i18n/ko-KR/` | `SKILL_KR.md` | Korean |

### 8.5 Quality Gates

| Check | Required | Description |
|-------|----------|-------------|
| i18n/ directory exists | Recommended | Internationalization directory present |
| zh-CN/ subdirectory exists | Recommended | Default Chinese locale present |
| SKILL_CN.md exists | Recommended | Chinese version of SKILL.md |
| SKILL_CN.md has YAML Frontmatter | Yes | Frontmatter structure matches SKILL.md |
| SKILL_CN.md description in Chinese | Yes | Description field uses Chinese text |
| SKILL_CN.md CLI commands in English | Recommended | Commands not translated |

---

## 9. CLI Usage Specification

### 9.1 General CLI Command Format

```bash
# General format
<cli-tool> <SERVICE> <Operation> --param1=value1 --param2=value2

# Concrete example
mytool ECS ListServers --region=cn-north-4

# Idempotent operations (safe to repeat)
mytool ECS ShowServer --server_id={instance_id}

# Nested parameters
mytool ECS StartInstance --os-start.servers.1.id={id1}
```

#### 9.1.1 Common Patterns

| Feature | Description | Example |
|---------|-------------|---------|
| Service name | Uppercase PascalCase | `ECS`, `VPC`, `IAM` |
| Operation name | PascalCase | `ListServers`, `ShowServer` |
| Region param | `--region=<value>` | `--region=cn-north-4` |
| Simple param | `--key=value` | `--server_id=xxx` |
| Index param | `--key.1=value1` | `--servers.1.id=xxx` |
| Nested param | `--key.sub_key=value` | `--config.protocol=vnc` |

### 9.2 Security Operations

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

### 9.3 Cost Confirmation

> **Important:** Skills that involve cloud resources (compute, storage, database, etc.) **must** include cost confirmation logic. Before executing any resource-mutating operation, the Agent must remind the user about potential costs and wait for explicit confirmation.

**Mandatory confirmation flow:**

1. Before executing any `Create*` / `Update*` / `Delete*` operation, display a cost reminder
2. Wait for explicit user confirmation (yes/no)
3. If the user declines or does not respond, **abort the operation immediately**
4. If the user confirms, proceed with the operation

**Cost reminder template:**

```
⚠️  Cost Notice: This operation will [create/update/delete] {RESOURCE_TYPE} resource(s)
    which may incur charges on your Huawei Cloud account.
    - Resource type: {RESOURCE_TYPE}
    - Billing model: {BILLING_MODEL} (e.g., pay-per-use, monthly subscription)
    - Estimated cost: {ESTIMATED_COST} (if known, otherwise "varies by specification")
    
    Do you want to proceed? (yes/no)
```

**Operations requiring cost confirmation:**
- `Create*` — Creating new resources (ECS, VPC, OBS, RDS, CCE, etc.)
- `Update*` — Modifying resource specifications (scale up, change flavor, etc.)
- `Delete*` — Deleting resources (may affect billing cycles)

**Operations exempt from cost confirmation:**
- `List*` / `Show*` / `Get*` — Read-only queries (no cost impact)
- `* --dry-run` — Dry-run mode (no actual resource change)

**SKILL.md requirement:** Every Skill that involves resource-mutating operations must include a `## Cost Confirmation` section documenting this flow.

### 9.4 User-Agent Identification

Add User-Agent identification in CLI calls for platform usage tracking:

```bash
# If CLI supports --user-agent parameter
mytool ECS ListServers --user-agent Platform-Agent-Skills

# If CLI supports environment variable
export CLI_USER_AGENT=Platform-Agent-Skills
```

---

## 10. Authentication & Security

### 10.1 Authentication Methods

| Method | Use Case | Recommended Approach |
|--------|----------|---------------------|
| AK/SK env vars | Development | `export ACCESS_KEY_ID=<AK>` |
| CLI config | Local use | `mytool configure set --access-key=AK --secret-key=SK` |
| Temporary token | Production | Use STS temporary AK/SK + SecurityToken |
| IAM role | Cloud runtime | Bind IAM role for automatic permission acquisition |

#### 10.1.1 CLI Configuration Flow

```bash
# View current config
mytool configure list

# Set AK/SK
mytool configure set --access-key={ACCESS_KEY} --secret-key={SECRET_KEY}

# Set default region
mytool configure set --region=cn-north-4

# Security reminder: never hardcode AK/SK in scripts
# Never do this:
# mytool configure set --access-key=AK...  # ❌ Do not do this
```

### 10.2 Permission Policy Documentation

Each Skill's `references/` should contain a permission policy document (`iam-policies.md`):

```markdown
# Permission Policies - {Service Name}

## Query Operations

| API Action | Description | Purpose |
|------------|-------------|---------|
| service:resources:get | Get resource details | Skill main workflow |
| service:resources:list | List resources | Resource filtering/selection |

## Mutation Operations

| API Action | Description | Purpose |
|------------|-------------|---------|
| service:resources:action | Execute operation | SSH/VNC operations |
| service:resources:delete | Delete resource | High-risk operation |

## Minimum Privilege Policy JSON

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "service:resources:get",
        "service:resources:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```
```

**Security requirements:**
1. Each Skill must define required permissions in `references/iam-policies.md`
2. Query and mutation operations listed separately
3. Provide minimum privilege policy JSON
4. Mark operations requiring MFA or elevated security

---

## 11. Version Management

### 11.1 Version Numbering

Follow SemVer: `MAJOR.MINOR.PATCH`

| Component | Meaning | When to Increment | Example |
|-----------|---------|-------------------|---------|
| MAJOR | Incompatible change | API version change, breaking update | `1.x.x` → `2.0.0` |
| MINOR | Backward-compatible feature | New capability, new operation | `2.0.x` → `2.1.0` |
| PATCH | Backward-compatible fix | Doc correction, bug fix | `2.1.0` → `2.1.1` |

Version is recorded in the SKILL.md YAML Frontmatter `version` field.

### 11.2 Branch Strategy

| Branch | Purpose | Description |
|--------|---------|-------------|
| `main` | Stable release | Tested and verified official version |
| `preview` | Preview/Beta | Early access to new features |
| `{skill-name}-{version}` | Version release | Specific version snapshot |
| `{skill-name}-{beta}` | Beta release | Beta version snapshot |

### 11.3 Installation

#### Via Package Manager

```bash
# Install a specific Skill
npx skills add https://gitcode.com/org/skills.git --skill skill-name

# Install all Skills
npx skills add https://gitcode.com/org/skills.git

# Install from a specific branch
npx skills add https://gitcode.com/org/skills/tree/preview --skill skill-name
```

#### Local Install

```bash
# Clone the repository
git clone https://gitcode.com/org/skills.git

# Add locally
npx skills add ./skills/skill-name
```

---

## 12. Contributing Guide

### 12.1 Issue Specification

| Label | Purpose | Description |
|-------|---------|-------------|
| `bug` | Bug report | Functional error, command failure |
| `feature` | Feature request | New Skill, capability extension |
| `documentation` | Doc improvement | SKILL.md improvement |
| `security` | Security issue | Permission, credential issues |
| `question` | Usage question | Usage inquiry |

**Bug report template:**
```markdown
## Bug Description
[Clear problem description]

## Environment
- Platform version:
- CLI version:
- Agent version:

## Steps to Reproduce
1. ...
2. ...
3. ...

## Expected Result
[Correct behavior]

## Actual Result
[Actual behavior]
```

### 12.2 Pull Request Specification

- Each PR addresses one issue only
- PR title format: `[type] description`
- Run validation tool before submitting
- Update the corresponding version number

### 12.3 Code Review

- Each submission needs at least one Reviewer
- Review focus: SKILL.md structure, command accuracy, permission completeness

---

## 13. Version Management Iteration

### 13.1 Version History

Record change history in the repository root or SKILL.md.

### 13.2 Release Process

1. Merge code to `main` branch
2. Update SKILL.md version number
3. Tag and publish

### 13.3 Deprecation Policy

- Deprecated API operations are marked in SKILL.md
- Deprecated Skills declare `deprecated` in description
- Provide migration guidance to the new version

---

## 14. Development Workflow

### 14.1 Full Development Process

```
Requirements → Draft → Create test cases →
Run with-skill / without-skill in parallel →
Compose assertions → Score →
User reviews output → Improve based on feedback → Repeat iteration
```

### 14.2 Iteration Principles

- Re-run all tests after each improvement
- Track version evolution with iteration markers (iteration-N)
- Stop when all user feedback is empty (satisfied) or no significant improvement remains
- Identify repetitive work from tests and extract into scripts/
- Read run logs, not just final output — identify patterns where the Agent wastes time

---

## 15. Testing & Evaluation

### 15.1 Test Types

| Type | Method | Goal |
|------|--------|------|
| Structural check | Directory inspection | Frontmatter and directory structure |
| Functional test | Run test cases | Verify functional correctness |
| Comparison test | with/without-skill | Quantify Skill value-add |
| Regression test | Cross-iteration comparison | Ensure improvements don't regress |
| Trigger test | trigger eval set | Optimize description accuracy |

### 15.2 Evaluation Metrics

| Metric | Description |
|--------|-------------|
| pass_rate | Assertion pass rate |
| time_seconds | Execution time |
| tokens | Token consumption |
| delta | with/without difference |

---

## 16. Quality Gates & Acceptance Criteria

| Check | Required | Description |
|-------|----------|-------------|
| SKILL.md Frontmatter | Yes | name, description required |
| i18n directory | Recommended | `i18n/zh-CN/SKILL_CN.md` exists with valid Frontmatter |
| Data flow diagram | Yes | `references/dataflow-diagram.md` exists with valid Mermaid flowchart |
| references/ links | Yes | Referenced files exist |
| Examples executable | Recommended | Command syntax correct |
| Auth method specified | Recommended | State which auth method is used |
| Permission policy specified | Recommended | List required permissions |
| Error handling complete | Recommended | Common errors have solutions |
| Version number correct | Recommended | Follows SemVer |
| Cost confirmation present | Recommended | `## Cost Confirmation` section for resource-mutating Skills |

---

## 17. References

- [Codex Skill Creator](https://github.com/openai/codex)
- [Skills Community Repo](https://github.com/openai/skills)
- [Feishu lark-skill-maker](https://open.feishu.cn)
- [Huawei Cloud Skills](https://gitcode.com/developer-skill/huaweicloud-skills)

---

> Document version: v1.0.0
> Generated: 2026-07-07
> File location: `references/skill-spec-generic.md`
