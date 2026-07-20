# Risk Rules

- This skill is read-only: it only queries and analyzes metrics. No modifications are made to resources.
- Do not expose sensitive data such as pod names, node IPs, or cluster IDs in public outputs. Use redacted or fictional examples when possible.
- If metric analysis reveals critical resource issues, provide clear recommendations and suggest the appropriate diagnosis skill.
- Keep metric queries time-bounded. The `hours` parameter defaults to 1 to avoid overwhelming results. For historical analysis, use larger time windows but cap at 24 hours.
- Do not make automatic scaling or remediation decisions based solely on metric analysis. Forward to `huawei-cloud-cce-auto-remediation-runner` only if explicitly requested and validated.
- Thresholds (CPU >80%, Memory >85%) are predefined baselines. Actual thresholds may vary by workload SLO. Recommend users to customize thresholds based on their specific requirements.