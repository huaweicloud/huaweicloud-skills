---
name: huawei-cloud-maas-tokens-usage
description: |
  Query Huawei Cloud MaaS (Model as a Service) tokens usage statistics, including total tokens, prompt tokens, completion tokens, total requests, and total errors. Supports preset service, my service, and custom endpoint with time range queries (last 7/14/30 days or custom). Data source is MaaS ShowStatistics API, consistent with console.
  Use this skill when the user wants to: (1) query MaaS token consumption statistics, (2) check MaaS service request counts and error rates, (3) analyze token usage for preset service or my service, (4) monitor MaaS usage over a specific time period.
  Trigger: user mentions "MaaS", "Model as a Service", "tokens usage", "token consumption", "request count", "error count", "MaaS usage", "preset service usage", "completion tokens", "prompt tokens", "MaaS statistics", "模型服务", "令牌用量", "token统计", "token用量", "词元用量", "请求次数", "MaaS监控", "华为云MaaS"
---

# Huawei Cloud MaaS Tokens Usage Monitoring

Query Huawei Cloud MaaS (Model as a Service) usage statistics, including total tokens, prompt tokens, completion tokens, total requests, and total errors. Supports querying last 7 days, 14 days, 30 days, or custom time ranges. Default query type is MaaS preset service.

## Architecture

```
Huawei Cloud MaaS Tokens Usage Monitoring
└── GetMaaSTokensUsage  (via MaaS ShowStatistics API)
```

## Prerequisites

> **Prerequisite check: Python3 + huaweicloudsdkcore required**
> ```bash
> python3 --version  # Python3 >= 3.8
> python3 -c "import huaweicloudsdkcore; print('OK')"  # SDK signing library
> ```
> If SDK not installed: `pip3 install --user huaweicloudsdkcore`

---

## Authentication

> **Prerequisite check: Huawei Cloud credentials required**

> **Security rules (must be followed):**
> - **Prohibited** from reading, echoing, or printing AK/SK values
> - **Prohibited** from asking the user to input AK/SK directly in the conversation
> - **Prohibited** from accepting AK/SK directly provided by the user in the conversation
> - **Only allowed** to read credentials from environment variables or credentials file

> **⚠️ Important: Handling user-provided credentials**
>
> If a user attempts to provide AK/SK directly (e.g., "my AK is xxx, SK is yyy"):
> 1. **Stop immediately** - Do not execute any commands
> 2. **Politely refuse** and return the following message:
>    ```
>    For account security, please do not provide Huawei Cloud Access Key ID and Access Key Secret directly in the conversation.
>
>    Please use one of the following secure methods to configure credentials:
>
>    Method 1: Environment variables
>        export HW_ACCESS_KEY=<your-access-key-id>
>        export HW_SECRET_KEY=<your-access-key-secret>
>
>    Method 2: Credentials file
>        Create a file (e.g., ~/aksk.txt) with AK on line 1, SK on line 2.
>        Then use: --credentials-file ~/aksk.txt
>
>    After configuration is complete, please retry your request.
>    ```
> 3. **Do not continue** executing any Huawei Cloud operations until credentials are configured

> **Check environment variables**:
> ```bash
> echo $HW_ACCESS_KEY  # Check if AK is set
> ```
> If not set, prompt the user to configure credentials using one of the methods above.

---

## IAM Permission Policies

Ensure the IAM user has the required permissions. See [references/iam-policies.md](references/iam-policies.md) for details.

**Minimum required permissions:**
- `modelarts:monitoring:get` — Query MaaS monitoring statistics
- `modelarts:service:get` — Query service information
- `iam:projects:get` — Auto-get project_id

---

## Core Workflow

### Task 1: Query MaaS Tokens Usage Statistics

Query MaaS usage statistics via the ShowStatistics API. Data is consistent with the console.

📄 Detailed steps → [references/task-query-tokens-usage.md](references/task-query-tokens-usage.md)

---

## Verification

See [references/verification-method.md](references/verification-method.md).

**Quick verification:**
```bash
export HW_ACCESS_KEY=<your-ak>
export HW_SECRET_KEY=<your-sk>
python3 scripts/maas_rest_usage_stats.py --from 2026-05-08 --to 2026-05-21
```

---

## References

| Document | Description |
|----------|-------------|
| [task-query-tokens-usage.md](references/task-query-tokens-usage.md) | Task 1: Query tokens usage statistics |
| [related-apis.md](references/related-apis.md) | API and parameter details |
| [iam-policies.md](references/iam-policies.md) | IAM permission policies |
| [maas-metrics.md](references/maas-metrics.md) | MaaS monitoring metrics reference |
| [verification-method.md](references/verification-method.md) | Verification steps |
| [acceptance-criteria.md](references/acceptance-criteria.md) | Correct/error pattern comparison |
| [cli-installation-guide.md](references/cli-installation-guide.md) | Prerequisites installation guide |
| [troubleshooting.md](references/troubleshooting.md) | Troubleshooting and practical experience |
| [maas_rest_usage_stats.py](scripts/maas_rest_usage_stats.py) | ShowStatistics API usage statistics script |
