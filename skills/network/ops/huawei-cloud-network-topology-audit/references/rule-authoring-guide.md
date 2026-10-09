# Rule Authoring Guide

This guide describes how to author, modify, and maintain audit rules in the
`rules/network-audit-rules.yaml` file.

## Rule Structure

Each rule is a YAML object with the following fields:

```yaml
- id: NET-{CATEGORY}-{NNN}
  resource_type: [type1, type2, ...]
  condition: "trigger condition description"
  severity: critical|high|medium|low|info
  description: "what the finding means"
  remediation: "how to fix it"
```

### Field Reference

| Field | Required | Format | Description |
|-------|----------|--------|-------------|
| `id` | Yes | `NET-{CAT}-{NNN}` | Unique identifier. CAT is a 3-letter category code (SEC, ROU, NAT, ELB, VPC, ECS, RDS, DCS, CCE, SUB, EIP). NNN is a zero-padded 3-digit number. |
| `resource_type` | Yes | List of strings | Resource types this rule applies to. See table below for valid types. |
| `condition` | Yes | String (max 120 chars) | Human-readable trigger condition description. Used by the agent to evaluate findings from the topology dataset. |
| `severity` | Yes | Enum | One of critical, high, medium, low, info |
| `description` | Yes | String (max 200 chars) | Description of what the finding means in Chinese. |
| `remediation` | No | String (max 200 chars) | How to fix the issue. If absent, the agent will suggest based on context. |

### Valid Resource Types

| Resource Type | Description | Source |
|---------------|-------------|--------|
| elb_listener | ELB listener configuration | network-query |
| elb_backend | ELB backend pool/member | network-query |
| eip | Elastic IP | network-query |
| nat | NAT gateway | network-query |
| nat_snat | NAT SNAT rules | network-query |
| nat_dnat | NAT DNAT rules | network-query |
| security_group | Security group rules | network-query |
| route_table | Route table entries | network-query |
| vpc | Virtual Private Cloud | network-query |
| subnet | VPC subnet | network-query |
| ecs_nic | ECS network interface | computing-query |
| rds_instance | RDS database instance | rds-smart-service |
| cce_cluster | CCE cluster | cce-cluster-management |
| cce_node | CCE node | cce-cluster-management |
| cce_service | CCE Kubernetes Service | cce-cluster-management |
| cce_ingress | CCE Kubernetes Ingress | cce-cluster-management |
| dcs_instance | DCS Redis/Memcached instance | scripts/query-dcs-instances.py |

## Adding a New Rule

1. Choose a category code and find the next available NNN number.
2. Add the rule to `network-audit-rules.yaml` following the same indentation (2 spaces).
3. Run validation:
   ```bash
   python3 scripts/validate-rules.py rules/network-audit-rules.yaml
   ```
4. Verify the new rule covers the correct resource types.

## Modifying an Existing Rule

- **Do NOT change `id`** once published — downstream audit reports reference rule IDs.
- Update `condition` or `severity` cautiously: changing severity affects report priority sorting.
- Always re-run validation after modification.

## Naming Conventions

- IDs follow `NET-{CAT}-{NNN}` pattern (e.g., NET-SEC-001, NET-ELB-005)
- Category codes are exactly 3 uppercase letters
- Resource types are snake_case, matching the type names in the topology dataset
- Conditions are descriptive Chinese or English phrases

## Best Practices

1. One rule per distinct risk — do not combine multiple conditions into one rule.
2. Broader resource_type coverage produces more comprehensive audits.
3. Use severity accurately — critical should only be for directly exploitable exposures.
4. Write remediation in actionable language — the remediation field guides the fix.
5. If a rule has no auto-detectable condition (requires human judgment), mark with
   `condition_type: manual` in a comment.