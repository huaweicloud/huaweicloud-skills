# IAM Policies — Least Privilege for huawei-cloud-sg-manage

This skill requires IAM permissions on the VPC service (security groups are VPC
sub-resources). The IAM action names below follow the official VPC 权限及授权项 naming
(`vpc:securityGroups:*` and `vpc:securityGroupRules:*`) — the same actions referenced by
existing skills in this repository (e.g. `huawei-cloud-iac-reverse`,
`huawei-cloud-flexus-l-deploy-jiuwenswarm` use `vpc:securityGroups:list/get`,
`vpc:securityGroupRules:list/get`).

Grant the **minimum** permissions per capability group. Policies are region-scoped by the
`--cli-region` flag at call time.

## 1. Query + Analyze (R3, read-only)

Covers: `huawei_list_security_groups`, `huawei_list_security_group_rules`,
`huawei_get_security_group`, `huawei_diagnose_sg_port_connectivity`,
`huawei_analyze_sg_rule_conflict`, `huawei_audit_sg_overexposed_rules`.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:securityGroups:get",
        "vpc:securityGroups:list",
        "vpc:securityGroupRules:get",
        "vpc:securityGroupRules:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> The analyze actions only *read* rules (they never modify them), so the read-only set
> above is sufficient. If a legacy IAM v3 template is required, use `"Version": "1.1"`.

## 2. Manage (R2 — create / update)

Covers: `huawei_create_security_group`, `huawei_create_sg_rule`,
`huawei_update_security_group`.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:securityGroups:create",
        "vpc:securityGroups:update",
        "vpc:securityGroups:get",
        "vpc:securityGroups:list",
        "vpc:securityGroupRules:create",
        "vpc:securityGroupRules:get",
        "vpc:securityGroupRules:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 3. Manage (R1 — delete)

Covers: `huawei_delete_security_group`, `huawei_delete_sg_rule`.

```json
{
  "Version": "5.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:securityGroups:delete",
        "vpc:securityGroups:get",
        "vpc:securityGroups:list",
        "vpc:securityGroupRules:delete",
        "vpc:securityGroupRules:get",
        "vpc:securityGroupRules:list"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## Notes

- Delete actions (`vpc:securityGroups:delete`, `vpc:securityGroupRules:delete`) have
  irreversible effects on network connectivity — restrict them to operators only.
- The skill itself never hardcodes credentials; authentication is delegated to the hcloud
  CLI (AK/SK env vars or local profile).