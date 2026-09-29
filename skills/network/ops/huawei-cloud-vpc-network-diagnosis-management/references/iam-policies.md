# IAM Policies — Least Privilege for huawei-cloud-vpc-network-diagnosis-management

This skill requires IAM permissions on the VPC service (service prefix `vpc`). Grant the
**minimum** permissions per capability group. All policies are region-scoped (VPC is a
regional service; subnets/route tables/ports/security groups belong to a project).

## 1. Query + Diagnose (R3, read-only)

Covers: `huawei_list_vpcs`, `huawei_list_subnets`, `huawei_get_vpc`, `huawei_get_subnet`,
`huawei_list_route_tables`, `huawei_diagnose_network_connectivity`,
`huawei_diagnose_port_connectivity`, `huawei_analyze_subnet_cidr_conflict`.

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:listVpcs",
        "vpc:showVpc",
        "vpc:listSubnets",
        "vpc:showSubnet",
        "vpc:listRouteTables",
        "vpc:showRouteTable",
        "vpc:listPorts",
        "vpc:showPort",
        "vpc:listSecurityGroups",
        "vpc:showSecurityGroup"
      ],
      "Resource": ["*"]
    }
  ]
}
```

> `vpc:listPorts`/`vpc:showPort` are only required for `huawei_diagnose_port_connectivity`
> and the delete-subnet pre-check. `vpc:listSecurityGroups`/`vpc:showSecurityGroup` are
> required for the security-group rule check inside port diagnosis.

## 2. Manage (R2 — create / update VPC and subnet)

Covers: `huawei_create_vpc`, `huawei_create_subnet`, `huawei_update_vpc`, `huawei_update_subnet`.

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:createVpc",
        "vpc:updateVpc",
        "vpc:createSubnet",
        "vpc:updateSubnet",
        "vpc:listVpcs",
        "vpc:listSubnets"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 3. Manage (R1 — delete VPC and subnet)

Covers: `huawei_delete_vpc`, `huawei_delete_subnet`. The pre-checks
(`vpc:listSubnets` for VPC emptiness, `vpc:listPorts` for subnet emptiness) are included.

```json
{
  "Version": "1.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:deleteVpc",
        "vpc:deleteSubnet",
        "vpc:listVpcs",
        "vpc:listSubnets",
        "vpc:listPorts",
        "vpc:showVpc",
        "vpc:showSubnet"
      ],
      "Resource": ["*"]
    }
  ]
}
```

## 4. Security notes

- **Never grant** permissions beyond the three groups above to the agent principal.
  In particular, do not grant `vpc:createRouteTable`, `vpc:deleteRouteTable`,
  `vpc:associateRouteTable`, `vpc:updateRouteTable` — route tables are read-only in this skill.
- For stronger isolation, restrict `Resource` to specific VPCs/subnets where the service
  supports resource-level authorization (IAM resource tags); `"Resource": ["*"]` is shown
  for simplicity.
- Prefer custom roles scoped to the **project** that owns the networks; never use
  `Tenant Administrator` or `VPC Administrator` for agent execution.
- `vpc:deleteVpc` / `vpc:deleteSubnet` are destructive and irreversible: consider granting
  them only in a restricted role used with explicit human confirmation.

## 5. Reference

- VPC permissions: https://support.huaweicloud.com/usermanual-vpc/vpc_01_0008.html
- IAM policy management: https://support.huaweicloud.com/usermanual-iam/iam_01_0017.html