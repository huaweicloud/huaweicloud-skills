# hcloud CLI Installation and Authentication Guide

All commands in this skill run through the **hcloud** CLI (KooCLI). This guide covers
installation and the two supported authentication modes: **AK/SK credentials** and a
**local hcloud profile**.

## 1. Install hcloud (KooCLI)

The hcloud CLI is a Python-based tool. Install with pip (requires Python 3.6+):

```bash
pip install huaweicloudcli
# verify
hcloud --version
```

Or use the official offline package / cloud-shell bundled CLI — see
https://support.huaweicloud.com/qs-hcli/hcli_02_003.html (KooCLI installation guide).

Upgrade KooCLI to the latest version before use:

```bash
hcloud update -y
```

## 2. Authentication mode A — AK/SK environment variables

Export your Huawei Cloud AK/SK in the shell that runs the agent:

```bash
export HUAWEICLOUD_SDK_AK="your-access-key-id"
export HUAWEICLOUD_SDK_SK="your-secret-access-key"
```

Alternative accepted variable names: `HUAWEI_ACCESS_KEY` / `HUAWEI_SECRET_KEY`,
`HW_ACCESS_KEY` / `HW_SECRET_KEY`.

> **Security:** never hardcode AK/SK in skill files, scripts, or reports; never echo them
> in the conversation. Prefer a local profile (mode B) or a secrets manager.

## 3. Authentication mode B — local hcloud profile

Configure a profile once; hcloud encrypts the credentials locally:

```bash
hcloud configure set --cli-profile=default --cli-mode=AKSK \
  --access-key=<your-access-key-id> --secret-key=<your-secret-access-key> --cli-region=cn-north-4
```

Or run the interactive wizard:

```bash
hcloud configure
```

Verify the profile:

```bash
hcloud configure list
```

Expected output contains a profile with `"mode": "AKSK"` and a **real** accessKeyId
(e.g. `"accessKeyId": "HPUA..."` — if it shows a masked placeholder like `you****key`,
re-run the configuration). It never prints the secret key.

Optional: pin the default project / region inside the profile:

```bash
hcloud configure set --cli-profile=default --cli-project-id=<project_id> --cli-region=cn-north-4
```

## 4. Region and project

- DEW (CSMS/KMS) and CTS are **regional** services. Always pass `--cli-region={region}`,
  e.g. `--cli-region=cn-north-4`.
- `--project_id` is required by the underlying APIs but hcloud auto-fills it from the
  authenticated profile; you only need to pass it explicitly when using multiple projects.

## 5. Verify DEW CLI support

```bash
hcloud CSMS --help      # shows CSMS operations (ListSecrets, ShowSecret, ...)
hcloud KMS --help       # shows KMS operations (ListKeys, CreateKey, DeleteKey, ...)
hcloud CTS --help       # shows CTS operations (ListTraces, ...)
```

KooCLI 7.2.x exposes rotation enablement as `CSMS UpdateSecret --auto_rotation=true`
(there is no separate `EnableSecretRotation` operation).