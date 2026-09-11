# KooCLI Installation & Authentication Guide

This skill runs entirely through the Huawei Cloud KooCLI (`hcloud`). Install it once, then
authenticate either with a local profile (recommended) or with AK/SK environment variables.

## 1. Install KooCLI

```bash
# Chinese mainland default mirror
curl -O https://cn-north-4-hcli.obs.cn-north-4.myhuaweicloud.com/hcli_install.sh && bash hcli_install.sh

# Verify
hcloud -v
```

Other regions: use the KooCLI install package for your site from
<https://support.huaweicloud.com/qs-hcli/hcli_02_003.html>.

## 2. Authenticate — Option A: local hcloud profile (recommended)

```bash
# Interactive profile creation (never paste AK/SK into chat; type them in the prompt)
hcloud configure set --cli-mode=AKSK --cli-region=cn-north-4
# then enter the AK and SK when prompted (credentials are stored encrypted by KooCLI)

# Confirm only metadata (values are masked), never reveal keys:
hcloud configure list
```

> Never pass AK/SK as command-line arguments (`--cli-access-key=<value>`). Command lines can be
> recorded in shell history; use the interactive prompt or environment variables instead.

The default profile stores the region and auto-resolves the project ID for `--project_id`.

## 3. Authenticate — Option B: AK/SK environment variables

KooCLI reads the standard Huawei Cloud SDK environment variables automatically. Set them outside
this conversation (shell profile, CI secret store, or a secrets manager):

```bash
export HUAWEICLOUD_SDK_AK=<your-access-key-id>
export HUAWEICLOUD_SDK_SK=<your-secret-access-key>
# Optional for temporary credentials:
export HUAWEICLOUD_SDK_SECURITY_TOKEN=<your-security-token>
# Optional default region:
export HUAWEICLOUD_SDK_REGION=cn-north-4
```

Then `hcloud` uses these for signing. Verify with a read-only call:

```bash
hcloud SMN ListTopics --cli-region=cn-north-4 --limit=1
```

## 4. Supported services for this skill

| KooCLI service | Purpose | Notes |
|----------------|---------|-------|
| `SMN` | Topics, subscriptions, message templates, publishing, confirmation | Uppercase `SMN` |
| `Kafka` | DMS Kafka instances + topics | **DMS** engine |
| `RabbitMQ` | DMS RabbitMQ instances | **DMS** engine |
| `RocketMQ` | DMS RocketMQ instances | **DMS** engine |

There is **no** `hcloud DMS` command — DMS is always reached through the three engine services.

## 5. Calibrate parameters before every run

The API surface changes over time. Always inspect the latest parameter set:

```bash
hcloud SMN CreateTopic --cli-region=cn-north-4 --help
hcloud Kafka CreatePostPaidKafkaInstance --cli-region=cn-north-4 --help
```

The skill's SKILL.md parameter tables were verified against KooCLI 7.2.12 on 2026-09-07.
