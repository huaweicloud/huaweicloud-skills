# Permission Policies - huawei-cloud-skill-creator-skill

> This Skill is a meta-skill that does not directly call Huawei Cloud APIs and requires no IAM permissions.
> This file only describes the permission template needed by generated sub-Skills.

## This Skill's Permissions

No additional IAM permissions required. This Skill only creates Skill file structures and does not execute Huawei Cloud API calls.

## Generated Sub-Skill Permission Template

Use [`templates/iam-policies.md.template`](../templates/iam-policies.md.template) to generate the sub-Skill's permission policy document.

Generated sub-Skills need to fill in based on the actual service:

| Placeholder | Description | Example |
|-------------|-------------|---------|
| `{{SERVICE_NAME}}` | Service full name | Elastic Cloud Server |
| `{{SERVICE_LOW}}` | Service lowercase identifier | ecs |
| `{{RESOURCE}}` | Resource identifier | servers |
| `{{RESOURCE_CN}}` | Resource Chinese name | Cloud Server |

## MFA Requirements

This Skill does not require MFA. In generated sub-Skills, delete operations should require MFA, marked via the `{{DELETE_REQUIRES_MFA}}` placeholder in the template.

## Minimum Privilege Policy JSON (This Skill)

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
