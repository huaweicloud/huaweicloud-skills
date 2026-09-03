# hcloud CLI Installation Guide

## Installation

### Linux / macOS

```bash
# Download and install hcloud CLI
curl -sSL https://hwcloudcli.obs.cn-north-1.myhuaweicloud.com/cli/latest/hcloud_install.sh -o hcloud_install.sh
bash hcloud_install.sh
```

### Verification

```bash
hcloud --version
# Expected: KooCLI Version 7.x.x
```

## Configuration

### Interactive Configuration

```bash
hcloud configure
```

This prompts for:
- Access Key ID (AK)
- Secret Access Key (SK)
- Region (e.g., `cn-north-4`)

### Non-Interactive (Environment Variables)

```bash
export HUAWEI_ACCESS_KEY="<your-access-key-id>"
export HUAWEI_SECRET_KEY="<your-secret-access-key>"
export HUAWEI_REGION="cn-north-4"
```

### Verify Configuration

```bash
hcloud configure list
```

Check that a valid profile exists with non-empty `accessKeyId`.

## LTS Service Availability

Verify LTS is available in your region:

```bash
hcloud LTS ListLogGroups --cli-region={region}
```

If this returns a valid response (even an empty list), LTS is available.
If it returns a service-not-available error, try a different region.

## Common Issues

| Issue | Solution |
|-------|----------|
| `command not found: hcloud` | Add hcloud to PATH: `export PATH=$PATH:~/hcloud/` |
| `Unauthorized` | Re-run `hcloud configure` with valid AK/SK |
| `Service not available in region` | LTS may not be available in the selected region; switch to a supported region |
| `Project ID not found` | Set `--cli-project-id` explicitly or let hcloud auto-resolve from credentials |
