# Reference Index

> This directory contains the "reference materials" for the OptVerse code-evolution skill, split into multiple files by responsibility.
> The main document is `SKILL.md`; content is extracted here only when the main document becomes too dense.

## Document list

| File | Purpose |
|---|---|
| [`api-mapping.md`](api-mapping.md) | OptVerse / IAM operations mapped to hcloud CLI |
| [`prerequisites.md`](prerequisites.md) | hcloud installation, credentials, region / project ID, and other prerequisites |
| [`cli-installation-guide.md`](cli-installation-guide.md) | KooCLI (`hcloud`) install + credentials + network verification (deep-dive) |
| [`parameter-format.md`](parameter-format.md) | hcloud parameter forms, nested objects, arrays, JMESPath |
| [`iam-policies.md`](iam-policies.md) | Sub-account permission checklist (required / upload-extension) and recommended system policies |
| [`iam-agency.md`](iam-agency.md) | IAM agency creation and management |
| [`agency-policy.md`](agency-policy.md) | OBS bucket authorization |
| [`language-python.md`](language-python.md) | Python project conventions (evaluator / baseline same file, two running modes) |
| [`language-cpp.md`](language-cpp.md) | C++ project conventions (EVOLVE markers, build_command, command-style evaluator) |
| [`algorithm-workflow.md`](algorithm-workflow.md) | Algorithm project workflow |
| [`evolve-task-workflow.md`](evolve-task-workflow.md) | Evolve task workflow |
| [`result-logs-status.md`](result-logs-status.md) | Results, logs, status |
| [`troubleshooting.md`](troubleshooting.md) | Error-message-grouped troubleshooting |
| [`verification-method.md`](verification-method.md) | Verification checklist |
| [`plan-maintenance.md`](plan-maintenance.md) | **(agent-side, optional)** `plan` / `scratchpad` tool maintenance (multi-step task state-machine; skip if your agent does not have these tools) |

## Recommended reading order 

1. Getting started → [`prerequisites.md`](prerequisites.md) (full context) or [`cli-installation-guide.md`](cli-installation-guide.md) (install only)
2. Permissions → [`iam-policies.md`](iam-policies.md)
3. Default scenario (no OBS upload) → [`language-python.md`](language-python.md) or [`language-cpp.md`](language-cpp.md) → [`algorithm-workflow.md`](algorithm-workflow.md) → [`evolve-task-workflow.md`](evolve-task-workflow.md)
4. *(Optional) When uploading to OBS:* [`iam-agency.md`](iam-agency.md) → [`agency-policy.md`](agency-policy.md)
5. Tuning and debugging → [`parameter-format.md`](parameter-format.md) → [`result-logs-status.md`](result-logs-status.md) → [`troubleshooting.md`](troubleshooting.md)
6. Verification → [`verification-method.md`](verification-method.md)
7. *(agent-side, optional)* [`plan-maintenance.md`](plan-maintenance.md) — only read this if your agent has `plan` / `scratchpad` tools; skip otherwise