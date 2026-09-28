# IAM Policies — Huawei Cloud Skill Audit

## Required IAM Permissions

The audit tool itself does **not** require Huawei Cloud IAM permissions. It operates entirely on local files (SKILL.md, scripts, references).

However, if you want to **verify a skill's functionality** after audit (e.g., test that CLI commands work), the following permissions may be needed:

> ⚠️ `iam:credentials:list` 可列出账号下用户的凭据/访问密钥信息, 属**敏感权限**; 此示例仅用于功能验证, 生产环境应使用更细粒度的权限或优先采用**不需要 IAM 权限的本地验证方式**, 并遵循最小权限原则。

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:credentials:list"
      ],
      "Resource": [
        "urn:iam::<account-id>:user/<your-username>"
      ]
    }
  ]
}
```
> ⚠️ 上述 JSON 已限定 `Resource` 到具体 IAM 用户(`<account-id>`/`<your-username>` 替换为实际值),
> 避免 `iam:credentials:list` 作用于账号下全部用户凭据。生产环境请进一步收紧 Action 粒度,
> 优先采用**不需要 IAM 权限的本地验证方式**; 若确需 IAM 权限, 按最小权限原则裁剪。

## Audited Skill IAM Policies

When auditing a Huawei Cloud skill, the audit checks that the skill's own `references/iam-policies.md` exists and follows the least privilege principle.

### Audit Checks on IAM

| Check | Tool / Rule | What It Verifies |
|-------|-------------|-----------------|
| references/iam-policies.md exists | skill 结构规范检查(非 skillspector/gitleaks 规则) | File must exist in the skill directory |
| No wildcard permissions | skillspector (PE1) | No `*:*` 或 `Action: ["*"]` 等通配授权 |
| No hardcoded AK/SK | gitleaks | No credential strings in source files |
| No sudo/root commands | skillspector (PE2) | No privilege escalation patterns |

> 归属说明: 通配权限与 sudo/root 由 skillspector 的 PE1/PE2 规则承担(属 Privilege Escalation 类别);
> `references/iam-policies.md` 存在性属于 skill 结构规范检查, 不在 skillspector 规则 JSON 中(critical/high 档也不会因缺失该文件产生 skillspector 发现)。

## Least Privilege Principle

- Each skill should only have the minimum permissions required for its operations
- Read operations (List/Show/Get) and write operations (Create/Update/Delete) should be listed separately
- IAM policies must use JSON format with policy descriptions
