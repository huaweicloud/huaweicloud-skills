# Verification Method

How to verify that the huawei-cloud-smn-dms-message skill is correctly installed and functional.

## 1. Environment sanity check

```bash
hcloud -v                                     # KooCLI installed (>= 2.x)
hcloud SMN --help           | head -5        # SMN service reachable
hcloud Kafka --help         | head -5        # Kafka service reachable
hcloud RabbitMQ --help      | head -5        # RabbitMQ service reachable
hcloud RocketMQ --help      | head -5        # RocketMQ service reachable
python3 --version                             # >= 3.8 if using scripts/smn_dms_skill.py
```

Expected: each `--help` prints "Service:" + "Available Operations".

## 2. Read-only smoke test (no resources changed)

```bash
hcloud SMN ListTopics --cli-region=cn-north-4 --limit=1
hcloud SMN ListSubscriptions --cli-region=cn-north-4 --limit=1
hcloud SMN ListMessageTemplates --cli-region=cn-north-4 --limit=1
hcloud Kafka ListInstances --engine=kafka --cli-region=cn-north-4 --limit=1
hcloud RabbitMQ ListInstancesDetails --engine=rabbitmq --cli-region=cn-north-4 --limit=1
hcloud RocketMQ ListInstances --engine=rocketmq --cli-region=cn-north-4 --limit=1
```

Expected: valid JSON responses (empty lists are fine; an auth/region error is a failure).

## 3. Action-level verification via the bundled script

```bash
python3 scripts/smn_dms_skill.py huawei_list_smn_topics --region=cn-north-4
python3 scripts/smn_dms_skill.py huawei_list_dms_instances --engine=kafka --region=cn-north-4
python3 scripts/smn_dms_skill.py huawei_analyze_smn_subscription_confirmation --region=cn-north-4
python3 scripts/smn_dms_skill.py huawei_create_smn_topic --name=verify-tmp --display_name="" --region=cn-north-4 --preview
```

`--preview` prints the exact `hcloud` command without executing it — use it to confirm command
construction safely for R2/R1 actions.

## 4. Write-action dry-run

For every R2/R1 action, run the same command with `--preview` and verify the printed `hcloud`
command matches the approved SKILL.md template (region present, required params present,
engine routed correctly). Only proceed to real execution after this dry run passes.

## 5. Full behavioral test (optional, requires real resources + confirmation)

1. Create a topic (`huawei_create_smn_topic`) → confirm it appears in `huawei_list_smn_topics`.
2. Add an email subscription (`huawei_add_smn_subscription`) → confirm `status=0` until the user
   clicks the mail link, then `status=1`.
3. Publish a message (`huawei_publish_smn_message`) → recipient receives it (email/SMS billing applies).
4. Create a Kafka instance (smallest flavor) → wait for `RUNNING` → list its topics → delete it.

Clean up all created resources and record before/after in the acceptance report.
