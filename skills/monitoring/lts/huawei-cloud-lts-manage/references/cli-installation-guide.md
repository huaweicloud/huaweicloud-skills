# CLI Installation Guide

## Install hcloud CLI

```bash
# Download and install hcloud CLI
curl -sSL https://cn-north-4-hdn-koocli.obs.cn-north-4.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh
```

## Configure Credentials

### Interactive Configuration

```bash
hcloud configure
# Follow prompts to enter AK/SK and region
```

> **Note**: hcloud CLI does not support authentication via environment variables.
> Credentials must be configured with `hcloud configure` (stored in `~/.hcloud/config.json`).

### Verify Configuration

```bash
hcloud configure list
# Check that a valid profile exists with AKSK mode
```

## Verify LTS Availability

```bash
hcloud LTS ListLogGroups --cli-region={your-region}
```

If the command returns results or an empty list (not an error), LTS is available in that region.
(`--project_id` is optional; when omitted, hcloud resolves it from the authenticated profile.)

## KooCLI Version

This skill requires KooCLI version 7.0.0 or later. Check with:

```bash
hcloud --version
```
