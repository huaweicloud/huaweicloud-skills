# Huawei Cloud Skills

[English](README.md) | **简体中文**

华为云官方 Agent Skills 集合，兼容主流Agent,包含Agent类安装部署、管理运维、最佳解决方案和产品案例实践等多个Skills。

## 概述

本仓库包含了华为云官方维护的 Agent Skills，skills目录下按照产品域分类，各个产品域下的文件夹是每个skill的目录，每个 Skill 目录包含运行该技能所需的全部文件。

## Skills 列表

[华为云产品 Skills 列表](https://gitcode.com/developer-skill/huaweicloud-skills/tree/master/skills)


## SKILL.md标准格式

skill-name/                    # 技能包根目录
├── SKILL.md                   # 技能定义文件（必需，唯一入口,默认英文）
├── references/                # 参考文档目录（可选但推荐）
│   ├── cli-installation-guide.md   # CLI安装指南
│   ├── iam-policies.md             # IAM权限策略
│   ├── verification-method.md      # 验证方法
│   ├── acceptance-criteria.md      # 验收标准
│   └── related-commands.md         # 相关命令参考
├── scripts/                   # 可执行脚本（可选）
│   ├── analyze.py
│   └── deploy.sh
├── templates/                 # 模板文件（可选）
│   ├── config.yaml
│   └── report.md
└── demo/                      # 演示样例（可选）
└── example.json

## 安装

### 使用 npx 安装 Skills

```bash
# 安装单个 Skill
npx skills add https://gitcode.com/developer-skill/huaweicloud-skills --skill <skill-name>
```

### 手动安装

```bash
# 克隆仓库
git clone https://gitcode.com/developer-skill/huaweicloud-skills

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


## 问题

[提交 Issue](https://gitcode.com/developer-skill/huaweicloud-skills/issues)不符合指南的问题可能会立即关闭。

## 相关地址

- [华为云官网](https://www.huaweicloud.com/)
- [gitcode](https://gitcode.com/developer-skill/huaweicloud-skills/)

## 许可证

[MIT License](https://gitcode.com/developer-skill/huaweicloud-skills/blob/master/LICENSE)

## 法务条款

该仓库提供的所有 Skills 均为开源项目，致力于为开发者提供丰富的 Agent 能力扩展工具，帮助您更高效地管理云资源。并遵循 [MIT 开源协议](https://spdx.org/licenses/MIT.html)。在您使用本平台提供的Skills之前，请务必仔细阅读[法务条款](https://www.huaweicloud.com/declaration/statement.html)，充分了解可能存在的风险。一旦您下载、安装或通过任何方式运行本平台提供的 Skills，即视为您已充分阅读并同意承担所有相关的操作风险，并确认由您自行承担因使用这些代码而产生的一切后果。
