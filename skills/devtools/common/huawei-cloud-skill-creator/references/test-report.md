# 功能测试报告 — huawei-cloud-skill-creator

> 生成时间：2026-07-15 13:42:40
> 测试区域：cn-north-4
> CLI 版本：[USE_ERROR]The --version parameter format must be '--param=value'.

## 测试结果汇总

| 指标 | 值 |
|------|-----|
| 总测试数 | 6 |
| ✅ 通过 | 3 |
| ❌ 失败 | 2 |
| ⏭️ 跳过 | 1 |
| 测试者 | Skill Creator (huawei-cloud-skill-creator) |

## 测试详情

| 操作 | 测试类型 | 结果 | 备注 |
|------|----------|------|------|
| `hcloud IAM CreatePolicy --help` | CLI 语法 | ✅ 通过 | 来自 iam-policies.md.template |
| `hcloud IAM CreatePolicy --help` | 变更操作(仅语法) | ⏭️ 安全跳过 | 已通过 --help 验证，不执行实际变更 |
| `hcloud IAM ListUsers --help` | CLI 语法 | ✅ 通过 | 来自 cli-installation-guide.md |
| `hcloud IAM ListUsers --cli-region=cn-north-4 --limit=1` | 只读实时 | ❌ 失败 | API 返回错误或权限不足 |
| `hcloud ECS ListServers --help` | CLI 语法 | ✅ 通过 | 来自 related-commands.md |
| `hcloud ECS ListServers --cli-region=cn-north-4 --limit=1` | 只读实时 | ❌ 失败 | API 返回错误或权限不足 |

**结论：❌ 2/6 项测试失败 — 需要修复后重新测试**
