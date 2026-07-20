# Risk Rules

## Risk Boundaries

- R3 tools are read-only operations, including alarm query, alarm analysis, action rule query, and mute rule query.
- R2, R1, and R0 tools must show the exact execution action, affected resources, and expected impact before execution.
- R2, R1, and R0 tools must wait for explicit user confirmation before adding `confirm=true` or performing any cloud-side change.
- Cloud resource changes are allowed only through the tools provided by this skill; do not modify alarm rules, action rules, mute rules, or other cloud resources through any out-of-band method.
- Output must never expose AK/SK, tokens, or complete sensitive logs.
- If the user requests scaling, rebooting, draining, or other remediation actions, output recommendations only and hand off to `huawei-cloud-cce-auto-remediation-runner`.

## Analysis Notes

- Do not interpret absence of active alarms as "no problem"; always cross-reference history alarms.
