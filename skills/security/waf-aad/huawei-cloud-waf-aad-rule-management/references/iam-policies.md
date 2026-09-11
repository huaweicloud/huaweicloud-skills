# IAM Policies for huawei-cloud-waf-aad-rule-management

Least-privilege IAM permissions for the WAF / AAD skill. Split read-only (R3) from write (R2/R1)
where possible.

## Read-Only Policy (R3 — queries & diagnostics)

Covers: WAF instances/hosts, policies, all rule types; AAD instances, packages, protected IPs.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:instance:list",
        "waf:host:list",
        "waf:host:get",
        "waf:policy:list",
        "waf:policy:get",
        "waf:rule:list",
        "waf:rule:get",
        "waf:geoip:list",
        "antiddos:instance:list",
        "antiddos:package:list",
        "antiddos:ip:list",
        "antiddos:ip:get",
        "eps:enterpriseProjects:list"
      ],
      "Resource": "*"
    }
  ]
}
```

## Full Policy (read + rule management R2/R1)

Adds rule creation (`BatchCreate*`) and deletion (`Delete*Rule`) permissions. AAD instance
purchase/unsubscribe has **no IAM API action** — it is a console-only (包周期) flow and is not
granted here.

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "waf:instance:list",
        "waf:host:list",
        "waf:host:get",
        "waf:policy:list",
        "waf:policy:get",
        "waf:rule:list",
        "waf:rule:get",
        "waf:geoip:list",
        "antiddos:instance:list",
        "antiddos:package:list",
        "antiddos:ip:list",
        "antiddos:ip:get",
        "eps:enterpriseProjects:list"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "waf:rule:create",
        "waf:rule:delete"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- Multi-factor / agency (委托) setups: grant the role to the agency instead of a user.
- Enterprise projects: if WAF resources live in a non-default enterprise project, add
  `eps:enterpriseProjects:get` and pass `--enterprise_project_id=<eps-id>` in CLI calls; the
  default is `0` (default enterprise project).
- The IAM policy action names above follow Huawei Cloud WAF/AAD API permissions
  (`waf:*`, `antiddos:*`). Verify exact action strings in the console IAM *Permissions* page for
  your region before production rollout.
