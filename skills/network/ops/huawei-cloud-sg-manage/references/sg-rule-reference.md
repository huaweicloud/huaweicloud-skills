# Security Group Rule Reference

A security group (安全组) is a VPC subnet-level stateful firewall. Traffic is evaluated
against its rules **in priority order**; the first matching rule decides the verdict.
VPC's default behaviour for traffic that matches no rule is **DENY**.

## Rule fields (VPC v3 API)

| Field | Values | Meaning |
| ----- | ------ | ------- |
| `direction` | `ingress` / `egress` | 入方向 (inbound) / 出方向 (outbound) |
| `ethertype` | `IPv4` / `IPv6` | Address family |
| `protocol` | `tcp` / `udp` / `icmp` / `icmpv6` / `any` | L4 protocol; `any` = all |
| `multiport` | `"22"`, `"22-25"`, `"22,80,443-450"`, empty | Ports; empty = all ports |
| `remote_ip_prefix` | CIDR, e.g. `10.0.0.0/8` | Remote address range |
| `remote_group_id` | security group id | Remote = any instance attached to that SG |
| `remote_address_group_id` | address group id | Remote = members of the address group |
| `action` | `allow` / `deny` | Verdict when the rule matches |
| `priority` | 1..65535 | Lower number = higher priority (default 1) |
| `enabled` | `true` / `false` | Disabled rules are ignored |
| `description` | string | Optional note |

Exactly one remote selector applies: `remote_ip_prefix` XOR `remote_group_id` XOR
`remote_address_group_id`; a rule with none of them has no remote restriction (matches
everything).

## Default security group

A new default security group ships built-in rules that allow traffic **within the group**
(ingress + egress, IPv4 + IPv6, priority 1). This is why two instances sharing the default
SG can talk to each other even though an explicit rule for their CIDR does not exist.

## Matching semantics used by the diagnose/conflict/audit engine

1. Only `enabled=true` rules are considered.
2. A rule matches a probe `(direction, protocol, port, remote)` when direction, protocol,
   ports and remote all match (`any`/empty wildcard matches everything).
3. Among matching rules the one with the **lowest numerical priority** wins; ties are
   broken by rule id.
4. The winning rule's `action` is the verdict: ALLOW or DENY.
5. No matching enabled rule → default DENY (unless covered by the default-SG in-group
   rules — see above).
6. Rules whose remote is `remote_group_id` / `remote_address_group_id` cannot be resolved
   to concrete IPs from SG-rule APIs alone → reported as INDETERMINATE in diagnosis.

## Priority pitfalls

- A broad `allow` with priority 1 makes every overlapping `deny` ineffective — the audit
  flags these as warnings.
- Two allow rules with the same action and overlapping scopes make the lower-priority one
  redundant (shadowed) — the conflict analysis flags them.