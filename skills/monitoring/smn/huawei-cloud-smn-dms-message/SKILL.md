---
name: huawei-cloud-smn-dms-message
description: |
  Manage Huawei Cloud SMN (Simple Message Notification) topics, subscriptions, message templates and message publishing, and manage DMS (Distributed Message Service) Kafka/RabbitMQ/RocketMQ instances and Kafka topics. 15 built-in actions cover query (list topics/subscriptions/message templates/DMS instances/Kafka topics), diagnosis (subscription confirmation status, DMS instance health & capacity), management (create topic, add subscription, create message template, publish message, create DMS instance) and destructive operations (delete SMN topic, confirm subscription, delete DMS instance). KooCLI has no DMS command; the three engine services are the only DMS entry points. Supports both AK/SK and local KooCLI profile authentication.
  Use this skill when the user wants to: (1) list or create SMN topics and subscriptions, (2) send or diagnose notifications, (3) inspect SMN subscription confirmation status, (4) list, create, or delete DMS Kafka/RabbitMQ/RocketMQ instances, (5) list Kafka topics, (6) analyze DMS instance health or capacity.
  Triggers include: "SMN", "SMN主题", "消息通知", "subscribe", "topic", "发布消息", "推送消息", "notification", "DMS", "Kafka", "RabbitMQ", "RocketMQ", "消息队列", "DMS实例", "Kafka实例", "RabbitMQ实例", "RocketMQ实例", "订阅", "消息模板", "MQS"
tags: ["smn", "dms", "kafka", "rabbitmq", "rocketmq"]
---

# Huawei Cloud SMN / DMS Messaging Skill

<!-- cli-install-version: 3.9.0 -->
## Step 0: Ensure skill-quality-cli (required; installed on first use)

**Mandatory**: before running any `huawei_*` action, ensure `skill-quality-cli` is installed
and available — every execution reports quality telemetry through it. This step MUST be
triggered on every execution of this skill (`ensure_cli.sh` is idempotent and exits
silently when everything is ready).

```bash
# Ensure ~/.local/bin is on PATH (where skill-quality-cli is installed)
export PATH="$HOME/.local/bin:$PATH"

# Ensure skill-quality-cli is ready (idempotent: installs a pinned version with SHA256
# verification only if absent; no auto-upgrade — upgrade manually with `skill-quality-cli upgrade`)
bash scripts/ensure_cli.sh

# Verify it works
skill-quality-cli version
```

> **供应链披露**: `ensure_cli.sh` 安装固定版本（默认 v1.1.8）并做 SHA256 白名单校验，
> 未命中校验和一律拒绝安装；下载前还会检查安装目录合法性（防目录穿越/通配符注入）。
> 安装位置 `~/.local/bin`，不修改系统服务或全局配置。失败（离线/校验失败）时显式
> 警告后静默降级——**绝不阻塞业务流**。关闭遥测上报：`export SKILL_QUALITY_REPORT=0`。

## Overview

This skill provides 15 `huawei_*` actions for Huawei Cloud **SMN** (Simple Message Notification) and **DMS** (Distributed Message Service). Only Huawei Cloud is supported; operations against other cloud providers are out of scope. SMN handles pub/sub notifications (topic → subscription → message). DMS is the product umbrella for three message-queue engines: **Kafka**, **RabbitMQ**, **RocketMQ**.

**Critical architecture rule:** KooCLI has **no DMS service** of its own. DMS is exposed as three independent services: `Kafka`, `RabbitMQ`, `RocketMQ` (callable as `hcloud <service>`). Every DMS operation must first determine the engine, then call the matching service. Never issue a DMS command.

```text
┌────────────────┐     ┌────────────────┐     ┌─────────────────────────────┐
│ hcloud SMN     │     │ hcloud Kafka   │     │ hcloud RabbitMQ / RocketMQ  │
│ topics/subs/   │     │ instances &    │     │ instances & delete ops      │
│ templates/msgs │     │ topics         │     │                             │
└────────────────┘     └────────────────┘     └─────────────────────────────┘
```

## Precedence of Action Families (Risk-Based Execution)

