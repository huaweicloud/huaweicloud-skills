<h1 align="center">Huawei Cloud Skills</h1>

<p align="center">
  A collection of official Huawei Cloud Agent Skills, providing AI Agents with rich Huawei Cloud service products, tools, and best practice capabilities. Compatible with mainstream AI Agents, helping AI Agents better utilize Huawei Cloud.
</p>

<p align="center">
  <a href="https://github.com/huaweicloud/huaweicloud-skills/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" /></a>
  <a href="https://support.huaweicloud.com/qs-hcli/hcli_02_003.html"><img src="https://img.shields.io/badge/Agent%20Skills-compatible-brightgreen.svg" alt="Agent Skills" /></a>
  <a href="https://nodejs.org"><img src="https://img.shields.io/badge/node-%3E%3D18-blue.svg" alt="Node.js" /></a>
</p>

<p align="center">
  <a href="./README-CN.md">简体中文</a>
</p>


---

## Overview

This repository contains officially maintained Huawei Cloud Agent Skills. Skills are organized by product domain or functional domain in different directories. Each Skill directory contains all files required to run that skill. All skills have been tested and verified and are compatible with mainstream AI Agents, allowing developers to use them safely and efficiently.

## Skills List

[Huawei Cloud Product Skills List](https://github.com/huaweicloud/huaweicloud-skills/tree/master/skills)

### Self-contained Package Structure

```
skill-name/        # Skill package root directory
├── SKILL.md       # Skill definition file (required, single entry point)
├── references/    # Reference documentation directory (optional but recommended)
├── scripts/       # Executable scripts (optional)
├── templates/     # Template files (optional)
└── demo/          # Demonstration examples (optional)
```

## Installation

### Install Skills Using npx

```bash
# Install a single Skill
npx skills add huaweicloud/huaweicloud-skills --skill <skill-name>

# Install all Skills
npx skills add huaweicloud/huaweicloud-skills
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

[Submit an Issue](https://github.com/huaweicloud/huaweicloud-skills/issues) - Issues that do not follow the guidelines may be closed immediately.

## Related 

- [Huawei Cloud Official Website](https://www.huaweicloud.com/)

## License

[MIT License](https://github.com/huaweicloud/huaweicloud-skills/blob/master/LICENSE)

## Legal

All skills provided in this repository are open-source projects, dedicated to providing developers with rich agent capability extension tools to help you manage cloud resources more efficiently. They follow the [MIT Open Source License](https://spdx.org/licenses/MIT.html). Before using the skills provided by this platform, please carefully read the [Legal Terms](https://www.huaweicloud.com/declaration/developer_service_agreement.html) to fully understand potential risks. Once you download, install, or run the skills provided by this platform in any way, it is deemed that you have fully read and agree to bear all related operational risks, and confirm that you are solely responsible for all consequences arising from the use of this code.