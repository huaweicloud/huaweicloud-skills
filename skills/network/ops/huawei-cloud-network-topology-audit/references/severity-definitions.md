# Severity Definitions

Five-level severity classification for audit findings. Every rule in `rules/network-audit-rules.yaml`
must assign one of these five severity levels.

| Level | Name | Description | Examples |
|-------|------|-------------|----------|
| critical | 严重 | Directly exploitable from the internet. Public exposure of management or database ports, 0.0.0.0/0 allow-all rules. | Public SSH (22) access, public database ports (3306/6379), 0.0.0.0/0 all ports |
| high | 高 | High probability of exploitation or missing basic protection. Direct public connectivity without NAT/ELB, management ports open to entire VPC. | ECS with public IP, RDS public access, SG missing on ECS |
| medium | 中 | Improper configuration but not directly exploitable. Overly broad security group rules beyond immediate subnet, missing health checks. | Wide port ranges, HTTP without HTTPS, no health check |
| low | 低 | Minor deviation from best practices. Configuration that reduces auditability or operational safety. | Flow logs disabled, too many SG rules, DHCP disabled |
| info | 提示 | Informational record. Non-critical observations that may be useful for optimization. | EIP idle, single-AZ subnet, egress allow-all |

## Severity Assignment Rules

1. **Authority**: The severity of each rule is predefined in the rule directory. The audit engine
   uses the severity from the matching rule without modification.
2. **Override**: If the audit engine identifies aggravating factors (e.g., a medium-severity rule
   applies to a production-critical resource), it may log a note but must not change the severity
   level.
3. **Sorting**: Audit findings are sorted by severity (critical → high → medium → low → info).
   Within the same severity, findings are sorted by resource ID alphabetically.

## Severity Impact on Reporting

| Severity | Report Section | Highlight Color |
|----------|----------------|-----------------|
| critical | Top of risk list, bold red | 🔴 |
| high | High-priority section | 🟠 |
| medium | Standard section | 🟡 |
| low | Optional section | 🔵 |
| info | Reference section | ⚪ |