| Family | Actions | Execution | Risk |
|--------|---------|-----------|------|
| **R3 — Query / Diagnose** (7) | `huawei_list_smn_topics`, `huawei_list_smn_subscriptions`, `huawei_list_smn_message_templates`, `huawei_list_dms_instances`, `huawei_list_dms_topics`, `huawei_analyze_smn_subscription_confirmation`, `huawei_analyze_dms_instance_status` | **Auto-execute** (read-only) | No |
| **R2 — Manage** (5) | `huawei_create_smn_topic`, `huawei_add_smn_subscription`, `huawei_create_smn_message_template`, `huawei_publish_smn_message`, `huawei_create_dms_instance` | **Preview command + ask user to confirm** before running | Yes (creates resources / spends money) |
| **R1 — Destructive** (3) | `huawei_delete_smn_topic`, `huawei_confirm_smn_subscription`, `huawei_delete_dms_instance` | **End-to-end confirmation**: present full command + describe irreversible impact, require explicit user approval | High (deletes/changes state, SMS/email side effects) |

## Action Dispatch (Script Executor)

Every `huawei_*` action is **dispatched through the bundled script**
`scripts/smn_dms_skill.py` — the script selects the right KooCLI service/operation,
injects `--cli-region`, and **hard-binds the quality report** (success / `biz_fail`
U02 / `sys_fail` B01) on every run. Execution is identical to the wrapped
`skill-quality-cli run` commands in "Core Commands" below; the script form is the
unified script/agent (wrapper) executor entry point:

```bash
# R3 — Query / Diagnose (read-only, auto-execute)
python3 scripts/smn_dms_skill.py huawei_list_smn_topics --region={region}
python3 scripts/smn_dms_skill.py huawei_list_smn_subscriptions --region={region}
python3 scripts/smn_dms_skill.py huawei_list_smn_message_templates --region={region}
python3 scripts/smn_dms_skill.py huawei_list_dms_instances --engine=kafka --region={region}
python3 scripts/smn_dms_skill.py huawei_list_dms_topics --instance_id={instance_id} --preview
python3 scripts/smn_dms_skill.py huawei_analyze_smn_subscription_confirmation --region={region}
python3 scripts/smn_dms_skill.py huawei_analyze_dms_instance_status --engine=kafka --region={region}

# R2 — Manage (preview + confirm; --preview prints the command without executing)
python3 scripts/smn_dms_skill.py huawei_create_smn_topic --name=test-topic --display_name=test --preview
python3 scripts/smn_dms_skill.py huawei_add_smn_subscription --topic_urn=urn:smn:test --protocol=email --endpoint=test@example.com --preview
python3 scripts/smn_dms_skill.py huawei_create_smn_message_template --message_template_name=test --content=hello --preview
python3 scripts/smn_dms_skill.py huawei_publish_smn_message --topic_urn=urn:smn:test --message=hello --preview
python3 scripts/smn_dms_skill.py huawei_create_dms_instance --engine=kafka --name=test --engine_version=2.7 --product_id=test --available_zones=cn-north-4a --broker_num=3 --vpc_id=vpc-test --subnet_id=subnet-test --security_group_id=sg-test --storage_space=100 --storage_spec_code=dms.physical.storage.high.v2 --preview

# R1 — Destructive (end-to-end confirm; --preview prints the command without executing)
python3 scripts/smn_dms_skill.py huawei_delete_smn_topic --topic_urn=urn:smn:test --preview
python3 scripts/smn_dms_skill.py huawei_confirm_smn_subscription --token=test-token --preview
python3 scripts/smn_dms_skill.py huawei_delete_dms_instance --engine=kafka --instance_id=test-id --preview
```

- `{region}` is auto-resolved (default `cn-north-4`); R2/R1 commands run with `--preview` by default and only execute for real after the user confirms the shown command.
- `huawei_list_dms_topics --instance_id={instance_id}` uses `--preview` because it requires a real Kafka instance ID; substitute the ID (from `huawei_list_dms_instances`) to run it live.

## Prerequisites

> **Prerequisite check 1/3: KooCLI (hcloud) 2.x+ installed and authenticated**

Install and configure the Huawei Cloud KooCLI:

```bash
curl -O https://cn-north-4-hcli.obs.cn-north-4.myhuaweicloud.com/hcli_install.sh && bash hcli_install.sh
# verify: hcloud --help should print the KooCLI version banner
```

> **Prerequisite check 2/3: Authentication — AK/SK or hcloud profile (either is supported)**

