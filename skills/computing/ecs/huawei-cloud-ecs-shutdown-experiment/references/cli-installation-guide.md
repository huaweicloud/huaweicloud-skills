# CLI Installation Guide — hcloud KooCLI

## Overview

This guide covers installation and configuration of Huawei Cloud KooCLI (`hcloud`),
which is required by all scripts in this skill.

## Installation

### Linux (x86_64 / ARM64) & macOS (AMD64 / ARM64)

KooCLI provides an official one-click installation script that automatically
detects the platform architecture and installs the `hcloud` binary to
`/usr/local/bin/`. Download and run the script from the
[KooCLI installation page](https://support.huaweicloud.com/developer-hcli/hcli_02_0001.html).

For manual installation, download the tar.gz package matching your OS and
architecture (e.g. `huaweicloud-cli-linux-amd64.tar.gz`,
`huaweicloud-cli-mac-arm64.tar.gz`), extract it, and move the `hcloud` binary
to `/usr/local/bin/`.

### Windows

Download the installer from the [KooCLI release page](https://support.huaweicloud.com/developer-hcli/hcli_02_0001.html).

## Configuration

### 1. Set AK/SK credentials

```bash
export HW_ACCESS_KEY="your_access_key"
export HW_SECRET_KEY="your_secret_key"
```

### 2. Set default region (optional — can also use --cli-region per command)

```bash
export HW_REGION_NAME="cn-north-4"
```

### 3. Initialize the CLI (first time only)

```bash
hcloud configure set --cli-region=cn-north-4
```

## Verification

```bash
# Check version
hcloud version

# Test a simple API call with explicit --cli-region
hcloud ECS ListServersDetails --cli-region=cn-north-4 --cli-output=json
```

## Command Format Standard

All hcloud commands in this skill follow this format:

```bash
hcloud <Product> <API> [parameters] --cli-region=<region> --cli-output=json
```

- `--cli-region` is **always** specified explicitly (either in the command or via the `HW_REGION_NAME` env var as fallback)
- `--cli-output=json` is used for all commands to ensure machine-parseable output
- For batch operations (BatchStopServers, BatchStartServers), flat parameter format is used:
  - `--os-stop.servers.1.id=<id1> --os-stop.servers.2.id=<id2> --os-stop.type=SOFT`
  - `--os-start.servers.1.id=<id1> --os-start.servers.2.id=<id2>`

## Common Issues

| Issue | Cause | Solution |
|---|---|---|
| `hcloud: command not found` | Not installed or not in PATH | Re-run installer or add to PATH: `export PATH=$PATH:~/hcloud-cli` |
| `InvalidAccessKey` | AK/SK not set or incorrect | Verify `HW_ACCESS_KEY` and `HW_SECRET_KEY` environment variables |
| `Region not found` | Invalid region ID | Use a valid region like `cn-north-4`, `cn-east-3`, `cn-south-1` |
| Timeout | Network issues or large result sets | Increase timeout or narrow filters |
| Permission denied | IAM policy missing required actions | See `iam-policies.md` for required permissions |

## References

- [KooCLI Documentation](https://support.huaweicloud.com/developer-hcli/hcli_01_0001.html)
- [KooCLI Download](https://support.huaweicloud.com/developer-hcli/hcli_02_0001.html)
