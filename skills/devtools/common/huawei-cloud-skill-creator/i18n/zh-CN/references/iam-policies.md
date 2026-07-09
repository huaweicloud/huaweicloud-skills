# 权限策略 - huawei-cloud-skill-creator-skill

> 本 Skill 为元技能（Meta Skill），不直接调用华为云 API，无需 IAM 权限。
> 此文件仅说明生成的子 Skill 所需的权限模板。

## 本 Skill 权限

无需额外 IAM 权限。本 Skill 仅创建 Skill 文件结构，不执行华为云 API 调用。

## 生成的子 Skill 权限模板

使用 [`templates/iam-policies.md.template`](../templates/iam-policies.md.template) 生成子 Skill 的权限策略文档。

生成的子 Skill 需根据实际服务填写：

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{{SERVICE_NAME}}` | 服务全称 | Elastic Cloud Server |
| `{{SERVICE_LOW}}` | 服务小写标识 | ecs |
| `{{RESOURCE}}` | 资源标识 | servers |
| `{{RESOURCE_CN}}` | 资源中文名 | 云服务器 |

## MFA 要求

本 Skill 不需要 MFA。生成的子 Skill 中，删除类操作建议要求 MFA，在模板中通过 `{{DELETE_REQUIRES_MFA}}` 占位符标注。

## 最小权限策略 JSON（本 Skill）

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [],
      "Resource": ["*"]
    }
  ]
}
```