| Auth mode | How to configure | When to use |
|-----------|------------------|-------------|
| **Local hcloud profile** | Run `hcloud configure set --cli-mode=AKSK --cli-region=cn-north-4` interactively, then enter AK/SK | Recommended; commands run exactly as documented below |
| **AK/SK environment variables** | `export HUAWEICLOUD_SDK_AK=<ak>` and `export HUAWEICLOUD_SDK_SK=<sk>` (optional `HUAWEICLOUD_SDK_SECURITY_TOKEN`) | CI / ephemeral runtimes; KooCLI reads these automatically |

Verify a profile exists (values are never printed):

```bash
# hcloud configure list | head -5   (only metadata is shown, keys are masked)
```

`--project_id` and `--cli-region` are **auto-resolved** by KooCLI from the profile / authentication info; you normally do not pass them.

> **Prerequisite check 3/3: IAM permissions**

The account must hold the SMN and DMS permissions listed in [references/iam-policies.md](references/iam-policies.md) (e.g., `SMN Administrator`, `DMS User`, or least-privilege policies from the same file).

- See [references/cli-installation-guide.md](references/cli-installation-guide.md) for full install/auth details.
- See [references/verification-method.md](references/verification-method.md) to verify the skill works.

## Authentication

> **Security rules (must be followed):**
>
> - Prohibited from reading, echoing, or printing AK/SK values.
> - Prohibited from asking the user to input AK/SK directly in the conversation.
> - Prohibited from using `hcloud configure set` with plaintext credential values pasted in chat.
> - Prohibited from hardcoding AK/SK in scripts or command lines.
> - Allowed: reference the configured `hcloud` profile, or use `HUAWEICLOUD_SDK_AK` / `HUAWEICLOUD_SDK_SK` environment variables set out-of-band.

If the user offers AK/SK inline, refuse politely and point them to the two auth modes above.

## Workflow

1. **Determine scope** — SMN or DMS? For DMS, ask/confirm the engine (`kafka`, `rabbitmq`, `rocketmq`) and choose the matching KooCLI service.
2. **Route the action** to one of the 15 `huawei_*` actions below.
3. **Risk gate:**
   - R3 query/diagnose → run immediately, summarize results.
   - R2 manage → build the exact `hcloud` command, show it to the user, and wait for confirmation before executing.
   - R1 destructive → show the exact command with its impact (what will be deleted / which endpoint will receive a confirmation), require explicit end-to-end confirmation, then execute.
4. **Interpret output** — SMN commands return JSON; subscription `status` field: `0`=unconfirmed, `1`=confirmed, `2`=no confirmation required, `3`=cancelled, `4`=deleted. DMS `status` values include `RUNNING` (healthy) and `CREATING`/`ERROR`/`DELETING`/`FROZEN`/`EXTENDING` etc.
5. **Report** — summarize created/updated/removed resources, and confirm no output contains credentials.

## Core Commands

> **Always run `hcloud <Service> <Operation> --help` first** to re-confirm parameter names before constructing a command, especially for create operations.

### R3 — Query (auto-execute)

#### huawei_list_smn_topics — List SMN topics

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN ListTopics --cli-region={region} --limit=20 --offset=0
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region, agent fills automatically |
| `--limit` | No | 1–100, default 100 |
| `--offset` | No | Page offset, default 0 |
| `--name` | No | Exact topic name match |
| `--fuzzy_name` | No | Fuzzy topic name search |

#### huawei_list_smn_subscriptions — List SMN subscriptions

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN ListSubscriptions --cli-region={region} --limit=20 --offset=0
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region |
| `--protocol` | No | `http` \| `https` \| `sms` \| `email` \| `functionstage` |
| `--status` | No | `0`=unconfirmed `1`=confirmed `2`=no confirm `3`=cancelled `4`=deleted |
| `--limit` / `--offset` | No | Pagination |

#### huawei_list_smn_message_templates — List SMN message templates

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN ListMessageTemplates --cli-region={region} --limit=20
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region |
| `--message_template_name` | No | Template name, 1–64 chars |
| `--protocol` | No | `default` \| `email` \| `sms` \| `functionstage` \| `http` \| `https` |

#### huawei_list_dms_instances — List DMS instances by engine

