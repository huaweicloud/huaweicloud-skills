---
name: huawei-cloud-smn-dms-message
description: |
  Manage Huawei Cloud SMN (Simple Message Notification) topics, subscriptions, message templates and message publishing, and manage DMS (Distributed Message Service) Kafka/RabbitMQ/RocketMQ instances and Kafka topics. 15 built-in actions cover query (list topics/subscriptions/message templates/DMS instances/Kafka topics), diagnosis (subscription confirmation status, DMS instance health & capacity), management (create topic, add subscription, create message template, publish message, create DMS instance) and destructive operations (delete SMN topic, confirm subscription, delete DMS instance). KooCLI has no DMS command; the three engine services are the only DMS entry points. Supports both AK/SK and local KooCLI profile authentication.
  Use this skill when the user wants to: (1) list or create SMN topics and subscriptions, (2) send or diagnose notifications, (3) inspect SMN subscription confirmation status, (4) list, create, or delete DMS Kafka/RabbitMQ/RocketMQ instances, (5) list Kafka topics, (6) analyze DMS instance health or capacity.
  Triggers include: "SMN", "SMN主题", "消息通知", "subscribe", "topic", "发布消息", "推送消息", "notification", "DMS", "Kafka", "RabbitMQ", "RocketMQ", "消息队列", "实例", "订阅", "消息模板", "MQS"
tags: ["smn", "dms", "kafka", "rabbitmq", "rocketmq", "notification"]
---

# Huawei Cloud SMN / DMS Messaging Skill

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
hcloud SMN ListTopics --cli-region={region} --limit=20 --offset=0
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
hcloud SMN ListSubscriptions --cli-region={region} --limit=20 --offset=0
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region |
| `--protocol` | No | `http` \| `https` \| `sms` \| `email` \| `functionstage` |
| `--status` | No | `0`=unconfirmed `1`=confirmed `2`=no confirm `3`=cancelled `4`=deleted |
| `--limit` / `--offset` | No | Pagination |

#### huawei_list_smn_message_templates — List SMN message templates

```bash
hcloud SMN ListMessageTemplates --cli-region={region} --limit=20
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region |
| `--message_template_name` | No | Template name, 1–64 chars |
| `--protocol` | No | `default` \| `email` \| `sms` \| `functionstage` \| `http` \| `https` |

#### huawei_list_dms_instances — List DMS instances by engine

```bash
# Kafka
hcloud Kafka ListInstances --engine=kafka --cli-region={region} --limit=20 --offset=0
# RabbitMQ
hcloud RabbitMQ ListInstancesDetails --engine=rabbitmq --cli-region={region} --limit=20 --offset=0
# RocketMQ
hcloud RocketMQ ListInstances --engine=rocketmq --cli-region={region} --limit=20 --offset=0
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--engine` | Yes | `kafka` \| `rabbitmq` \| `rocketmq` (fixed per engine) |
| `--cli-region` | Yes (auto) | Region |
| `--status` | No | `RUNNING` \| `CREATING` \| `ERROR` \| `DELETING` \| ... |

#### huawei_list_dms_topics — List Kafka topics of an instance

```bash
hcloud Kafka ListInstanceTopics --instance_id={instance_id} --cli-region={region} --limit=20 --offset=0
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance_id` | Yes | Kafka instance ID (from `huawei_list_dms_instances`) |
| `--cli-region` | Yes (auto) | Region |

### R3 — Diagnose (auto-execute)

#### huawei_analyze_smn_subscription_confirmation — Subscription confirmation status analysis

```bash
hcloud SMN ListSubscriptions --cli-region={region}
```

Analyze the result: `status=0` subscriptions have **not been confirmed** — HTTP/HTTPS endpoints must implement the ping-back confirmation, email endpoints require the user to click the confirmation link. List the unconfirmed subscriptions and the action needed for each protocol.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--cli-region` | Yes (auto) | Region |
| `--topic_urn` | No | Analyze a single topic |
| `--protocol` | No | Focus on one protocol |

