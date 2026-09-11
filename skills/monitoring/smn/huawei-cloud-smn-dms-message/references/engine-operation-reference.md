# Engine & Operation Reference — SMN + DMS

Complete mapping of the 15 `huawei_*` actions to real KooCLI commands. Parameter names are
verbatim from `hcloud <Service> <Operation> --help` (KooCLI 7.2.12, verified 2026-09-07).

## SMN (service `SMN`, uppercase)

| Action | Operation | Risk | Key params |
|--------|-----------|------|------------|
| `huawei_list_smn_topics` | `ListTopics` | R3 | `--limit`, `--offset`, `--name`, `--fuzzy_name` |
| `huawei_list_smn_subscriptions` | `ListSubscriptions` | R3 | `--protocol`, `--status`, `--endpoint`, `--limit`, `--offset` |
| `huawei_list_smn_message_templates` | `ListMessageTemplates` | R3 | `--message_template_name`, `--protocol`, `--limit`, `--offset` |
| `huawei_analyze_smn_subscription_confirmation` | `ListSubscriptions` (analysis) | R3 | `--protocol`, `--status`, `--topic_urn` |
| `huawei_create_smn_topic` | `CreateTopic` | R2 | `--name`, `--display_name` (required, may be empty) |
| `huawei_add_smn_subscription` | `AddSubscription` | R2 | `--topic_urn`, `--protocol`, `--endpoint` |
| `huawei_create_smn_message_template` | `CreateMessageTemplate` | R2 | `--message_template_name`, `--content` |
| `huawei_publish_smn_message` | `PublishMessage` | R2 | `--topic_urn`, `--message` (or structure/template) |
| `huawei_delete_smn_topic` | `DeleteTopic` | R1 | `--topic_urn` |
| `huawei_confirm_smn_subscription` | `ConfirmSubscription` | R1 | `--token`, `--topic_urn`, `--endpoint` |

### SMN subscription `status` codes

| status | Meaning | Action needed |
|--------|---------|---------------|
| 0 | Not confirmed | HTTP/HTTPS endpoint ping-back or email click-link |
| 1 | Confirmed | None |
| 2 | No confirmation required | None |
| 3 | Cancelled | Re-add if still needed |
| 4 | Deleted | Re-add if still needed |

### SMN alarms

- **HTTP/HTTPS subscription**: after `AddSubscription`, the endpoint receives a ping-back request whose body contains the confirm `token`; call `ConfirmSubscription` with it.
- **Email subscription**: the mailbox receives a confirmation email; the link's token must be used with `ConfirmSubscription` (or the user clicks the link directly).
- **SMS**: billed per delivered message; SMS message ≤ 490 chars, no `[]`.

## DMS — engine routing (there is NO `hcloud DMS`)

| Action | Kafka | RabbitMQ | RocketMQ |
|--------|-------|----------|----------|
| `huawei_list_dms_instances` | `Kafka ListInstances --engine=kafka` | `RabbitMQ ListInstancesDetails --engine=rabbitmq` | `RocketMQ ListInstances --engine=rocketmq` |
| `huawei_analyze_dms_instance_status` | `Kafka ListInstances/ShowInstance` | `RabbitMQ ListInstancesDetails/ShowInstance` | `RocketMQ ListInstances/ShowInstance` |
| `huawei_list_dms_topics` | `Kafka ListInstanceTopics --instance_id=...` | — | (`RocketMQ ListRocketInstanceTopics` if needed) |
| `huawei_create_dms_instance` | `Kafka CreatePostPaidKafkaInstance` | `RabbitMQ CreatePostPaidInstanceByEngine` | `RocketMQ CreateInstanceByEngine` |
| `huawei_delete_dms_instance` | `Kafka DeleteInstance --instance_id=...` | `RabbitMQ DeleteInstance --instance_id=...` | `RocketMQ DeleteInstance --instance_id=...` |

### DMS instance `status` values (all engines)

`CREATING`, `RUNNING`, `RESTARTING`, `DELETING`, `ERROR`, `CREATEFAILED`, `FREEZING`,
`FROZEN`, `EXTENDING`, `SHRINKING`, `EXTENDEDFAILED`, `CONFIGURING`, `ROLLBACK`,
`ROLLBACKFAILED`, `VOLUMETYPECHANGING`.

Only `RUNNING` is fully healthy; `EXTENDING`/`SHRINKING`/`RESTARTING` are transitional and fine.

### Create-instance required parameters by engine

| Parameter | Kafka | RabbitMQ | RocketMQ |
|-----------|:-----:|:--------:|:--------:|
| `--engine` | kafka | rabbitmq | rocketmq |
| `--name` | ✔ | ✔ | ✔ |
| `--engine_version` | ✔ | ✔ | ✔ |
| `--product_id` | ✔ | ✔ | ✔ |
| `--available_zones.[N]` | ✔ | ✔ | ✔ |
| `--broker_num` | ✔ | — | ✔ |
| `--access_user` / `--password` | — | ✔ | — |
| `--vpc_id` / `--subnet_id` / `--security_group_id` | ✔ | ✔ | ✔ |
| `--storage_space` | ✔ | ✔ | ✔ |
| `--storage_spec_code` | ✔ | ✔ | ✔ |

`--storage_spec_code` values: `dms.physical.storage.high.v2` | `dms.physical.storage.ultra.v2`
| `dms.physical.storage.general` | `dms.physical.storage.extreme`.

Look up valid `--product_id` / `--engine_version` pairs with `ListEngineProducts`:

```bash
hcloud Kafka ListEngineProducts --engine=kafka --cli-region={region}
hcloud RabbitMQ ListEngineProducts --engine=rabbitmq --cli-region={region}
hcloud RocketMQ ListEngineProducts --engine=rocketmq --cli-region={region}
```

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|-------------------|
| `[USE_ERROR]Unsupported service: DMS` | You typed `hcloud DMS ...` — route by engine instead (`Kafka`/`RabbitMQ`/`RocketMQ`) |
| `AddSubscription` succeeds but message never arrives | Subscription still `status=0`; run ping-back/email confirmation |
| `CreateInstance` fails | Validate VPC/subnet/security-group IDs, AZ, product availability via `ListEngineProducts` |
| Auth errors (`[USE_ERROR]auth`) | Profile AK/SK invalid or `HUAWEICLOUD_SDK_AK/SK` not set / stale |
| `--display_name` rejected as missing | `CreateTopic` requires explicit `--display_name` even when empty |
| Parameter not recognized | Rerun `hcloud <Service> <Operation> --help` — API params changed |