```bash
# Kafka
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud Kafka ListInstances --engine=kafka --cli-region={region} --limit=20 --offset=0
# RabbitMQ
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud RabbitMQ ListInstancesDetails --engine=rabbitmq --cli-region={region} --limit=20 --offset=0
# RocketMQ
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud RocketMQ ListInstances --engine=rocketmq --cli-region={region} --limit=20 --offset=0
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--engine` | Yes | `kafka` \| `rabbitmq` \| `rocketmq` (fixed per engine) |
| `--cli-region` | Yes (auto) | Region |
| `--status` | No | `RUNNING` \| `CREATING` \| `ERROR` \| `DELETING` \| ... |

#### huawei_list_dms_topics — List Kafka topics of an instance

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud Kafka ListInstanceTopics --instance_id={instance_id} --cli-region={region} --limit=20 --offset=0
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | Yes | Kafka instance ID (from `huawei_list_dms_instances`) |
| `--cli-region` | Yes (auto) | Region |

### R3 — Diagnose (auto-execute)

#### huawei_analyze_smn_subscription_confirmation — Subscription confirmation status analysis

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN ListSubscriptions --cli-region={region}
```

Analyze the result: `status=0` subscriptions have **not been confirmed** — HTTP/HTTPS endpoints must implement the ping-back confirmation, email endpoints require the user to click the confirmation link. List the unconfirmed subscriptions and the action needed for each protocol.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region |
| `--topic_urn` | No | Analyze a single topic |
| `--protocol` | No | Focus on one protocol |

#### huawei_analyze_dms_instance_status — DMS instance health & capacity analysis

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud Kafka ListInstances --engine=kafka --cli-region={region}     # then per instance:
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud Kafka ShowInstance --instance_id={instance_id} --cli-region={region}
```

Analyze: instance status (`RUNNING` healthy; `ERROR`/`FROZEN`/`CREATEFAILED` unhealthy), storage usage, restart/maintain state, broker count. Follow the same pattern with `RabbitMQ`/`RocketMQ` for other engines.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--engine` | Yes | Engine |
| `--instance_id` | Yes (for `ShowInstance`) | Instance ID |

### R2 — Manage (preview + confirm)

#### huawei_create_smn_topic — Create a topic

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN CreateTopic --name={name} --display_name={display_name} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--name` | Yes | 1–255 chars, letters/digits/`-`/`_`, must start with letter/digit |
| `--display_name` | Yes | Display name shown as sender in email (may be empty string) |
| `--enterprise_project_id` | No | Enterprise project |

#### huawei_add_smn_subscription — Add a subscription to a topic

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN AddSubscription --topic_urn={topic_urn} --protocol={protocol} --endpoint={endpoint} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--topic_urn` | Yes | Topic resource identifier |
| `--protocol` | Yes | `email` \| `sms` \| `http` \| `https` \| `functionstage` \| `dingding` \| `wechat` \| `feishu` \| `welink` |
| `--endpoint` | Yes | Per protocol: email address, phone, `http(s)://` URL, FunctionGraph ARN, chatbot webhook |
| `--remark` | No | Remarks, ≤128 bytes |

> ⚠️ **After adding, HTTP/HTTPS subscriptions need endpoint ping-back confirmation; email subscriptions need the user to click the confirmation link** — the subscription stays `status=0` until then.

#### huawei_create_smn_message_template — Create a message template

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN CreateMessageTemplate --message_template_name={message_template_name} --content={content} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--message_template_name` | Yes | 1–64 chars, start with letter/digit |
| `--content` | Yes | Plain-text template content, ≤256 KB; supports `${variable}` placeholders |
| `--protocol` | No | `default` \| `email` \| `sms` \| `functionstage` \| `http` \| `https` |

> ⚠️ **SMS is billed per delivered message** — publishing via SMS-inclined templates incurs per-message charges.

#### huawei_publish_smn_message — Publish a message to a topic

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN PublishMessage --topic_urn={topic_urn} --message={message} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--topic_urn` | Yes | Topic resource identifier |
| `--message` | Yes (or `--message_structure`/`--message_template_name`) | ≤256 KB; SMS ≤490 chars, no `[]` |
| `--subject` | No | Email subject, ≤512 bytes |
| `--message_template_name` | No | Publish using a template |
| `--tags.*` | No | Template variable substitution, e.g. `--tags.name=value` |
| `--time_to_live` | No | Retention ≤86400 s, default 3600 |

#### huawei_create_dms_instance — Create a DMS instance (by engine)

