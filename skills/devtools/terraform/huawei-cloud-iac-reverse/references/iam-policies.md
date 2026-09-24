# IAM Policies

## Summary

This skill discovers and analyzes existing Huawei Cloud resources via RMS
(Config / 配置审计) and reads service-level metadata through the KooCLI
(`hcloud`). It **never creates, modifies, or deletes** cloud resources — it
only performs read-only queries and generates Terraform HCL code locally.

## Least-Privilege Policy

The following IAM policy grants the minimum permissions required by this
skill. All actions are **read-only** (`*:list`, `*:get`, `*:show`, ...).

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rms:resources:list",
        "rms:resources:get"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:vpcs:list",
        "vpc:subnets:list",
        "vpc:securityGroups:list",
        "vpc:securityGroupRules:list",
        "vpc:publicIps:list",
        "vpc:bandwidths:list"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:servers:list",
        "ecs:serverVolumes:list",
        "ecs:flavors:get"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "evs:volumes:list",
        "obs:bucket:ListAllMyBuckets",
        "obs:bucket:GetBucketLocation"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cce:cluster:list",
        "cce:node:list",
        "cce:nodePool:list"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "gaussdb:instance:list",
        "gaussdb:mysqlInstance:list",
        "sfsturbo:shares:list"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dcs:instance:list",
        "dms:instance:list",
        "kms:key:list",
        "lts:logGroup:list"
      ]
    }
  ]
}
```

## Notes

- The RMS `ListAllResources` call (service `Config`) requires the
  `rms:resources:list` permission; without it the discovery phase fails.
- The resource types returned by RMS span many services; the statements above
  cover the layers handled by this skill (network → storage → compute → CCE →
  database → cache/MQ → KMS/LTS).
- For `terraform plan`, the same credentials are reused; no additional write
  permission is granted because this skill never executes `terraform apply`.
- Credentials are read from the `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`
  environment variables — never hardcoded in any file.