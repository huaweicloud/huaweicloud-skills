# Huawei Cloud Skills

 **English** | [简体中文](README-CN.md)

A collection of official Huawei Cloud Agent Skills, compatible with mainstream Agents, including skills for Agent installation and deployment, management and operations, best practice solutions, and product case studies.

## Overview

This repository contains officially maintained Huawei Cloud Agent Skills. The skills are organized by product domain in the skills directory. Each product domain folder contains subdirectories for individual skills, with each skill directory containing all files necessary to run that skill.

## Skills List

[Huawei Cloud Product Skills List](https://gitcode.com/developer-skill/huaweicloud-skills/tree/master/skills)

## SKILL.md Standard Format

skill-name/                    # Skill package root directory
├── SKILL.md                   # Skill definition file (required, single entry point, default English)
├── references/                # Reference documentation directory (optional but recommended)
│   ├── cli-installation-guide.md   # CLI installation guide
│   ├── iam-policies.md             # IAM permission policies
│   ├── verification-method.md      # Verification methods
│   ├── acceptance-criteria.md      # Acceptance criteria
│   └── related-commands.md         # Related command references
├── scripts/                   # Executable scripts (optional)
│   ├── analyze.py
│   └── deploy.sh
├── templates/                 # Template files (optional)
│   ├── config.yaml
│   └── report.md
└── demo/                      # Demonstration examples (optional)
└── example.json

## Installation

### Install Skills with npx

```bash
# Install a single skill
npx skills add https://gitcode.com/developer-skill/huaweicloud-skills --skill <skill-name>
```

### Manual Installation

```bash
# Clone the repository
git clone https://gitcode.com/developer-skill/huaweicloud-skills

# Navigate to Skills directory
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

## Issues

[Submit Issue](https://gitcode.com/developer-skill/huaweicloud-skills/issues) Issues that do not follow the guidelines may be closed immediately.

## Related 

- [Huawei Cloud Official Website](https://www.huaweicloud.com/)
- [gitcode](https://gitcode.com/developer-skill/huaweicloud-skills/)

## License

[MIT License](https://gitcode.com/developer-skill/huaweicloud-skills/blob/master/LICENSE)

## Legal 

All skills provided in this repository are open-source projects, dedicated to providing developers with rich Agent capability extension tools to help you manage cloud resources more efficiently. They follow the [MIT Open Source License](https://spdx.org/licenses/MIT.html). Before using the skills provided by this platform, please carefully read the [Legal Terms](https://www.huaweicloud.com/declaration/statement.html) to fully understand potential risks. Once you download, install, or run the skills provided by this platform in any way, it is deemed that you have fully read and agreed to bear all related operational risks, and confirm that you will bear all consequences arising from using this code.