```bash
# Kafka
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud Kafka CreatePostPaidKafkaInstance --name={name} --engine=kafka --engine_version={engine_version} --product_id={product_id} --available_zones.1={zone} --broker_num={broker_num} --vpc_id={vpc_id} --subnet_id={subnet_id} --security_group_id={security_group_id} --storage_space={storage_space} --storage_spec_code={storage_spec_code} --cli-region={region}

# RabbitMQ
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud RabbitMQ CreatePostPaidInstanceByEngine --name={name} --engine=rabbitmq --engine_version={engine_version} --product_id={product_id} --available_zones.1={zone} --access_user={access_user} --password={password} --vpc_id={vpc_id} --subnet_id={subnet_id} --security_group_id={security_group_id} --storage_space={storage_space} --storage_spec_code={storage_spec_code} --cli-region={region}

# RocketMQ
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud RocketMQ CreateInstanceByEngine --name={name} --engine=rocketmq --engine_version={engine_version} --product_id={product_id} --available_zones.1={zone} --broker_num={broker_num} --vpc_id={vpc_id} --subnet_id={subnet_id} --security_group_id={security_group_id} --storage_space={storage_space} --storage_spec_code={storage_spec_code} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--engine` | Yes | `kafka` \| `rabbitmq` \| `rocketmq` |
| `--name` | Yes | Instance name |
| `--engine_version` | Yes | e.g. Kafka `2.7`/`3.3`, RabbitMQ `3.8.35`, RocketMQ `4.8.0` |
| `--product_id` | Yes | Instance flavor published with engine/version (see `ListEngineProducts`) |
| `--available_zones.1` | Yes | AZ ID |
| `--vpc_id` / `--subnet_id` / `--security_group_id` | Yes | Networking |
| `--storage_space` | Yes | Storage in GB |
| `--storage_spec_code` | Yes | `dms.physical.storage.high.v2` \| `dms.physical.storage.ultra.v2` \| `dms.physical.storage.general` \| `dms.physical.storage.extreme` |
| `--broker_num` | Yes (Kafka/RocketMQ) | Number of brokers |
| `--access_user` / `--password` | Yes (RabbitMQ) | RabbitMQ console credentials |

> Run `hcloud Kafka ListEngineProducts --engine=kafka --cli-region={region}` to get valid `--product_id` / `--engine_version` pairs before creating. Preview the full command and confirm the estimated cost with the user before running.

### R1 — Destructive (end-to-end confirm)

#### huawei_delete_smn_topic — Delete a topic (and its subscriptions)

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN DeleteTopic --topic_urn={topic_urn} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--topic_urn` | Yes | Topic resource identifier |

> ⚠️ Deleting a topic deletes **all subscriptions and message history** for it — require explicit user confirmation including the topic name.

#### huawei_confirm_smn_subscription — Confirm a pending subscription

```bash
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud SMN ConfirmSubscription --token={token} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--token` | Yes | Confirmation token (from the HTTP ping-back request body or the email confirmation link) |
| `--topic_urn` | No | Topic resource identifier |
| `--endpoint` | No | Subscription endpoint IP |

> The token normally arrives at the subscribing endpoint (HTTP/HTTPS ping-back body, or the URL in the email confirmation link). The agent must obtain it from the user/endpoint and show the exact confirmation action before running.

#### huawei_delete_dms_instance — Delete a DMS instance

```bash
# Kafka
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud Kafka DeleteInstance --instance_id={instance_id} --cli-region={region}
# RabbitMQ
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud RabbitMQ DeleteInstance --instance_id={instance_id} --cli-region={region}
# RocketMQ
skill-quality-cli run --skill-name huawei-cloud-smn-dms-message -- hcloud RocketMQ DeleteInstance --instance_id={instance_id} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | Yes | DMS instance ID |
| `--cli-region` | Yes (auto) | Region |

> ⚠️ Deleting a message-queue instance is **irreversible** and deletes all stored messages (topics, queues, offsets). Confirm instance ID, engine, and data-loss impact with the user explicitly before running.

## Parameter Confirmation

- All commands use the exact parameter spelling verified against `hcloud <Service> <Operation> --help`. Do not invent parameter names.
- `--cli-region` and `--project_id` are resolved automatically from the hcloud profile / authentication; no user input needed.
- Required parameters are marked "Yes" in each table; optional parameters are described in each table and only added to a command when a value is needed.
- `--help` is the source of truth: run `hcloud <Service> <Operation> --cli-region={region} --help` before executing any non-trivial command.

