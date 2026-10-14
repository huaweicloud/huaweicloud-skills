# Risk Rules

## Risk Levels

| Level | Tools | Rule |
|---|---|---|
| R3 | All query and analysis tools | Read-only; may run automatically. |
| R2 | `huawei_create_cce_logconfig`, `huawei_create_lts_access_config` | Preview the exact collection scope and destination, then wait for explicit user confirmation. |
| R1 | `huawei_delete_cce_logconfig`, `huawei_delete_lts_access_config` | Preview the exact existing rule, then wait for explicit user confirmation. |

There are no R0 tools in this skill.

## Mutating Operations

- Creating LogConfig or LTS Access Config resources is allowed only through `huawei_create_cce_logconfig` or `huawei_create_lts_access_config`. The tool must preview first and requires `confirm=true` before it changes collection configuration.
- Deleting LogConfig or LTS Access Config resources is allowed only through `huawei_delete_cce_logconfig` or `huawei_delete_lts_access_config`. The tool must preview the exact target first and requires `confirm=true`.
- Never select a log group or log stream for the user. For read-only application-log queries, a uniquely discovered LogConfig or Access Config may be used automatically; when multiple rules match, present candidates and wait for the user's explicit choice.

## Scope Boundaries

- Do not update workloads, LogConfig resources, log groups, log streams, LTS Access Config resources, or LTS data outside the dedicated confirmed tools.
- If a user asks for remediation based on logs, provide evidence and hand off to the relevant diagnosis or remediation skill instead of changing resources here.

## Credential Security

- Never expose AK/SK, tokens, cluster certificates, or full sensitive log payloads in summaries.
- When `--cli-access-key` and `--cli-secret-key` are supplied, use only those explicit credentials (and the optional `--cli-security-token`) for hcloud and `kubectl cce`; never fall back to a local profile or credential environment variables.
- Prefer time-bounded queries. If no time range is provided, use recent logs and keep limits small.

## Data Privacy

- When logs contain secrets, credentials, cookies, authorization headers, or personal data, summarize the pattern and redact the value.
- Never include raw sensitive values in output or conversation.

## Guardrails

| Guardrail           | Rule                                                                                   | Rationale                                       |
| ------------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------- |
| `max_auto_risk: R1` | Only read operations proceed automatically; mutating operations require `confirm=true` | Prevents unintended LogConfig creation/deletion |

## Confirmation Flow

```
Call without confirm=true → Preview output → User reviews → User confirms → Call with confirm=true
```

**No exceptions**:
- Do not skip preview for "simple" LogConfig or LTS Access Config operations
- Do not call with confirm=true without showing preview first
- Do not assume the preview is correct without user verification
