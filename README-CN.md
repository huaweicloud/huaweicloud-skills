<h1 align="center">Huawei Cloud Skills</h1>

<p align="center">
  华为云官方 Agent Skills 集合，向AI Agent提供丰富的华为云服务产品、工具和最佳实践能力，兼容主流AI Agent，助力AI Agent更好使用华为云。
</p>

<p align="center">
  <a href="https://github.com/huaweicloud/huaweicloud-skills/blob/master/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" /></a>
  <a href="https://support.huaweicloud.com/qs-hcli/hcli_02_003.html"><img src="https://img.shields.io/badge/Agent%20Skills-compatible-brightgreen.svg" alt="Agent Skills" /></a>
  <a href="https://nodejs.org"><img src="https://img.shields.io/badge/node-%3E%3D18-blue.svg" alt="Node.js" /></a>
</p>

<p align="center">
  <a href="./README.md">English</a>
</p>

---


## 概述

本仓库包含了华为云官方维护的 Agent Skills，skill包按照产品域或功能域放在不同目录下，每个 Skill 目录包含运行该技能所需的全部文件，所有的skill均经过测试与验证、且兼容主流AI Agent。开发者可以安全、高效使用这些skill。

## Skills 列表

[华为云产品 Skills 列表](https://github.com/huaweicloud/huaweicloud-skills/tree/master/skills)


### 自包含包结构


```
skill-name/        # 技能包根目录
├── SKILL.md       # 技能定义文件（必需，唯一入口）
├── references/    # 参考文档目录（可选但推荐）
├── scripts/        # 可执行脚本（可选） 
├── templates/      # 模板文件（可选）
└── demo/           # 演示样例（可选）
```


## 安装

### 使用 npx 安装 Skills

```bash
# 安装单个 Skill
npx skills add huaweicloud/huaweicloud-skills --skill <skill-name>

# 安装全部 Skills
npx skills add huaweicloud/huaweicloud-skills
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

[提交 Issue](https://github.com/huaweicloud/huaweicloud-skills/issues)不符合指南的问题可能会立即关闭。

## 相关地址

- [华为云官网](https://www.huaweicloud.com/)

## 许可证

[MIT License](https://github.com/huaweicloud/huaweicloud-skills/blob/master/LICENSE)

## 法务条款

该仓库提供的所有 Skills 均为开源项目，致力于为开发者提供丰富的 Agent 能力扩展工具，帮助您更高效地管理云资源。并遵循 [MIT 开源协议](https://spdx.org/licenses/MIT.html)。在您使用本平台提供的Skills之前，请务必仔细阅读[法务条款](https://www.huaweicloud.com/declaration/developer_service_agreement.html)，充分了解可能存在的风险。一旦您下载、安装或通过任何方式运行本平台提供的 Skills，即视为您已充分阅读并同意承担所有相关的操作风险，并确认由您自行承担因使用这些代码而产生的一切后果。
