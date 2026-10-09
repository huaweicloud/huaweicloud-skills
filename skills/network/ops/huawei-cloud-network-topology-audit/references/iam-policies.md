# IAM Policies

## Least-Privilege IAM Policy

This skill is read-only. The minimum IAM permissions required are:

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:vpcs:list",
        "vpc:vpcs:get",
        "vpc:subnets:list",
        "vpc:subnets:get",
        "vpc:securityGroups:list",
        "vpc:securityGroups:get",
        "vpc:routeTables:list",
        "vpc:routeTables:get",
        "vpc:publicIps:list",
        "vpc:publicIps:get",
        "vpc:bandwidths:list",
        "vpc:flowLogs:list",
        "vpc:flowLogs:get",
        "elb:loadbalancers:list",
        "elb:loadbalancers:get",
        "elb:listeners:list",
        "elb:listeners:get",
        "elb:pools:list",
        "elb:pools:get",
        "nat:natGateways:list",
        "nat:natGateways:get",
        "nat:snatRules:list",
        "nat:dnatRules:list",
        "ecs:servers:list",
        "ecs:servers:get",
        "ecs:serverInterfaces:list",
        "rds:instance:list",
        "rds:instance:get",
        "cce:cluster:list",
        "cce:cluster:get",
        "cce:node:list",
        "dcs:instance:list",
        "dcs:instance:get"
      ]
    }
  ]
}
```

## Policy Configuration

1. Go to IAM → Policies → Create Custom Policy
2. Switch to JSON view and paste the policy above
3. Attach the policy to the user/group that runs this skill

## Security Notes

- This policy grants read-only access only. No write operations are allowed.
- Review the policy regularly and remove permissions for services not in use.
- For production environments, consider scoping to specific resource tags or projects.