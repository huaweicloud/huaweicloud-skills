<h1 align="center">Huawei Cloud Skills</h1>

<p align="center">
  A collection of official Huawei Cloud Agent Skills, compatible with mainstream agents, including skills for agent installation and deployment, management and operations, best practice solutions, and product case studies.

</p>

<p align="center">
  <a href="https://gitcode.com/developer-skill/huaweicloud-skills/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License" /></a>
  <a href="https://gitcode.com/developer-skill/huaweicloud-skills/stargazers"><img src="https://img.shields.io/github/stars/QianWen-AI/qianwen-ai?style=social" alt="Stars" /></a>
  <a href="https://support.huaweicloud.com/qs-hcli/hcli_02_003.html"><img src="https://img.shields.io/badge/Agent%20Skills-compatible-brightgreen.svg" alt="Agent Skills" /></a>
  <a href="https://nodejs.org"><img src="https://img.shields.io/badge/node-%3E%3D18-blue.svg" alt="Node.js" /></a>
</p>

<p align="center">
  <a href="./README-CN.md">简体中文</a>
</p>

---
# Huawei Cloud Skills

 **English** | [简体中文](README-CN.md)

A collection of official Huawei Cloud Agent Skills, compatible with mainstream agents, including skills for agent installation and deployment, management and operations, best practice solutions, and product case studies.

## Overview

This repository contains officially maintained Huawei Cloud Agent Skills. The skills are organized by product domain in the skills directory. Each product domain folder contains directories for individual skills, with each skill directory including all files required to run that skill.

## Skills List

[Huawei Cloud Product Skills List](https://gitcode.com/developer-skill/huaweicloud-skills/tree/master/skills)

### Self-contained Package Structure

```
skill-name/        # Skill package root directory
├── SKILL.md       # Skill definition file (required, single entry point)
└── references/    # Reference documentation directory (optional but recommended)
    ├── cli-installation-guide.md   # CLI installation guide
    ├── iam-policies.md             # IAM permission policies
    ├── verification-method.md      # Verification methods
    ├── acceptance-criteria.md      # Acceptance criteria
    └── related-commands.md         # Related command references
└── scripts/       # Executable scripts (optional)
    ├── analyze.py
    └── deploy.sh
└── templates/     # Template files (optional)
    ├── config.yaml
    └── report.md
└── demo/          # Demonstration examples (optional)
    └── example.json
```

### SKILL.md Standard Format

```yaml
---
name: huawei-cloud-{product}-{function}
description: |
  {English function description}, based on KooCLI v7.2.2+.
  {List of main capabilities}.
  Suitable for {applicable scenarios}.
  Trigger words: "{trigger word 1}", "{trigger word 2}", "{trigger word 3}"
tags: [huawei-cloud, {product}, {function}, {other-tags}]
version: 1.0.0
---

# Huawei Cloud {Product} {Function} Skill

## Overview

This skill provides {function description}.

**Architecture**: {Involved cloud services}

**Applicable Scenarios**:
- {Scenario 1}
- {Scenario 2}

## Prerequisites

### 1. CLI Requirements
- KooCLI >= 7.2.2
- Verify installation: `hcloud version`

### 2. Authentication Configuration
- Valid Huawei Cloud credentials (AK/SK mode)
- **Security Rules**:
  - 🚫 Never expose AK/SK values
  - ✅ Only use `hcloud configure list` to check credential status

### 3. IAM Permission Requirements
- {Permission 1}
- {Permission 2}
See [IAM Permission Policies](references/iam-policies.md) for details

## KooCLI Command Format Standard

{Command format description and examples}

## Core Commands

### {Function Group 1}

```bash
# {Command description}
hcloud {SERVICE} {Operation} --param=value --cli-region=<region>

## Parameter Confirmation

| Parameter Name | Required/Optional | Description | Default Value |
|---------------|------------------|-------------|---------------|
| `{param}` | Required | {Description} | N/A |

## Output Format

{Output format description}

## Verification Methods

See [Verification Methods](references/verification-method.md) for details

## Best Practices

1. {Best Practice 1}
2. {Best Practice 2}

## Reference Documentation

| Document | Description |
|----------|-------------|
| [CLI Installation Guide](references/cli-installation-guide.md) | KooCLI installation and configuration |
| [IAM Permission Policies](references/iam-policies.md) | Required permission list |
| [Verification Methods](references/verification-method.md) | Verification steps |
| [Acceptance Criteria](references/acceptance-criteria.md) | Testing standards |

## Notes

- {Note 1}
- {Note 2}
```

## Installation

### Install Skills Using npx

```bash
# Install a single skill
npx skills add https://github.com/huaweicloud/huaweicloud-skills --skill <skill-name>
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/huaweicloud/huaweicloud-skills

# Enter the Skills directory
npx skills add <path>/huaweicloud-skills/skills/<skill-name>
```

## Authentication and Configuration

Using Huawei Cloud product-related skills requires authentication configuration. The following authentication methods are supported:

### Interactive Configuration

```bash
Access Key Id: <your AK>
Secret Access Key: <your SK>
```

### AccessKey Authentication

```bash
# Set credentials via command
hcloud configure set --cli-access-key="<your AK>" --cli-secret-key="<your SK>" --cli-mode="AKSK"
```

**Security Tips**

- **`AccessKey Authentication`** and **`AK credential authentication in KooCLI configuration files`** are recommended only for personal use in local testing environments to avoid exposing plaintext AK/SK credentials.
- For cloud service environments, it is strongly recommended to follow the security requirements in [Huawei Cloud Command Line Tool Service KooCLI](https://support.huaweicloud.com/productdesc-hcli/hcli_26_002.html).

## Issues

[Submit Issues](https://gitcode.com/developer-skill/huaweicloud-skills/issues) - Issues that do not follow the guidelines may be closed immediately.

## Related 

- [Huawei Cloud Official Website](https://www.huaweicloud.com/)
- [gitcode](https://gitcode.com/developer-skill/huaweicloud-skills/)

## License

[MIT License](https://gitcode.com/developer-skill/huaweicloud-skills/blob/master/LICENSE)

## Legal 

All skills provided in this repository are open-source projects, dedicated to providing developers with rich agent capability extension tools to help you manage cloud resources more efficiently. They follow the [MIT Open Source License](https://spdx.org/licenses/MIT.html). Before using the skills provided by this platform, please carefully read the [Legal Terms](https://www.huaweicloud.com/declaration/developer_service_agreement.html) to fully understand potential risks. Once you download, install, or run the skills provided by this platform in any way, it is deemed that you have fully read and agree to bear all related operational risks, and confirm that you are solely responsible for all consequences arising from the use of this code.