## KooCLI Command Format Standard

The generic invocation shape is `hcloud <Service> <Operation> --cli-region={region} [--key=value ...]`
— this is a **format description only**: `<...>` and `[...]` are placeholders, never executed verbatim.

| Feature | Convention | Example |
|---------|-----------|---------|
| Service name | Actual KooCLI service (case matters): `SMN`, `Kafka`, `RabbitMQ`, `RocketMQ`. **No `DMS` service exists** | `hcloud <Service> <Operation>` |
| Operation name | PascalCase | `ListInstanceTopics` |
| Region | `--cli-region={region}` always included | `--cli-region=cn-north-4` |
| Scalar param | `--param=value` | `--instance_id=xxx` |
| Indexed param | `--param.N=value` | `--available_zones.1=cn-north-4a` |

## RAM / Capacity Notes

- SMN topic `display_name` is required by the API but can be an empty string; unknown defaults tend to be rejected by parameter validation — always pass `--display_name` explicitly on `CreateTopic`.
- Kafka topic listing requires an instance ID; keep instance IDs from `huawei_list_dms_instances` output for reuse.
- Email/SMS/FunctionGraph notification endpoints each have protocol-specific validation; confirm the endpoint format before `AddSubscription`.

## Reference Documents

- [references/iam-policies.md](references/iam-policies.md) — least-privilege IAM policies (required)
- [references/cli-installation-guide.md](references/cli-installation-guide.md) — KooCLI install + auth setup (required)
- [references/verification-method.md](references/verification-method.md) — how to verify this skill (recommended)
- [references/dataflow-diagram.md](references/dataflow-diagram.md) — end-to-end data flow (recommended)
- [references/acceptance-criteria.md](references/acceptance-criteria.md) — acceptance checks (recommended)
- [references/engine-operation-reference.md](references/engine-operation-reference.md) — full SMN + DMS engine operation catalog (recommended)
- [references/security-audit-guide.md](references/security-audit-guide.md) — security audit how-to (recommended)

<!-- cli-inject-version: 3.9.0 -->
## Quality Reporting (Unified CLI)

> CLI installation: see "Step 0: Ensure skill-quality-cli" at the top of this document (idempotent, installs a pinned version with SHA256 verification only if absent).

Report execution quality on every run of this skill, using either mode below. The CLI collects `session_id` / `agent` explicitly (via `--session-id`, `SKILL_QUALITY_SESSION_ID`, or the per-run `.quality_report.json`) — no host session scraping.

> **⚠️ PATH note: the CLI is installed to `~/.local/bin/`, which is NOT always in `$PATH` in some environments. If `skill-quality-cli: command not found` (exit 127) appears, run `export PATH="$HOME/.local/bin:$PATH"` first (ensure_cli.sh does this automatically), then retry; or call the absolute path `~/.local/bin/skill-quality-cli` directly.**

### Mode 1 (recommended, automatic) — wrap the whole execution
For script/command-style skills, wrap the entire command with `run`:
```bash
skill-quality-cli run --skill-name <skill-name> -- <your command>
```

### Mode 2 (multi-step / instruction-style skills)
Report once per step (callable multiple times):
```bash
skill-quality-cli report --skill-name <skill-name> --status <success|sys_fail|biz_fail|cancel>
```

> **⚠️ Mandatory rule: any hcloud command executed by this skill MUST be wrapped with `skill-quality-cli run` — bare hcloud calls are strictly forbidden.**

### CLI installation (pinned version, SHA256-verified)
- **Auto install**: run `bash scripts/ensure_cli.sh` before execution (idempotent, skips if installed; installs the pinned version with SHA256 whitelist verification).
- **No auto-upgrade**: the CLI never upgrades itself at runtime — upgrade manually with `skill-quality-cli upgrade` (or re-run `bash scripts/install_cli.sh` for a manual install).
- **Offline / failure**: installation failures are silent and never block the business flow; the skill degrades gracefully and reporting is skipped.
- **Disable reporting**: set `SKILL_QUALITY_REPORT=0` (opt-out).
- Current version is recorded in `~/.skill-quality/version.json`; both `ensure_cli.sh` and `install_cli.sh` verify SHA256 (fail-closed).
