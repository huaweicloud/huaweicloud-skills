# hcloud CLI Installation and Configuration Guide

This Skill relies on the Huawei Cloud KooCLI (`hcloud`) for all DLI operations.

## 1. Install KooCLI

### Linux / macOS

```bash
# Use the official installation script
curl -sSL https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_install.sh -o /tmp/hcloud_install.sh
bash /tmp/hcloud_install.sh

# Verify
hcloud version
```

### Windows

Download the installer from the KooCLI download page and run it, or use
`hcloud_install.ps1` from the same OBS bucket.

## 2. Update KooCLI

```bash
hcloud update -y
hcloud version
```

## 3. Configure Authentication (AK/SK)

Two options — either is sufficient.

### Option A: Interactive configuration

```bash
hcloud configure set --cli-profile=default
# Follow the prompts to enter AK, SK, and default region (e.g. cn-north-4)
```

### Option B: Environment variables (recommended for agents)

```bash
export HUAWEICLOUD_SDK_AK="your_access_key"
export HUAWEICLOUD_SDK_SK="your_secret_key"
export HUAWEICLOUD_SDK_REGION="cn-north-4"

# Or via an existing configured profile
hcloud configure list
```

> **Security**: never commit AK/SK to the repository or skill files. Keep them
> in the environment / secret manager only.

## 4. Verify DLI Service Availability

```bash
# The service metadata exists and the CLI responds
hcloud dli --help

# Read-only smoke test against the configured account
hcloud dli ListQueues --cli-region=cn-north-4 --queue_type=all
hcloud dli ListDatabases --cli-region=cn-north-4 --limit=5
```

Expected: JSON output with `is_success: true` and resource lists.

## 5. Region and Project

- `--cli-region` selects the region; if omitted KooCLI uses the profile default.
- `--project_id` is a path parameter for DLI APIs; KooCLI auto-fills it from the
  region's parent project when omitted. Pass it explicitly only when operating
  across projects.

## 6. Common Troubleshooting

| Symptom | Fix |
|---------|-----|
| `hcloud: command not found` | Reinstall; ensure `~/.local/bin` or install path is in `PATH` |
| `Auth failed` / 401 | Re-run `hcloud configure set`; check AK/SK validity and IAM permissions |
| `There is no such operation` | Upgrade: `hcloud update -y`; check operation name spelling (PascalCase) |
| `Connection timeout` | Check network/proxy access to `myhuaweicloud.com` endpoints |
| `Project not found` | Pass `--cli-region` explicitly; verify the region supports DLI |