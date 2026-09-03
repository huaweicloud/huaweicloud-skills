# IAM Policies for HSS Skill

## Least-Privilege Policy

This skill requires HSS read permissions for query operations and HSS write permissions for alert handling.

### Query-Only Policy (Read Operations)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hss:hosts:get",
        "hss:hosts:list",
        "hss:vulnerabilities:get",
        "hss:vulnerabilities:list",
        "hss:baseline:get",
        "hss:baseline:list",
        "hss:events:get",
        "hss:events:list",
        "hss:login:list",
        "hss:risk:get",
        "hss:statistics:get"
      ],
      "Resource": "*"
    }
  ]
}
```

### Full Policy (Read + Alert Handling)

```json
{
  "Version": "1.1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "hss:hosts:get",
        "hss:hosts:list",
        "hss:vulnerabilities:get",
        "hss:vulnerabilities:list",
        "hss:baseline:get",
        "hss:baseline:list",
        "hss:events:get",
        "hss:events:list",
        "hss:events:put",
        "hss:login:list",
        "hss:risk:get",
        "hss:statistics:get",
        "hss:vulnerabilities:put"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- The query-only policy is sufficient for daily inspection (List/Show operations).
- The full policy is required when updating alert handling status (ChangeEvent / ChangeVulStatus).
- HSS permissions are project-level; apply the policy to the target project.
- If using enterprise projects, scope the policy to specific enterprise project IDs.
