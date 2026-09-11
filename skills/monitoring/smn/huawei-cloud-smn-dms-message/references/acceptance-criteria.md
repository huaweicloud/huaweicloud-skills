# Acceptance Criteria

Checklist for accepting the huawei-cloud-smn-dms-message skill.

## Structural compliance

- [ ] `SKILL.md` exists at the skill root with YAML frontmatter (`name`, `description`, `tags`, no `version`).
- [ ] Frontmatter `name` equals directory name `huawei-cloud-smn-dms-message`.
- [ ] `description` states the feature summary **and** trigger conditions.
- [ ] Required sections present: Overview, Prerequisites, Workflow, Core Commands, Parameter Confirmation, Reference Documents.
- [ ] `references/iam-policies.md` and `references/cli-installation-guide.md` exist.
- [ ] SKILL.md ≤ 500 lines; total files ≤ 30; total size ≤ 40 MB; all extensions allowlisted.

## Action coverage (15/15)

- [ ] R3 query (auto): `huawei_list_smn_topics`, `huawei_list_smn_subscriptions`,
      `huawei_list_smn_message_templates`, `huawei_list_dms_instances`, `huawei_list_dms_topics`.
- [ ] R3 diagnose (auto): `huawei_analyze_smn_subscription_confirmation`,
      `huawei_analyze_dms_instance_status`.
- [ ] R2 manage (preview + confirm): `huawei_create_smn_topic`, `huawei_add_smn_subscription`,
      `huawei_create_smn_message_template`, `huawei_publish_smn_message`, `huawei_create_dms_instance`.
- [ ] R1 destructive (end-to-end confirm): `huawei_delete_smn_topic`,
      `huawei_confirm_smn_subscription`, `huawei_delete_dms_instance`.

## CLI correctness

- [ ] Every command contains `--cli-region`.
- [ ] Service names are real KooCLI services: `SMN`, `Kafka`, `RabbitMQ`, `RocketMQ`. **No `hcloud DMS`.**
- [ ] Operations use PascalCase and were verified via `--help` on KooCLI 7.2.12.
- [ ] DMS actions route by engine (Kafka/RabbitMQ/RocketMQ), never a single "DMS" service.
- [ ] Required parameters per command match the `--help` output.

## Behavior & safety

- [ ] R3 actions execute automatically (read-only).
- [ ] R2 actions preview the command and request confirmation before execution.
- [ ] R1 actions require explicit end-to-end confirmation describing the destructive impact.
- [ ] Authentication documented for both hcloud profile and AK/SK env vars (never printed).
- [ ] No hardcoded credentials, no `hcloud configure set` examples with real values in commands.

## Testing evidence

- [ ] Read-only smoke tests executed against a live account in `cn-north-4` (see references/verification-method.md).
- [ ] `--preview` dry-runs passed for all R2/R1 commands.
- [ ] Engine routing verified live: `kafka`, `rabbitmq`, `rocketmq` each returned valid API responses.