#### huawei_analyze_dms_instance_status — DMS instance health & capacity analysis

```bash
hcloud Kafka ListInstances --engine=kafka --cli-region={region}     # then per instance:
hcloud Kafka ShowInstance --instance_id={instance_id} --cli-region={region}
```

Analyze: instance status (`RUNNING` healthy; `ERROR`/`FROZEN`/`CREATEFAILED` unhealthy), storage usage, restart/maintain state, broker count. Follow the same pattern with `RabbitMQ`/`RocketMQ` for other engines.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--engine` | Yes | Engine |
| `--instance_id` | Yes (for `ShowInstance`) | Instance ID |

### R2 — Manage (preview + confirm)

#### huawei_create_smn_topic — Create a topic

```bash
hcloud SMN CreateTopic --name={name} --display_name={display_name} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--name` | Yes | 1–255 chars, letters/digits/`-`/`_`, must start with letter/digit |
| `--display_name` | Yes | Display name shown as sender in email (may be empty string) |
| `--enterprise_project_id` | No | Enterprise project |

#### huawei_add_smn_subscription — Add a subscription to a topic

```bash
hcloud SMN AddSubscription --topic_urn={topic_urn} --protocol={protocol} --endpoint={endpoint} --cli-region={region}
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
hcloud SMN CreateMessageTemplate --message_template_name={message_template_name} --content={content} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--message_template_name` | Yes | 1–64 chars, start with letter/digit |
| `--content` | Yes | Plain-text template content, ≤256 KB; supports `${variable}` placeholders |
| `--protocol` | No | `default` \| `email` \| `sms` \| `functionstage` \| `http` \| `https` |

> ⚠️ **SMS is billed per delivered message** — publishing via SMS-inclined templates incurs per-message charges.

#### huawei_publish_smn_message — Publish a message to a topic

```bash
hcloud SMN PublishMessage --topic_urn={topic_urn} --message={message} --cli-region={region}
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
hcloud Kafka CreatePostPaidKafkaInstance --name={name} --engine=kafka --engine_version={engine_version} --product_id={product_id} --available_zones.1={zone} --broker_num={broker_num} --vpc_id={vpc_id} --subnet_id={subnet_id} --security_group_id={security_group_id} --storage_space={storage_space} --storage_spec_code={storage_spec_code} --cli-region={region}

# RabbitMQ
hcloud RabbitMQ CreatePostPaidInstanceByEngine --name={name} --engine=rabbitmq --engine_version={engine_version} --product_id={product_id} --available_zones.1={zone} --access_user={access_user} --password={password} --vpc_id={vpc_id} --subnet_id={subnet_id} --security_group_id={security_group_id} --storage_space={storage_space} --storage_spec_code={storage_spec_code} --cli-region={region}

# RocketMQ
hcloud RocketMQ CreateInstanceByEngine --name={name} --engine=rocketmq --engine_version={engine_version} --product_id={product_id} --available_zones.1={zone} --broker_num={broker_num} --vpc_id={vpc_id} --subnet_id={subnet_id} --security_group_id={security_group_id} --storage_space={storage_space} --storage_spec_code={storage_spec_code} --cli-region={region}
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
hcloud SMN DeleteTopic --topic_urn={topic_urn} --cli-region={region}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--topic_urn` | Yes | Topic resource identifier |

> ⚠️ Deleting a topic deletes **all subscriptions and message history** for it — require explicit user confirmation including the topic name.

#### huawei_confirm_smn_subscription — Confirm a pending subscription

```bash
hcloud SMN ConfirmSubscription --token={token} --cli-region={region}
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
hcloud Kafka DeleteInstance --instance_id={instance_id} --cli-region={region}
# RabbitMQ
hcloud RabbitMQ DeleteInstance --instance_id={instance_id} --cli-region={region}
# RocketMQ
hcloud RocketMQ DeleteInstance --instance_id={instance_id} --cli-region={region}
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
