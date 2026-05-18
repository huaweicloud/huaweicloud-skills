# Huawei Cloud Skills

**English** | [简体中文](README-CN.md)

Official Huawei Cloud Agent Skills collection, providing rich Huawei Cloud product capabilities and general toolkits for AI Agents.

## Overview

This repository contains a collection of officially maintained Agent Skills designed to help developers use Huawei Cloud products and services more efficiently. Each Skill is carefully designed and tested to ensure stability and reliability.

## Skills List

Huawei Cloud Product Skills List:

* huawei-cloud-cli-guidance
* huawei-cloud-find-skills
* huawei-cloud-ecs-diagnosis-workflowloud-cli-guidance
* huawei-cloud-ecs-manage
* huawei-cloud-as-manage
* huawei-cloud-vpc-manage
* huawei-cloud-eip-manage
* huawei-cloud-elb-manage
* huawei-cloud-obs-manage
* huawei-cloud-obs-backup
* huawei-cloud-evs-manage
* huawei-cloud-rds-manage
* huawei-cloud-dcs-manage
* huawei-cloud-iam-manage
* huawei-cloud-waf-manage
* huawei-cloud-ces-manage
* huawei-cloud-cce-manage
* huawei-cloud-dtse-workflow

## SKILL.md Standard Format

skill-name/                    # Skill package root directory
├── SKILL.md                   # Skill definition file (required, unique entry, default English)
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
└── demo/                      # Demo examples (optional)
└── example.json

## Installation

### Install Skills with npx

```bash
# Install a single Skill
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

Using Huawei Cloud product-related Skills requires authentication configuration. The following authentication methods are supported:

Interactive Configuration

```bash
Access Key Id：<your-access-key-id>
Secret Access Key：<your-access-key-secret>
```

AccessKey Authentication

```bash
# Command to set credentials
hcloud configure set --cli-access-key=<AK> --cli-secret-key=<SK>
```

**Security Tips**

- **`AccessKey Authentication`** and **`AK credential authentication via configuration file`** are recommended only for personal use in local testing environments to avoid exposure of plaintext AK/SK credential information.

## Issues

[Submit Issue](https://gitcode.com/developer-skill/huaweicloud-skills/issues) Issues that do not follow the guidelines may be closed immediately.

## Related

- [Huawei Cloud Official Website](https://www.huaweicloud.com/)
- [gitcode](https://gitcode.com/developer-skill/huaweicloud-skills/)

## License

[MIT License](https://gitcode.com/developer-skill/huaweicloud-skills/blob/master/LICENSE)

## Legal

All Skills provided in this repository are open-source projects dedicated to providing developers with rich Agent capability extension tools to help you manage cloud resources more efficiently. They follow the [MIT Open Source License](https://spdx.org/licenses/MIT.html). Before using the Skills provided by this platform, please carefully read the [Legal Terms](https://www.huaweicloud.com/declaration/statement.html) to fully understand potential risks. Once you download, install, or run the Skills provided by this platform in any way, it is deemed that you have fully read and agreed to bear all related operational risks, and confirm that you will bear all consequences arising from using this code.