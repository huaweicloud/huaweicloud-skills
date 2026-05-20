<h1 align="center">Huawei Cloud Skills</h1>

<p align="center">
  华为云官方 Agent Skills 集合，兼容主流Agent，包含Agent类安装部署、管理运维、最佳解决方案和产品案例实践等多个Skills。
</p>

<p align="center">
  <a href="https://gitcode.com/developer-skill/huaweicloud-skills/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License" /></a>
  <a href="https://gitcode.com/developer-skill/huaweicloud-skills/stargazers"><img src="https://img.shields.io/github/stars/QianWen-AI/qianwen-ai?style=social" alt="Stars" /></a>
  <a href="https://support.huaweicloud.com/qs-hcli/hcli_02_003.html"><img src="https://img.shields.io/badge/Agent%20Skills-compatible-brightgreen.svg" alt="Agent Skills" /></a>
  <a href="https://nodejs.org"><img src="https://img.shields.io/badge/node-%3E%3D18-blue.svg" alt="Node.js" /></a>
</p>

<p align="center">
  <a href="./README.md">English</a>
</p>

---


## 概述

本仓库包含了华为云官方维护的 Agent Skills，skills目录下按照产品域分类，各个产品域下的文件夹是每个skill的目录，每个 Skill 目录包含运行该技能所需的全部文件。

## Skills 列表

[华为云产品 Skills 列表](https://gitcode.com/developer-skill/huaweicloud-skills/tree/master/skills)


### 自包含包结构


```
skill-name/        # 技能包根目录
├── SKILL.md       # 技能定义文件（必需，唯一入口）
└── references/    # 参考文档目录（可选但推荐）        
    ├── cli-installation-guide.md   # CLI安装指南
    ├── iam-policies.md             # IAM权限策略
    ├── verification-method.md      # 验证方法
    ├── acceptance-criteria.md      # 验收标准
    └── related-commands.md         # 相关命令参考
└── scripts/        # 可执行脚本（可选）
    ├── analyze.py
    └── deploy.sh   
└── templates/      # 模板文件（可选）
    ├── config.yaml
    └──  report.md
└── demo/           # 演示样例（可选）
    └── example.json


```


### SKILL.md标准格式
```yaml
---
name: huawei-cloud-{product}-{function}
description: |
  {中文功能描述}，基于KooCLI v7.2.2+。
  {主要能力列表}。
  适用于{适用场景}。
  触发词："{触发词1}"、"{触发词2}"、"{触发词3}"
tags: [huawei-cloud, {product}, {function}, {other-tags}]
version: 1.0.0
---

# 华为云 {产品} {功能} 技能

## 概述

本技能提供{功能描述}。

**架构**: {涉及的云服务}

**适用场景**:
- {场景1}
- {场景2}

## 前置条件

### 1. CLI 要求
- KooCLI >= 7.2.2
- 验证安装: `hcloud version`

### 2. 认证配置
- 有效的华为云凭证（AK/SK模式）
- **安全规则**:
  - 🚫 绝不暴露AK/SK值
  - ✅ 仅使用 `hcloud configure list` 检查凭据状态

### 3. IAM 权限要求
- {权限1}
- {权限2}
详见 [IAM权限策略](references/iam-policies.md)

## KooCLI 命令格式标准

{命令格式说明和示例}

## 核心命令

### {功能分组1}

```bash
# {命令说明}
hcloud {SERVICE} {Operation} --param=value --cli-region=<region>


## 参数确认

| 参数名 | 必需/可选 | 说明 | 默认值 |
|--------|----------|------|--------|
| `{param}` | 必需 | {说明} | N/A |

## 输出格式

{输出格式说明}

## 验证方法

详见 [验证方法](references/verification-method.md)

## 最佳实践

1. {最佳实践1}
2. {最佳实践2}

## 参考文档

| 文档 | 说明 |
|------|------|
| [CLI安装指南](references/cli-installation-guide.md) | KooCLI安装配置 |
| [IAM权限策略](references/iam-policies.md) | 所需权限列表 |
| [验证方法](references/verification-method.md) | 各步骤验证 |
| [验收标准](references/acceptance-criteria.md) | 测试标准 |

## 注意事项

- {注意事项1}
- {注意事项2}
```

## 安装

### 使用 npx 安装 Skills

```bash
# 安装单个 Skill
npx skills add https://github.com/huaweicloud/huaweicloud-skills --skill <skill-name>
```

### 手动安装

```bash
# 克隆仓库
git clone https://github.com/huaweicloud/huaweicloud-skills

# 进入 Skills 目录
npx skills add <path>/huaweicloud-skills/skills/<skill-name>

```

## 认证与配置

使用华为云产品相关的 Skills 需要配置认证信息。支持以下认证方式：

交互式配置

```bash
Access Key Id：<your AK>
Secret Access Key：<yourSKt>
```

AccessKey 认证

```bash
# 命令设置凭证
hcloud configure set --cli-access-key="<your AK> " --cli-secret-key="<yourSK>" --cli-mode="AKSK"
```
**安全提示**

- **`AccessKey 认证`**和**`KooCLI配置文件的AK凭证认证`**，建议仅在本地测试环境时个人使用，避免明文 AK/SK凭证信息的外泄。
- 云上环境服务，强烈推荐参考[华为云命令行工具服务KooCLI](https://support.huaweicloud.com/productdesc-hcli/hcli_26_002.html)的安全要求。

## 问题

[提交 Issue](https://gitcode.com/developer-skill/huaweicloud-skills/issues)不符合指南的问题可能会立即关闭。

## 相关地址

- [华为云官网](https://www.huaweicloud.com/)
- [gitcode](https://gitcode.com/developer-skill/huaweicloud-skills/)

## 许可证

[MIT License](https://gitcode.com/developer-skill/huaweicloud-skills/blob/master/LICENSE)

## 法务条款

该仓库提供的所有 Skills 均为开源项目，致力于为开发者提供丰富的 Agent 能力扩展工具，帮助您更高效地管理云资源。并遵循 [MIT 开源协议](https://spdx.org/licenses/MIT.html)。在您使用本平台提供的Skills之前，请务必仔细阅读[法务条款](https://www.huaweicloud.com/declaration/developer_service_agreement.html)，充分了解可能存在的风险。一旦您下载、安装或通过任何方式运行本平台提供的 Skills，即视为您已充分阅读并同意承担所有相关的操作风险，并确认由您自行承担因使用这些代码而产生的一切后果。
