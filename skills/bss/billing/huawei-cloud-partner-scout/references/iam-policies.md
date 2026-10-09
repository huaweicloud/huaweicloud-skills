# IAM Policies (Least Privilege)

The skill queries BSS partner APIs with the partner account's AK/SK
(解决方案提供商/总经销商 role). No extra IAM policy is granted by this skill —
the partner relationship itself (伙伴账号关联) is what authorizes the query set.

For an IAM user inside the partner account used to run these queries, attach a
read-only custom policy covering BSS read permissions:

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:bill:view",
        "bss:balance:view",
        "bss:customer:view",
        "bss:order:view",
        "bss:coupon:view",
        "bss:resource:view"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> **Least privilege note:** the actions above are query-only. Do NOT grant any
> `bss:*:update`, `bss:*:create`, `bss:*:delete`, or `bss:pay` actions — the
> skill is read-only and must refuse write operations at the semantic layer too.

If the partner console requires a fixed region, keep the policy region-scoped
(`"Condition": {"StringEquals": {"g:DomainId": "<partner_domain_id>"}}` is
optional; BSS is a global service and normally region-independent).

## Permission error mapping

| Error | Meaning | Suggested fix |
| --- | --- | --- |
| `domain_id has no access to this api` | Account not a partner (no 伙伴关系) | Use a 解决方案提供商/总经销商 account |
| `CBC.0151` | Action not authorized | Check the IAM policy / partner role assignment |
| `ListFreeResourceInfos` returns 403 | 资源包查询需要额外权限 | Inform user; the API is marked "需权限" in the requirement |